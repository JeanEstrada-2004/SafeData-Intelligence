(function () {
  const API_BASE = "/api/map";
  const STORAGE_KEY = "safedata.mapaCalor.filters";
  const MAP_CENTER = [-71.531532, -16.408978];
  const DEFAULT_STYLE = "mapbox://styles/mapbox/standard";
  const FALLBACK_STYLE = "mapbox://styles/mapbox/streets-v12";
  const ZONE_COLORS = ["#0077b6", "#008f7a", "#7c3aed", "#d97706", "#dc2626", "#0891b2", "#15803d"];

  let map;
  let currentPoints = emptyFeatureCollection();
  let currentZones = emptyFeatureCollection();
  let filtersCollapsed = false;
  let fallbackApplied = false;

  const layersState = {
    heat: true,
    clusters: true,
    zones: true,
  };

  document.addEventListener("DOMContentLoaded", init);

  async function init() {
    attachListeners();
    updateLayerButtons();

    try {
      await loadFilters();
      const restored = restoreFilters();

      if (!window.SAFEDATA_MAPBOX_TOKEN) {
        showTokenWarning();
        showSummary("Token de Mapbox pendiente.", true);
        await loadPreviewData(restored);
        return;
      }

      if (typeof mapboxgl === "undefined") {
        showSummary("No se pudo cargar Mapbox GL JS.", true);
        return;
      }

      mapboxgl.accessToken = window.SAFEDATA_MAPBOX_TOKEN;
      createMap();
      map.once("load", async () => {
        addOrUpdateSourcesAndLayers();
        await loadZones();
        await applyFilters(restored);
      });
    } catch (error) {
      console.error("Error inicializando mapa", error);
      showSummary("No se pudieron cargar los datos del mapa.", true);
    }
  }

  function createMap() {
    map = new mapboxgl.Map({
      container: "map",
      style: DEFAULT_STYLE,
      center: MAP_CENTER,
      zoom: 13.4,
      pitch: 54,
      bearing: -18,
      antialias: true,
      attributionControl: false,
      config: {
        basemap: {
          lightPreset: "day",
          showPointOfInterestLabels: true,
          showRoadLabels: true,
          showTransitLabels: false,
        },
      },
    });

    map.addControl(new mapboxgl.NavigationControl({ visualizePitch: true }), "top-right");
    map.addControl(new mapboxgl.FullscreenControl(), "top-right");
    map.addControl(new mapboxgl.AttributionControl({ compact: true }), "bottom-right");

    map.on("style.load", () => {
      if (typeof map.setFog === "function") {
        map.setFog({
          color: "rgb(226, 235, 241)",
          "high-color": "rgb(196, 218, 232)",
          "horizon-blend": 0.1,
          "space-color": "rgb(236, 242, 246)",
          "star-intensity": 0,
        });
      }
      addOrUpdateSourcesAndLayers();
      applyLayerVisibility();
    });

    map.on("error", (event) => {
      const message = String(event?.error?.message || "");
      if (!fallbackApplied && message && !message.includes("401")) {
        fallbackApplied = true;
        map.setStyle(FALLBACK_STYLE);
        showSummary("Estilo estándar no disponible. Usando vista de calles.", false);
      }
    });
  }

  function attachListeners() {
    document.getElementById("aplicar-filtros")?.addEventListener("click", async () => {
      const filters = collectFilters();
      saveFilters(filters);
      await applyFilters(filters);
    });

    document.getElementById("descargar-csv")?.addEventListener("click", () => {
      const query = buildQueryString(collectFilters());
      window.open(`${API_BASE}/points.csv${query ? `?${query}` : ""}`, "_blank");
    });

    document.getElementById("limpiar-filtros")?.addEventListener("click", clearFilters);

    document.getElementById("toggle-heat")?.addEventListener("click", () => toggleLayer("heat"));
    document.getElementById("toggle-clusters")?.addEventListener("click", () => toggleLayer("clusters"));
    document.getElementById("toggle-zonas")?.addEventListener("click", () => toggleLayer("zones"));

    document.getElementById("filtro-anio")?.addEventListener("change", function () {
      if (this.value) {
        document.getElementById("fecha-desde").value = `${this.value}-01-01`;
        document.getElementById("fecha-hasta").value = `${this.value}-12-31`;
      }
    });

    document.getElementById("toggle-filters")?.addEventListener("click", toggleFilters);
  }

  function addOrUpdateSourcesAndLayers() {
    if (!map || !map.isStyleLoaded()) return;

    if (!map.getSource("denuncias-heat")) {
      map.addSource("denuncias-heat", {
        type: "geojson",
        data: currentPoints,
        buffer: 0,
        maxzoom: 14,
      });
    } else {
      map.getSource("denuncias-heat").setData(currentPoints);
    }

    if (!map.getSource("denuncias-cluster")) {
      map.addSource("denuncias-cluster", {
        type: "geojson",
        data: currentPoints,
        cluster: true,
        clusterMaxZoom: 14,
        clusterRadius: 44,
      });
    } else {
      map.getSource("denuncias-cluster").setData(currentPoints);
    }

    if (!map.getSource("zonas-source")) {
      map.addSource("zonas-source", {
        type: "geojson",
        data: currentZones,
      });
    } else {
      map.getSource("zonas-source").setData(currentZones);
    }

    addZonesLayers();
    addHeatLayer();
    addClusterLayers();
    orderMapLayers();
    bindMapInteractions();
  }

  function orderMapLayers() {
    if (!map) return;
    try {
      if (map.getLayer("zones-outline") && map.getLayer("clusters")) {
        map.moveLayer("zones-outline", "clusters");
      }
      if (map.getLayer("zones-label") && map.getLayer("clusters")) {
        map.moveLayer("zones-label", "clusters");
      }
    } catch (error) {
      console.debug("No se pudo reordenar capas del mapa", error);
    }
  }

  function addZonesLayers() {
    const zoneColorMatch = [
      "match",
      ["to-number", ["get", "id_zona"]],
      1,
      ZONE_COLORS[0],
      2,
      ZONE_COLORS[1],
      3,
      ZONE_COLORS[2],
      4,
      ZONE_COLORS[3],
      5,
      ZONE_COLORS[4],
      6,
      ZONE_COLORS[5],
      7,
      ZONE_COLORS[6],
      "#0077b6",
    ];

    if (!map.getLayer("zones-fill")) {
      map.addLayer({
        id: "zones-fill",
        type: "fill",
        source: "zonas-source",
        paint: {
          "fill-color": zoneColorMatch,
          "fill-opacity": ["interpolate", ["linear"], ["zoom"], 11, 0.18, 13, 0.28, 15, 0.38],
        },
      });
    }
    if (!map.getLayer("zones-outline")) {
      map.addLayer({
        id: "zones-outline",
        type: "line",
        source: "zonas-source",
        paint: {
          "line-color": zoneColorMatch,
          "line-width": ["interpolate", ["linear"], ["zoom"], 11, 1.6, 14, 2.8, 16, 3.6],
          "line-opacity": 0.96,
        },
      });
    }
    if (!map.getLayer("zones-label")) {
      map.addLayer({
        id: "zones-label",
        type: "symbol",
        source: "zonas-source",
        minzoom: 12,
        layout: {
          "text-field": ["concat", "Zona ", ["to-string", ["get", "id_zona"]]],
          "text-font": ["Open Sans Bold", "Arial Unicode MS Bold"],
          "text-size": ["interpolate", ["linear"], ["zoom"], 12, 12, 15, 14],
          "text-allow-overlap": false,
          "text-padding": 8,
        },
        paint: {
          "text-color": "#063a46",
          "text-halo-color": "rgba(255,255,255,0.92)",
          "text-halo-width": 2,
        },
      });
    }
  }

  function addHeatLayer() {
    if (map.getLayer("denuncias-heatmap")) return;
    map.addLayer({
      id: "denuncias-heatmap",
      type: "heatmap",
      source: "denuncias-heat",
      maxzoom: 17,
      paint: {
        "heatmap-weight": ["interpolate", ["linear"], ["get", "peso"], 0, 0, 1, 1],
        "heatmap-intensity": ["interpolate", ["linear"], ["zoom"], 11, 0.7, 15, 1.4],
        "heatmap-color": [
          "interpolate",
          ["linear"],
          ["heatmap-density"],
          0,
          "rgba(22,166,182,0)",
          0.18,
          "rgba(22,166,182,0.55)",
          0.42,
          "rgba(15,118,110,0.72)",
          0.68,
          "rgba(217,146,9,0.82)",
          1,
          "rgba(208,68,68,0.96)",
        ],
        "heatmap-radius": ["interpolate", ["linear"], ["zoom"], 11, 16, 15, 34],
        "heatmap-opacity": 0.86,
      },
    });
  }

  function addClusterLayers() {
    if (!map.getLayer("clusters")) {
      map.addLayer({
        id: "clusters",
        type: "circle",
        source: "denuncias-cluster",
        filter: ["has", "point_count"],
        paint: {
          "circle-color": ["step", ["get", "point_count"], "#16a6b6", 25, "#d99209", 75, "#d04444"],
          "circle-radius": ["step", ["get", "point_count"], 18, 25, 25, 75, 34],
          "circle-opacity": 0.9,
          "circle-stroke-width": 2,
          "circle-stroke-color": "rgba(255,255,255,0.86)",
        },
      });
    }

    if (!map.getLayer("cluster-count")) {
      map.addLayer({
        id: "cluster-count",
        type: "symbol",
        source: "denuncias-cluster",
        filter: ["has", "point_count"],
        layout: {
          "text-field": ["get", "point_count_abbreviated"],
          "text-font": ["Open Sans Bold", "Arial Unicode MS Bold"],
          "text-size": 12,
        },
        paint: { "text-color": "#ffffff" },
      });
    }

    if (!map.getLayer("unclustered-point")) {
      map.addLayer({
        id: "unclustered-point",
        type: "circle",
        source: "denuncias-cluster",
        filter: ["!", ["has", "point_count"]],
        paint: {
          "circle-color": ["interpolate", ["linear"], ["get", "peso"], 0, "#16a6b6", 0.55, "#d99209", 1, "#d04444"],
          "circle-radius": ["interpolate", ["linear"], ["zoom"], 11, 4, 16, 8],
          "circle-opacity": 0.88,
          "circle-stroke-width": 1.5,
          "circle-stroke-color": "#ffffff",
        },
      });
    }
  }

  function bindMapInteractions() {
    if (map.__safedataBound) return;
    map.__safedataBound = true;

    map.on("click", "clusters", (event) => {
      const features = map.queryRenderedFeatures(event.point, { layers: ["clusters"] });
      const clusterId = features[0].properties.cluster_id;
      map.getSource("denuncias-cluster").getClusterExpansionZoom(clusterId, (err, zoom) => {
        if (err) return;
        map.easeTo({ center: features[0].geometry.coordinates, zoom });
      });
    });

    map.on("click", "unclustered-point", (event) => {
      const feature = event.features[0];
      const p = feature.properties || {};
      const precision = describeGeoPrecision(p);
      new mapboxgl.Popup({ closeButton: true, maxWidth: "300px" })
        .setLngLat(feature.geometry.coordinates)
        .setHTML(`
          <div class="map-popup">
            <strong>${p.tipo || "Sin tipo"}</strong>
            <div class="meta">Turno: ${p.turno || "-"}<br>Fecha: ${formatDateTime(p.fecha)}<br>Zona: ${p.zona || "-"}<br>Dirección: ${p.direccion || "Sin registro"}<br>Coordenada: ${precision}</div>
          </div>
        `)
        .addTo(map);
    });

    ["clusters", "unclustered-point"].forEach((layer) => {
      map.on("mouseenter", layer, () => { map.getCanvas().style.cursor = "pointer"; });
      map.on("mouseleave", layer, () => { map.getCanvas().style.cursor = ""; });
    });
  }

  async function loadFilters() {
    const response = await fetch(`${API_BASE}/filters`, { credentials: "include" });
    if (!response.ok) throw new Error("No se pudo obtener la configuración de filtros");
    const payload = await response.json();

    populateSelect("tipo-denuncia", payload.tipos || []);
    populateSelect("turno", payload.turnos || []);
    populateSelect("zona", (payload.zonas || []).map((z) => ({ value: z, label: `Zona ${z}` })));

    const years = buildYears(payload.fecha);
    populateSelect("filtro-anio", [{ value: "", label: "Todos los años" }, ...years]);

    const defaults = computeDefaultDates(payload.fecha);
    const fd = document.getElementById("fecha-desde");
    const fh = document.getElementById("fecha-hasta");
    if (fd && !fd.value) fd.value = defaults.desde;
    if (fh && !fh.value) fh.value = defaults.hasta;
  }

  async function loadZones() {
    const response = await fetch(`${API_BASE}/zones`, { credentials: "include" });
    if (!response.ok) throw new Error("No se pudieron obtener las zonas");
    const zones = await response.json();
    currentZones = zonesToGeoJson(zones);
    if (map?.getSource("zonas-source")) map.getSource("zonas-source").setData(currentZones);
  }

  async function loadPreviewData(filters) {
    const query = buildQueryString(filters);
    const response = await fetch(`${API_BASE}/points${query ? `?${query}` : ""}`, { credentials: "include" });
    if (!response.ok) return;
    const points = await response.json();
    updateIncidentCounter(points.length);
    updateSummary(filters, points.length);
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
    currentPoints = pointsToGeoJson(points);
    if (map?.getSource("denuncias-heat")) map.getSource("denuncias-heat").setData(currentPoints);
    if (map?.getSource("denuncias-cluster")) map.getSource("denuncias-cluster").setData(currentPoints);
    updateIncidentCounter(points.length);
    updateSummary(filters, points.length);
  }

  function toggleFilters() {
    const panel = document.getElementById("map-control-panel");
    filtersCollapsed = !filtersCollapsed;
    panel.classList.toggle("collapsed", filtersCollapsed);
  }

  function toggleLayer(layer) {
    layersState[layer] = !layersState[layer];
    updateLayerButtons();
    applyLayerVisibility();
  }

  function applyLayerVisibility() {
    setVisibility(["denuncias-heatmap"], layersState.heat);
    setVisibility(["clusters", "cluster-count", "unclustered-point"], layersState.clusters);
    setVisibility(["zones-fill", "zones-outline", "zones-label"], layersState.zones);
    updateHudMeta(collectFilters());
  }

  function setVisibility(ids, visible) {
    if (!map) return;
    ids.forEach((id) => {
      if (map.getLayer(id)) map.setLayoutProperty(id, "visibility", visible ? "visible" : "none");
    });
  }

  function updateLayerButtons() {
    document.querySelectorAll(".map-layer-button").forEach((btn) => {
      const layerType = btn.getAttribute("data-layer");
      btn.classList.toggle("active", Boolean(layersState[layerType]));
    });
    updateHudLayers();
  }

  function pointsToGeoJson(points) {
    return {
      type: "FeatureCollection",
      features: (points || [])
        .filter((p) => Number.isFinite(Number(p.lon)) && Number.isFinite(Number(p.lat)))
        .map((p) => ({
          type: "Feature",
          geometry: { type: "Point", coordinates: [Number(p.lon), Number(p.lat)] },
          properties: {
            id: p.id,
            peso: Number(p.peso || 1),
            tipo: p.tipo || "",
            turno: p.turno || "",
            fecha: p.fecha || "",
            zona: p.zona || "",
            direccion: p.direccion || "",
            geocode_status: p.geocode_status || "",
            geocode_precision: p.geocode_precision || "",
            geo_method: p.geo_method || "",
          },
        })),
    };
  }

  function zonesToGeoJson(zones) {
    return {
      type: "FeatureCollection",
      features: (zones || []).map((zone) => {
        const raw = zone.geojson || {};
        if (raw.type === "Feature") {
          return {
            ...raw,
            properties: { ...(raw.properties || {}), id_zona: zone.id_zona, nombre: zone.nombre },
          };
        }
        return {
          type: "Feature",
          geometry: raw.geometry || raw,
          properties: { id_zona: zone.id_zona, nombre: zone.nombre },
        };
      }),
    };
  }

  function emptyFeatureCollection() {
    return { type: "FeatureCollection", features: [] };
  }

  function populateSelect(elementId, values) {
    const select = document.getElementById(elementId);
    if (!select) return;
    select.innerHTML = "";
    const options = Array.isArray(values) ? values.map((v) => (typeof v === "object" ? v : { value: v, label: v })) : [];
    options.forEach((opt) => {
      const option = document.createElement("option");
      option.value = opt.value;
      option.textContent = opt.label;
      select.appendChild(option);
    });
    renderChoiceCards(elementId);
  }

  function renderChoiceCards(elementId) {
    const select = document.getElementById(elementId);
    const container = document.getElementById(`${elementId}-cards`);
    if (!select || !container) return;

    container.innerHTML = "";
    Array.from(select.options).forEach((option) => {
      const card = document.createElement("button");
      card.type = "button";
      card.className = "choice-card";
      card.textContent = option.textContent;
      card.title = option.textContent;
      card.setAttribute("aria-pressed", option.selected ? "true" : "false");
      card.classList.toggle("active", option.selected);
      card.addEventListener("click", () => {
        option.selected = !option.selected;
        renderChoiceCards(elementId);
      });
      container.appendChild(card);
    });
  }

  function collectFilters() {
    return {
      desde: document.getElementById("fecha-desde").value,
      hasta: document.getElementById("fecha-hasta").value,
      anio: document.getElementById("filtro-anio").value,
      tipos: getSelectValues("tipo-denuncia"),
      turnos: getSelectValues("turno"),
      zonas: getSelectValues("zona"),
    };
  }

  function getSelectValues(id) {
    const select = document.getElementById(id);
    return select ? Array.from(select.selectedOptions).map((o) => o.value) : [];
  }

  function setSelectValues(id, values) {
    const el = document.getElementById(id);
    if (!el) return;
    const normalized = (values || []).map((v) => v.toString());
    Array.from(el.options).forEach((o) => { o.selected = normalized.includes(o.value.toString()); });
    renderChoiceCards(id);
  }

  function saveFilters(filters) {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(filters));
  }

  function readFilters() {
    try {
      return JSON.parse(sessionStorage.getItem(STORAGE_KEY) || "{}");
    } catch {
      return {};
    }
  }

  function restoreFilters() {
    const saved = readFilters();
    if (saved.desde) document.getElementById("fecha-desde").value = saved.desde;
    if (saved.hasta) document.getElementById("fecha-hasta").value = saved.hasta;
    if (saved.anio) document.getElementById("filtro-anio").value = saved.anio;
    setSelectValues("tipo-denuncia", saved.tipos || []);
    setSelectValues("turno", saved.turnos || []);
    setSelectValues("zona", saved.zonas || []);
    return collectFilters();
  }

  async function clearFilters() {
    sessionStorage.removeItem(STORAGE_KEY);
    await loadFilters();
    const fresh = collectFilters();
    await applyFilters(fresh);
  }

  function buildYears(range) {
    const start = range?.min ? new Date(range.min).getFullYear() : 2020;
    const end = range?.max ? new Date(range.max).getFullYear() : new Date().getFullYear();
    const years = [];
    for (let y = start; y <= end; y++) years.push({ value: y, label: y });
    return years;
  }

  function computeDefaultDates(range) {
    const today = range?.max ? new Date(range.max) : new Date();
    const minDate = range?.min ? new Date(range.min) : null;
    const from = new Date(today);
    from.setDate(from.getDate() - 30);
    if (minDate && from < minDate) from.setTime(minDate.getTime());
    return { desde: formatDate(from), hasta: formatDate(today) };
  }

  function updateIncidentCounter(count) {
    const el = document.getElementById("incident-count");
    if (el) el.textContent = String(count);
  }

  function updateSummary(filters, count) {
    const parts = [];
    if (filters.anio) parts.push(`Año ${filters.anio}`);
    if (filters.desde) parts.push(`Desde ${filters.desde}`);
    if (filters.hasta) parts.push(`Hasta ${filters.hasta}`);
    if (filters.tipos?.length) parts.push(`Tipos: ${filters.tipos.join(", ")}`);
    if (filters.turnos?.length) parts.push(`Turnos: ${filters.turnos.join(", ")}`);
    if (filters.zonas?.length) parts.push(`Zonas: ${filters.zonas.join(", ")}`);
    const message = parts.length ? `${parts.join(" · ")}` : "Sin filtros aplicados";
    showSummary(`${message} · ${count} visibles`, false);
    updateHudMeta(filters);
    updateHudLayers();
  }

  function updateHudMeta(filters) {
    const periodo = document.getElementById("hud-periodo");
    const zona = document.getElementById("hud-zona");
    if (periodo) {
      periodo.textContent = filters?.desde || filters?.hasta
        ? `${filters.desde || "Inicio"} - ${filters.hasta || "Actual"}`
        : "Sin filtros";
    }
    if (zona) {
      zona.textContent = filters?.zonas?.length
        ? filters.zonas.map((z) => `Zona ${z}`).join(", ")
        : "Todas las zonas";
    }
  }

  function updateHudLayers() {
    const el = document.getElementById("hud-capas");
    if (!el) return;
    const active = [];
    if (layersState.heat) active.push("Heatmap");
    if (layersState.clusters) active.push("Clusters");
    if (layersState.zones) active.push("Zonas");
    el.textContent = active.length ? active.join(" · ") : "Sin capas activas";
  }

  function showSummary(message, isError) {
    const el = document.getElementById("filtros-resumen");
    if (!el) return;
    el.textContent = message;
    el.classList.toggle("text-danger", Boolean(isError));
  }

  function showTokenWarning() {
    const warning = document.getElementById("map-token-warning");
    if (warning) warning.hidden = false;
  }

  function formatDate(date) {
    const y = date.getFullYear();
    const m = String(date.getMonth() + 1).padStart(2, "0");
    const d = String(date.getDate()).padStart(2, "0");
    return `${y}-${m}-${d}`;
  }

  function formatDateTime(value) {
    if (!value) return "-";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return value;
    return `${formatDate(date)} ${String(date.getHours()).padStart(2, "0")}:${String(date.getMinutes()).padStart(2, "0")}`;
  }

  function describeGeoPrecision(p) {
    const precision = String(p.geocode_precision || "").toLowerCase();
    const method = String(p.geo_method || "").toLowerCase();
    if (precision === "centroid" || method === "manual") return "Aproximada por centroide";
    if (["rooftop", "interpolated", "street"].includes(precision)) return "Geocodificada";
    if (precision || method) return "Aproximada";
    return "No especificada";
  }
})();

function buildQueryString(filters) {
  const params = new URLSearchParams();
  if (filters.desde) params.set("desde", filters.desde);
  if (filters.hasta) params.set("hasta", filters.hasta);
  if (filters.anio) params.set("anio", filters.anio);
  if (filters.tipos?.length) params.set("tipo", filters.tipos.join(","));
  if (filters.turnos?.length) params.set("turno", filters.turnos.join(","));
  if (filters.zonas?.length) params.set("zona", filters.zonas.join(","));
  return params.toString();
}
