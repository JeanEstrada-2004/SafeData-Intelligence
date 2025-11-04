(function () {
  const API_BASE = "/api/map";
  const STORAGE_KEY = "safedata.mapaCalor.filters";
  const MAP_CENTER = [-16.408978, -71.531532];
  const DEFAULT_ZOOM = 13;
  const HEAT_OPTIONS = { radius: 25, blur: 15, minOpacity: 0.3, maxZoom: 17 };

  let map;
  let heatLayer;
  let clusterLayer;
  let zonesLayer;
  let zoneFeatures = [];
  let filtersCollapsed = false;

  // Estado de las capas
  let layersState = {
    heat: true,
    clusters: false,
    zones: false
  };

  document.addEventListener("DOMContentLoaded", init);

  async function init() {
    if (typeof L === "undefined") {
      showSummary("No se pudo cargar Leaflet (CDN bloqueado).", true);
      try { await loadFilters(); } catch (_) {}
      return;
    }

    map = L.map("map", { 
      zoomControl: true,
      zoomControl: false // Desactivamos el control por defecto para posicionarlo manualmente
    }).setView(MAP_CENTER, DEFAULT_ZOOM);
    
    // Añadir control de zoom personalizado
    L.control.zoom({
      position: 'topright'
    }).addTo(map);
    
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: "© OpenStreetMap contributors",
      maxZoom: 19,
    }).addTo(map);

    heatLayer = L.heatLayer([], HEAT_OPTIONS).addTo(map);
    clusterLayer = L.markerClusterGroup();
    zonesLayer = L.geoJSON([], {
      style: () => ({ color: "#2ecc71", weight: 2, fillOpacity: 0.08 }),
      onEachFeature: (_feature, layer) => {
        layer.on({ mouseover: () => layer.setStyle({ weight: 3, fillOpacity: 0.2 }), mouseout: () => zonesLayer.resetStyle(layer) });
      },
    });

    // Inicializar estado de capas
    updateLayerButtons();

    attachListeners();

    try {
      await loadFilters();
      await loadZones();
      const restored = restoreFilters();
      await applyFilters(restored);
    } catch (error) {
      console.error("Error inicializando mapa", error);
      showSummary("No se pudieron cargar los datos del mapa.", true);
    }
  }

  function attachListeners() {
    document.getElementById("aplicar-filtros")?.addEventListener("click", async (event) => {
      event.preventDefault();
      const filters = collectFilters();
      saveFilters(filters);
      await applyFilters(filters);
    });

    document.getElementById("descargar-csv")?.addEventListener("click", (event) => {
      event.preventDefault();
      const filters = collectFilters();
      const query = buildQueryString(filters);
      window.open(`${API_BASE}/points.csv${query ? `?${query}` : ""}`, "_blank");
    });

    document.getElementById("limpiar-filtros")?.addEventListener("click", async (event) => {
      event.preventDefault();
      await clearFilters();
    });

    // CORRECCIÓN: Permitir selección múltiple de capas
    document.getElementById("toggle-heat")?.addEventListener("click", function() {
      toggleLayer("heat");
    });
    
    document.getElementById("toggle-clusters")?.addEventListener("click", function() {
      toggleLayer("clusters");
    });
    
    document.getElementById("toggle-zonas")?.addEventListener("click", function() {
      toggleLayer("zones");
    });
    
    // Event listener para el filtro de año
    document.getElementById("filtro-anio")?.addEventListener("change", function() {
      const selectedYear = this.value;
      if (selectedYear) {
        document.getElementById("fecha-desde").value = `${selectedYear}-01-01`;
        document.getElementById("fecha-hasta").value = `${selectedYear}-12-31`;
      }
    });
    
    // CORRECCIÓN: Event listener mejorado para expandir/contraer filtros
    document.getElementById("toggle-filters")?.addEventListener("click", function(e) {
      e.stopPropagation(); // Prevenir que el evento se propague
      toggleFilters();
    });
    
    // CORRECCIÓN: Permitir hacer clic en el panel colapsado completo
    document.querySelector('.floating-filters')?.addEventListener('click', function(e) {
      if (this.classList.contains('collapsed')) {
        toggleFilters();
      }
    });
    
    // CORRECCIÓN: Prevenir que los clics dentro del panel expandido cierren el panel
    document.querySelector('.filters-content')?.addEventListener('click', function(e) {
      e.stopPropagation();
    });
  }

  // CORRECCIÓN: Función mejorada para toggle de filtros
  function toggleFilters() {
    const filtersPanel = document.querySelector('.floating-filters');
    filtersCollapsed = !filtersCollapsed;
    
    if (filtersCollapsed) {
      filtersPanel.classList.add("collapsed");
    } else {
      filtersPanel.classList.remove("collapsed");
    }
  }

  // CORRECCIÓN: Actualizar botones de capas según el estado actual
  function updateLayerButtons() {
    document.querySelectorAll('.btn-layer').forEach(btn => {
      const layerType = btn.getAttribute('data-layer');
      if (layersState[layerType]) {
        btn.classList.add('active');
      } else {
        btn.classList.remove('active');
      }
    });
  }

  // CORRECCIÓN: Modificado para permitir múltiples capas activas
  function toggleLayer(layer) {
    // Cambiar el estado de la capa
    layersState[layer] = !layersState[layer];
    
    // Aplicar cambios al mapa
    if (layer === "heat") {
      layersState.heat ? heatLayer.addTo(map) : map.removeLayer(heatLayer);
    }
    if (layer === "clusters") {
      layersState.clusters ? clusterLayer.addTo(map) : map.removeLayer(clusterLayer);
    }
    if (layer === "zones") {
      layersState.zones ? zonesLayer.addTo(map) : map.removeLayer(zonesLayer);
    }
    
    // Actualizar la apariencia de los botones
    updateLayerButtons();
  }

  async function loadFilters() {
    const response = await fetch(`${API_BASE}/filters`, { credentials: "include" });
    if (!response.ok) throw new Error("No se pudo obtener la configuración de filtros");
    const payload = await response.json();
    
    // Cargar años disponibles (desde 2020 hasta el año actual)
    const currentYear = new Date().getFullYear();
    const years = [];
    for (let year = 2020; year <= currentYear; year++) {
      years.push({ value: year, label: year });
    }
    populateSelect("filtro-anio", years);
    
    populateSelect("tipo-denuncia", payload.tipos);
    populateSelect("turno", payload.turnos);
    populateSelect("zona", payload.zonas.map((z) => ({ value: z, label: `Zona ${z}` })));
    const defaults = computeDefaultDates(payload.fecha);
    const fd = document.getElementById("fecha-desde");
    const fh = document.getElementById("fecha-hasta");
    if (fd && !fd.value) fd.value = defaults.desde;
    if (fh && !fh.value) fh.value = defaults.hasta;
  }

  async function loadZones() {
    const response = await fetch(`${API_BASE}/zones`, { credentials: "include" });
    if (!response.ok) throw new Error("No se pudieron obtener las zonas");
    zoneFeatures = await response.json();
    zonesLayer.clearLayers();
    const enriched = zoneFeatures.map((f) => {
      const g = f.geojson;
      if (g.type === "Feature") {
        g.properties = { ...(g.properties || {}), id_zona: f.id_zona, nombre: f.nombre };
        return g;
      }
      return { type: "Feature", properties: { id_zona: f.id_zona, nombre: f.nombre }, geometry: g.geometry || g };
    });
    zonesLayer.addData(enriched);
  }

  async function applyFilters(filters) {
    showSummary("Cargando datos...", false);
    const query = buildQueryString(filters);
    const response = await fetch(`${API_BASE}/points${query ? `?${query}` : ""}`, { credentials: "include" });
    if (!response.ok) {
      showSummary("No se pudieron obtener los incidentes.", true);
      throw new Error("Fallo la carga de incidentes");
    }
    const points = await response.json();
    updateMap(points);
    updateSummary(filters, points.length);
  }

  function updateMap(points) {
    updateHeatLayer(points);
    updateClusterLayer(points);
    updateIncidentCounter(points.length);
    updateZones(points);
  }

  function updateHeatLayer(points) {
    const data = points.map((p) => [p.lat, p.lon, p.peso || 1]);
    heatLayer.setLatLngs(data);
    // No añadimos/quitamos la capa aquí, eso se controla con el toggle
  }

  function updateClusterLayer(points) {
    clusterLayer.clearLayers();
    points.forEach((p) => {
      const m = L.marker([p.lat, p.lon]);
      const html = `<strong>${p.tipo || "Sin tipo"}</strong><br/>Turno: ${p.turno || "-"}<br/>Fecha: ${formatDateTime(p.fecha)}<br/>Zona: ${p.zona || "-"}<br/>Direccion: ${p.direccion || "Sin registro"}`;
      m.bindPopup(html);
      clusterLayer.addLayer(m);
    });
    // No añadimos/quitamos la capa aquí, eso se controla con el toggle
  }

  function updateZones(points) {
    if (!zoneFeatures.length) return;
    const counts = computeZoneCounts(points);
    zonesLayer.eachLayer((layer) => {
      const id = String(layer.feature?.properties?.id_zona || "");
      const name = layer.feature?.properties?.nombre || (id ? `Zona ${id}` : "Zona");
      const n = counts.get(id) || 0;
      layer.bindTooltip(`${name} - Incidentes filtrados: ${n}`, { sticky: true });
    });
    // No añadimos/quitamos la capa aquí, eso se controla con el toggle
  }

  function computeZoneCounts(points) {
    const counts = new Map();
    const polys = zoneFeatures.map((f) => ({ id: String(f.id_zona), geometries: normalizePolygons(getGeometry(f)) }));
    points.forEach((p) => {
      const lonlat = [p.lon, p.lat];
      polys.forEach((poly) => { if (poly.geometries.some((g) => pointInPolygon(lonlat, g))) counts.set(poly.id, (counts.get(poly.id) || 0) + 1); });
    });
    return counts;
  }

  function getGeometry(f) { if (!f || !f.geojson) return null; if (f.geojson.type === "Feature") return f.geojson.geometry; if (f.geojson.geometry) return f.geojson.geometry; return f.geojson; }
  function normalizePolygons(geometry) {
    if (!geometry) return [];
    if (geometry.type === "Feature") return normalizePolygons(geometry.geometry);
    if (geometry.type === "Polygon") return geometry.coordinates.map((ring) => ring.map(([lon, lat]) => [lon, lat]));
    if (geometry.type === "MultiPolygon") return geometry.coordinates.map((poly) => (poly[0] || []).map(([lon, lat]) => [lon, lat]));
    return [];
  }
  function pointInPolygon(point, polygon) {
    let inside = false;
    for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
      const xi = polygon[i][0], yi = polygon[i][1];
      const xj = polygon[j][0], yj = polygon[j][1];
      const intersects = yi > point[1] !== yj > point[1] && point[0] < ((xj - xi) * (point[1] - yi)) / ((yj - yi) || 1e-9) + xi;
      if (intersects) inside = !inside;
    }
    return inside;
  }

  function updateIncidentCounter(count) { 
    const el = document.getElementById("incident-count"); 
    if (el) el.textContent = String(count); 
  }
  
  function updateSummary(filters, count) {
    const parts = [];
    if (filters.desde) parts.push(`Desde ${filters.desde}`);
    if (filters.hasta) parts.push(`Hasta ${filters.hasta}`);
    if (filters.tipos?.length) parts.push(`Tipos: ${filters.tipos.join(", ")}`);
    if (filters.turnos?.length) parts.push(`Turnos: ${filters.turnos.join(", ")}`);
    if (filters.zonas?.length) parts.push(`Zonas: ${filters.zonas.join(", ")}`);
    const message = parts.length ? `${parts.join(" · ")}` : `Sin filtros aplicados`;
    showSummary(message, false);
    updateIncidentCounter(count);
  }
  
  function showSummary(message, isError) {
    const alert = document.getElementById("filtros-resumen");
    if (!alert) return; 
    alert.textContent = message; 
  }

  function populateSelect(elementId, values) {
    const select = document.getElementById(elementId);
    if (!select) return;
    select.innerHTML = "";
    const options = Array.isArray(values) ? values.map((v) => (typeof v === "object" ? v : { value: v, label: v })) : [];
    options.forEach((opt) => { const o = document.createElement("option"); o.value = opt.value; o.textContent = opt.label; select.appendChild(o); });
  }
  
  function computeDefaultDates(range) { 
    const today = range?.max ? new Date(range.max) : new Date(); 
    const minDate = range?.min ? new Date(range.min) : null; 
    const from = new Date(today); 
    from.setDate(from.getDate() - 30); 
    if (minDate && from < minDate) from.setTime(minDate.getTime()); 
    return { desde: formatDate(from), hasta: formatDate(today) }; 
  }
  
  function restoreFilters() { 
    const s = readFilters(); 
    if (s.desde) document.getElementById("fecha-desde").value = s.desde; 
    if (s.hasta) document.getElementById("fecha-hasta").value = s.hasta; 
    if (s.anio) document.getElementById("filtro-anio").value = s.anio; 
    setSelectValues("tipo-denuncia", s.tipos || []); 
    setSelectValues("turno", s.turnos || []); 
    setSelectValues("zona", s.zonas || []); 
    return collectFilters(); 
  }
  
  function collectFilters() { 
    return { 
      desde: document.getElementById("fecha-desde").value, 
      hasta: document.getElementById("fecha-hasta").value, 
      anio: document.getElementById("filtro-anio").value, 
      tipos: getSelectValues("tipo-denuncia"), 
      turnos: getSelectValues("turno"), 
      zonas: getSelectValues("zona") 
    }; 
  }
  
  function getSelectValues(id) { 
    return Array.from(document.getElementById(id).selectedOptions).map((o) => o.value); 
  }
  
  function setSelectValues(id, values) { 
    const el = document.getElementById(id); 
    const n = values.map((v) => v.toString()); 
    Array.from(el.options).forEach((o) => (o.selected = n.includes(o.value.toString()))); 
  }
  
  function saveFilters(f) { 
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(f)); 
  }
  
  function readFilters() { 
    try { 
      return JSON.parse(sessionStorage.getItem(STORAGE_KEY) || "{}"); 
    } catch { 
      return {}; 
    } 
  }
  
  async function clearFilters() { 
    sessionStorage.removeItem(STORAGE_KEY); 
    await loadFilters(); 
    const fresh = collectFilters(); 
    await applyFilters(fresh); 
  }
  
  function formatDate(d) { 
    const y = d.getFullYear(); 
    const m = String(d.getMonth() + 1).padStart(2, "0"); 
    const day = String(d.getDate()).padStart(2, "0"); 
    return `${y}-${m}-${day}`; 
  }
  
  function formatDateTime(v) { 
    if (!v) return "-"; 
    const d = new Date(v); 
    return `${formatDate(d)} ${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`; 
  }
})();

function buildQueryString(filters) {
  const params = new URLSearchParams();
  if (filters.desde) params.set("desde", filters.desde);
  if (filters.hasta) params.set("hasta", filters.hasta);
  if (filters.tipos?.length) params.set("tipo", filters.tipos.join(","));
  if (filters.turnos?.length) params.set("turno", filters.turnos.join(","));
  if (filters.zonas?.length) params.set("zona", filters.zonas.join(","));
  return params.toString();
}