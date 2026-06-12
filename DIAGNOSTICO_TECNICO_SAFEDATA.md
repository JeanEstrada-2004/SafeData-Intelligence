# Diagnóstico técnico del sistema SafeData Intelligence

## 1. Resumen ejecutivo técnico

SafeData Intelligence es una aplicación web monolítica desarrollada principalmente en Python con FastAPI, plantillas Jinja2, Bootstrap, JavaScript del lado cliente y PostgreSQL como base de datos. El sistema está orientado a gestionar registros denominados en el código como "denuncias", aunque por el contexto funcional se comportan mejor como incidencias municipales o reportes operativos de seguridad ciudadana.

El sistema actual tiene un avance importante como prototipo funcional. Existen rutas web, autenticación, control parcial de roles, carga real de archivos Excel/CSV, persistencia de incidencias, dashboard con gráficos, listado de registros, mapa de calor con Mapbox, zonas operativas georreferenciadas, módulo predictivo híbrido y administración de usuarios. También existe una base de datos PostgreSQL configurada y verificada durante esta auditoría, con tablas y datos reales: 100 denuncias, 7 zonas, 1 usuario, 32 eventos de auditoría y 100 registros de caché de geocodificación.

Las funcionalidades principales implementadas son:

- Login, logout, recuperación y restablecimiento de contraseña mediante JWT en cookie HttpOnly.
- Administración de usuarios para rol Gerente.
- Carga de archivos `.xlsx`, `.xls` y `.csv` con lectura mediante pandas y persistencia en `denuncias`.
- Dashboard con KPIs y gráficos conectados a consultas reales de base de datos.
- Listado de denuncias renderizado con datos reales y filtrado del lado cliente.
- Mapa de calor con Mapbox GL JS, puntos georreferenciados, clusters, heatmap, zonas y exportación CSV.
- Predicción de riesgo mediante modelo `.pkl` si existe, con fallback heurístico por datos históricos.
- Tabla de auditoría para accesos, login, logout y recuperación de contraseña.

Las funcionalidades incompletas o parciales más relevantes son:

- APIs críticas sin autenticación real: `/api/denuncias/*`, `/api/prediccion/*` y `/api/map/*` no usan la dependencia real de usuario autenticado; en mapa existe un stub local que siempre devuelve un usuario demo.
- Carga de archivos sin tabla de lotes, sin persistencia de errores por fila y sin reporte estructurado de aceptados/rechazados.
- No existe edición/corrección de denuncias.
- No existe CRUD real de zonas, turnos, tipos de incidencia ni otros catálogos.
- La predicción no persiste resultados, no versiona modelos y no expone métricas operativas guardadas.
- No hay backups, restauración, monitoreo formal ni despliegue reproducible.
- No hay Docker, docker-compose, Alembic ni pipeline de migraciones versionadas.

Funcionalidades importantes no implementadas todavía:

- Exportación Excel/PDF de reportes gerenciales.
- Auditoría completa de cargas, exportaciones, cambios de usuarios y catálogos.
- Control CSRF para formularios con cookie.
- Registro de cargas y validaciones en base de datos.
- Backups automatizados y plan de recuperación.
- Monitoreo centralizado, alertas, métricas y healthchecks protegidos.
- Despliegue de producción documentado con HTTPS, proxy, workers y variables separadas por entorno.

El sistema está cerca de un MVP demostrable para entorno académico o piloto controlado, porque permite cargar datos, consultarlos, visualizarlos y obtener análisis geoespacial/predictivo inicial. Sin embargo, no está listo para producción municipal por brechas de seguridad, trazabilidad, operación, respaldo, despliegue y control de calidad de datos.

Riesgos técnicos principales observados:

- Credenciales o valores sensibles por defecto dentro de código de base de datos.
- APIs no protegidas aunque las pantallas sí tengan control de roles.
- Uso de `debug=True` en FastAPI.
- Ausencia de CSRF en formularios POST con cookie.
- Posible XSS si datos cargados desde Excel contienen HTML, porque algunas vistas construyen `innerHTML` con contenido de base de datos.
- Migraciones no centralizadas ni versionadas.
- Scripts de ejemplo desactualizados frente al modelo actual.
- Sin backup ni plan de continuidad.

## 2. Estructura general del repositorio

El repositorio tiene estructura monolítica. Backend, plantillas HTML, CSS, JS, scripts, SQL y archivos de datos conviven en el mismo proyecto. No existe separación frontend/backend como aplicaciones independientes; el frontend se sirve desde FastAPI usando Jinja2 y archivos estáticos.

| Carpeta/archivo | Función aparente | Observación |
| --------------- | ---------------- | ----------- |
| `app/main.py` | Punto de entrada FastAPI, rutas HTML, routers API, middleware de usuario | Crea tablas con `metadata.create_all` al iniciar; útil en desarrollo, riesgoso como mecanismo de migración en producción |
| `app/database.py` | Configuración SQLAlchemy/PostgreSQL | Lee `.env`, pero también contiene valores por defecto sensibles; se detectó conexión real a PostgreSQL |
| `app/models.py` | Modelos SQLAlchemy | Define `Denuncia`, `Zona`, `User`, `PasswordResetToken`, `AuditAccess`, `GeocodeCache` e `Incidente` |
| `app/schemas.py` | Esquemas Pydantic | Define DTOs para denuncias, dashboard, mapa, usuarios y tokens |
| `app/crud.py` | Consultas y agregaciones | Contiene CRUD básico y dashboard avanzado |
| `app/routers/autenticacion.py` | Login, logout, recuperación de contraseña | Implementado con JWT en cookie HttpOnly y auditoría básica |
| `app/routers/admin_usuarios.py` | Administración de usuarios | Solo Gerente; permite listar, crear, editar y desactivar usuarios |
| `app/routers/denuncias.py` | API de carga y consulta de denuncias | Carga real Excel/CSV; endpoints API no tienen dependencia de autenticación |
| `app/routers/mapa_calor.py` | API para filtros, puntos, zonas y CSV del mapa | Funcional, pero usa stub local de autenticación en lugar de seguridad real |
| `app/routers/prediccion_ia.py` | API de predicción y estadísticas de riesgo | Funcional parcial; sin control de roles en API |
| `app/services/enrich.py` | Enriquecimiento de denuncias | Geocodificación + peso para heatmap durante carga/backfill |
| `app/services/geocode_job.py` | Geocodificación offline | Usa Nominatim, caché y fallback a centroide de zona |
| `app/services/backfill_centroids.py` | Relleno de coordenadas por centroides | Útil para completar coordenadas faltantes |
| `app/services/seed_zonas.py` | Seeder de zonas | Actualmente contiene 7 polígonos GeoJSON reales de prueba, no cuadrados simples |
| `app/services/train_ml_model.py` | Entrenamiento de modelo predictivo | Entrena Random Forest y guarda `models/prediccion_delitos.pkl` |
| `app/utils/seguridad.py` | Hash, JWT, roles, auditoría de vistas | Usa bcrypt y PyJWT |
| `app/utils/geocoder.py` | Geocodificador con geopy/Nominatim | Incluye caché en memoria y base de datos |
| `app/utils/heat.py` | Cálculo de peso del heatmap | Heurística por tipo, resultado y antigüedad |
| `templates/` | Plantillas HTML Jinja2 | Contiene login, dashboard, carga, listado, mapa, predicción, zonas y usuarios |
| `static/css/` | Estilos CSS | Incluye estilos globales, login y mapa |
| `static/js/` | JavaScript del cliente | Incluye `main.js` y lógica Mapbox en `mapa_calor.js` |
| `models/prediccion_delitos.pkl` | Modelo ML serializado | Existe un archivo `.pkl` de aproximadamente 4.2 MB |
| `sql/migracion_auth.sql` | SQL para tablas de autenticación | Crea usuarios, tokens y auditoría |
| `sql/2025_11_03_add_geo_cols.sql` | SQL para columnas geoespaciales/caché | No crea tabla `zonas`; complementa parte de mapa |
| `db_migration_map.sql` | SQL de migración para mapa | Crea/ajusta geodatos y zonas |
| `scripts/semilla_admin.py` | Crea usuario admin inicial | Usa variables `SEED_ADMIN_*` o defaults |
| `scripts/ejecutar_sql.py` | Ejecuta archivo SQL indicado | La guía menciona uso sin argumento, pero el script requiere ruta |
| `scripts/backfill_denuncias_geo.py` | Backfill de geocodificación/peso | Escritura sobre denuncias si se ejecuta |
| `run_server.py` | Script de arranque dev | Verifica dependencias, directorios, conexión y lanza uvicorn |
| `requirements.txt` | Dependencias Python | Versiones fijadas para librerías principales |
| `README.md` | Descripción mínima | Muy incompleto |
| `GUIA_INICIO.md` | Guía extendida | Útil, pero tiene rutas/comandos desactualizados frente al código actual |
| `PREDICCION_IA.md` | Documentación del módulo IA | Detallada, pero algunas claves de respuesta documentadas no coinciden exactamente con el endpoint actual |
| `.env` | Variables locales | Existe en raíz; no se revisaron valores, solo nombres de claves |
| `.gitignore` | Exclusiones Git | Incluye `.env`, `.venv`, `*.xlsx`, `*.csv`, `*.db` |
| `crear_excel.py` | Generador de Excel antiguo | Usa columnas antiguas que no coinciden con carga actual |
| `create_sample_data.py` | Semilla antigua | Usa campos no presentes en `Denuncia` actual; potencialmente roto/desactualizado |
| `fix_admin.py` | Script temporal para admin | Contiene credenciales de demo impresas; no debería permanecer en producción |
| `tmp_*.txt` | Archivos temporales de revisión | No parecen parte funcional del sistema |

## 3. Stack tecnológico real detectado

| Componente | Tecnología detectada | Versión si aparece | Evidencia encontrada | Estado |
| ---------- | -------------------- | ------------------ | -------------------- | ------ |
| Lenguaje backend | Python | No fijada en archivo; guía menciona Python 3.13 | `*.py`, `GUIA_INICIO.md` | Implementado |
| Framework backend | FastAPI | `0.104.1` | `requirements.txt`, `app/main.py` | Implementado |
| Servidor ASGI | Uvicorn | `0.24.0` | `requirements.txt`, `run_server.py` | Implementado para desarrollo |
| ORM | SQLAlchemy | `2.0.23` | `requirements.txt`, `app/database.py`, `app/models.py` | Implementado |
| Base de datos | PostgreSQL | No fija; conexión real verificada | `app/database.py`, `psycopg2-binary`, SQL scripts | Implementado |
| Driver PostgreSQL | psycopg2-binary | `2.9.9` | `requirements.txt` | Implementado |
| Plantillas | Jinja2 | `3.1.2` | `requirements.txt`, `templates/` | Implementado |
| CSS/UI | Bootstrap CDN + CSS propio | Bootstrap `5.3.0` en CDN | `templates/base.html`, `static/css/style.css` | Implementado |
| Iconos | Font Awesome CDN | `6.0.0` en CDN | `templates/base.html` | Implementado |
| Gráficos | Chart.js CDN | `4.4.1` en CDN | `templates/dashboard.html` | Implementado |
| Mapas | Mapbox GL JS | `3.24.0` CDN | `templates/mapa_calor.html`, `static/js/mapa_calor.js` | Implementado |
| Excel/CSV | pandas, openpyxl | pandas `2.1.3`, openpyxl `3.1.2` | `requirements.txt`, `app/routers/denuncias.py` | Implementado |
| Machine Learning | scikit-learn, numpy | scikit-learn `1.7.2`, numpy `1.26.4` | `requirements.txt`, `train_ml_model.py` | Parcial |
| Modelo ML | Pickle `.pkl` | No aplica | `models/prediccion_delitos.pkl` | Existe, no se evaluó calidad predictiva |
| Autenticación | JWT en cookie HttpOnly | PyJWT `2.8.0` | `app/utils/seguridad.py`, `autenticacion.py` | Implementado parcial |
| Hash contraseñas | bcrypt | `5.0.0` | `requirements.txt`, `app/utils/seguridad.py` | Implementado |
| Email | SMTP con `EmailMessage` | Librería estándar | `app/utils/correo.py` | Parcial, depende de `.env` |
| Geocodificación | geopy/Nominatim + requests | geopy `2.4.1`, requests `2.31.0` | `app/utils/geocoder.py`, `geocode_job.py` | Parcial |
| Variables de entorno | python-dotenv | `1.0.0` | `requirements.txt`, `app/database.py` | Implementado |
| Docker | No detectado | No aplica | No existe `Dockerfile` ni `docker-compose.yml` | No implementado |
| Migraciones | SQL manual | No aplica | `sql/*.sql`, `db_migration_map.sql` | Parcial |
| Alembic | No detectado | No aplica | No existe `alembic.ini` | No implementado |
| Frontend empaquetado | No detectado | No aplica | No existe `package.json` | No implementado |
| CORS | No detectado | No aplica | No hay `CORSMiddleware` | No implementado |

## 4. Cómo se ejecuta el sistema actualmente

El sistema puede ejecutarse como aplicación FastAPI con uvicorn. Existen dos caminos documentados: `python run_server.py` y `uvicorn app.main:app`. El script `run_server.py` verifica dependencias, crea directorios y prueba conexión a base de datos antes de lanzar uvicorn con `--reload`.

La configuración de base de datos puede venir por `DATABASE_URL` o por partes (`DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASS`). En el `.env` actual se detectaron claves por partes, además de SMTP y `MAPBOX_ACCESS_TOKEN`. No se exponen valores en este diagnóstico.

| Paso | Comando o acción | Estado | Observación |
| ---- | ---------------- | ------ | ----------- |
| Crear entorno virtual | `python -m venv .venv` o similar | Documentado parcialmente | README usa `venv`; el entorno actual visible es `.venv` |
| Activar entorno | `.\.venv\Scripts\Activate.ps1` | Necesario en Windows | Ya usado anteriormente en el proyecto |
| Instalar dependencias | `pip install -r requirements.txt` | Implementado | Mejor que el comando manual largo de `GUIA_INICIO.md` |
| Configurar `.env` | Crear variables de BD, SMTP, Mapbox y secreto | Necesario | `.env` existe localmente; `.gitignore` lo excluye |
| Migrar auth | `python scripts\ejecutar_sql.py sql\migracion_auth.sql` | Parcial | La guía dice `python -m scripts.ejecutar_sql` sin argumento, pero el script requiere ruta |
| Migrar mapa | `python scripts\ejecutar_sql.py db_migration_map.sql` | Parcial | Script disponible, no hay Alembic |
| Crear admin | `python -m scripts.semilla_admin` | Implementado | Crea `admin@demo.local` por defecto si no existe |
| Sembrar zonas | `python -m app.services.seed_zonas` | Implementado | Inserta/actualiza 7 polígonos GeoJSON |
| Ejecutar servidor | `python run_server.py` | Implementado | Arranca uvicorn con reload |
| Ejecutar alternativo | `python -m uvicorn app.main:app --host 127.0.0.1 --port 8000` | Implementado | Más directo y evita lógica adicional del script |
| Entrenar ML | `python -m app.services.train_ml_model` | Parcial | Requiere datos suficientes; guarda `.pkl` |
| Geocodificar | `python -m app.services.geocode_job --batch 200` | Parcial | Usa Nominatim; requiere cuidado por rate limit |

El procedimiento está documentado, pero no de forma totalmente consistente. Hay rutas y credenciales en la documentación que no coinciden completamente con el código actual. Por ejemplo, el código usa `/login`, mientras la guía también menciona `/iniciar-sesion`.

## 5. Estado de la base de datos

El sistema usa una base de datos PostgreSQL real mediante SQLAlchemy. Durante la auditoría se realizó consulta solo de lectura a la conexión configurada y se verificó:

- Conexión exitosa.
- Tablas encontradas: `audit_access`, `denuncias`, `geocode_cache`, `incidentes`, `password_reset_tokens`, `users`, `zonas`.
- Conteos verificados:
  - `denuncias`: 100 registros.
  - `users`: 1 registro.
  - `password_reset_tokens`: 0 registros.
  - `audit_access`: 32 registros.
  - `geocode_cache`: 100 registros.
  - `zonas`: 7 registros.
  - `incidentes`: 0 registros.
- Las 100 denuncias tienen latitud y longitud.
- Las 100 denuncias mantienen `geocode_status='pending'`, aunque tienen coordenadas. Esto es inconsistente.
- `geocode_precision`/`geo_method`: 65 centroides manuales y 35 aproximadas por Nominatim.
- `source_file` y `raw_row_hash` están nulos en las 100 denuncias, por lo que no existe trazabilidad real del archivo de origen en los datos actuales.
- Rango de fechas en denuncias: desde 2020-04-04 07:30:00 hasta 2025-05-16 20:52:00.

| Tabla/modelo | Campos principales | Relación con el sistema | Estado |
| ------------ | ------------------ | ----------------------- | ------ |
| `denuncias` / `Denuncia` | `id`, `numero_parte`, `estado_denuncia`, `zona_denuncia`, `turno`, `fecha_hora_suceso`, `tipo_denuncia`, `lugar_ocurrencia`, `direccion_ocurrencia`, `latitud`, `longitud`, `peso`, `created_at` | Tabla central de incidencias/reportes operativos | Implementado |
| `zonas` / `Zona` | `id_zona`, `nombre`, `geojson`, `centroid_lat`, `centroid_lon` | Polígonos y centroides usados por mapa y fallback geográfico | Implementado |
| `geocode_cache` / `GeocodeCache` | `direccion`, `latitud`, `longitud`, `fuente`, `precision`, `updated_at` | Caché para geocodificación | Implementado |
| `users` / `User` | `id`, `email`, `full_name`, `hashed_password`, `role`, `is_active`, `created_at`, `updated_at` | Autenticación y roles | Implementado |
| `password_reset_tokens` / `PasswordResetToken` | `id`, `user_id`, `token`, `expires_at`, `used_at`, `created_at` | Recuperación de contraseña | Implementado |
| `audit_access` / `AuditAccess` | `id`, `user_id`, `action`, `path`, `ip`, `user_agent`, `created_at` | Auditoría básica de accesos | Parcial |
| `incidentes` / `Incidente` | `id` | Modelo marcado como no usado, compatibilidad | Obsoleto/no usado |

Evaluación:

- ¿La base de datos permite guardar incidencias reales? Sí. La tabla `denuncias` tiene campos operativos suficientes para reportes municipales.
- ¿Permite guardar cargas de archivos? Parcial. Existen campos `source_file` y `raw_row_hash`, pero el endpoint de carga no los llena y no existe tabla de cargas.
- ¿Permite guardar errores de validación? No implementado. Los errores se devuelven por HTTP y no se persisten.
- ¿Permite usuarios y roles? Sí. Tabla `users` y campo `role`.
- ¿Permite auditoría? Parcial. Existe `audit_access`, pero solo cubre accesos/eventos puntuales.
- ¿Permite predicciones o resultados analíticos? No. No hay tabla para guardar predicciones, modelos, métricas o resultados calculados.

## 6. Módulo de autenticación, usuarios y roles

| Funcionalidad | Estado: implementado/parcial/no implementado | Evidencia | Observación |
| ------------- | -------------------------------------------- | --------- | ----------- |
| Login real | Implementado | `app/routers/autenticacion.py`, `/login` GET/POST | Verifica usuario activo y bcrypt |
| Logout | Implementado | `POST /logout` | Elimina cookie y audita |
| JWT | Implementado | `app/utils/seguridad.py` | JWT HS256 con `sub` y `exp` |
| Cookie HttpOnly | Implementado | `resp.set_cookie(... httponly=True, samesite='lax')` | `secure=True` solo si `APP_BASE_URL` inicia con HTTPS |
| Hash de contraseña | Implementado | `bcrypt.hashpw`, `bcrypt.checkpw` | Trunca a 72 bytes por limitación bcrypt |
| Recuperación de contraseña | Parcial | `/forgot-password`, `/reset-password`, SMTP | Crea token y manda correo si SMTP funciona; si falla SMTP, el flujo no se detiene |
| Registro público de usuarios | No implementado | No hay ruta pública de registro | Solo admin crea usuarios |
| Administración de usuarios | Implementado | `/admin/users` | Solo rol Gerente |
| Baja de usuario | Parcial | `POST /admin/users/{id}/delete` | Es baja lógica (`is_active=False`) |
| Roles | Implementado parcial | `require_roles`, roles en templates y rutas | Roles: `Gerente`, `JefeOperaciones`, `Analista`, `EncargadoSipCop` |
| Restricción de rutas HTML | Parcial | `main.py`, `admin_usuarios.py` | Varias páginas protegidas por rol |
| Restricción de APIs | Parcial/deficiente | APIs de denuncias/predicción sin `get_current_user`; mapa usa stub | Riesgo alto: APIs utilizables sin sesión real |
| Middleware de sesión | Implementado | `inject_current_user` en `app/main.py` | Inyecta `request.state.current_user` para plantillas |
| Auditoría de login/logout | Implementado | `AuditAccess`, `_audit` | Guarda acción, IP y user-agent |
| CSRF | No implementado | No se detectan tokens CSRF | Riesgo en formularios POST con cookie |
| Políticas de contraseña | No implementado | No hay validación de fuerza | Solo campo requerido |

Evaluación para entorno municipal interno:

El control de acceso es insuficiente para un entorno municipal real. La autenticación de pantallas funciona de manera básica, pero las APIs críticas deben quedar protegidas con la dependencia real de usuario y rol. También faltan CSRF, política de contraseñas, rotación de secretos, cierre de sesión más robusto, auditoría completa de cambios administrativos y configuración segura para producción.

## 7. Módulo de carga de archivos Excel/CSV

| Función de carga | Estado | Evidencia | Observación |
| ---------------- | ------ | --------- | ----------- |
| Pantalla de carga | Implementado | `templates/carga_denuncias.html`, `/carga-denuncias` | Ruta HTML protegida para Gerente y EncargadoSipCop |
| Selección de archivo | Implementado | `<input accept=".xlsx,.xls,.csv">` | Validación visual del navegador |
| Endpoint de carga | Implementado | `POST /api/denuncias/upload-excel/` | API no protegida por dependencia de sesión |
| Formatos aceptados | Implementado | `.xlsx`, `.xls`, `.csv` | Validado por extensión en backend |
| Lectura Excel | Implementado | `pd.read_excel(tmp_path)` | Usa pandas/openpyxl |
| Lectura CSV | Implementado | `pd.read_csv(tmp_path, sep=None, engine='python')` | Detecta separador |
| Validación de columnas | Implementado | Lista `required` de 21 columnas | Falla si falta alguna |
| Validación de zona | Implementado | `1 <= zona <= 7` | Rango fijo |
| Validación de fecha/hora | Implementado parcial | `_parse_dt` con `pd.to_datetime` | Acepta formatos comunes, pero no guarda detalle de error por lote |
| Validación de edad | Parcial | `_req_int` si hay valor | No valida rango de edad |
| Generación de número de parte | Implementado | `_gen_numero_parte` si falta | No valida unicidad |
| Inserción en base de datos | Implementado | `db.bulk_save_objects(objetos)` | Persiste `Denuncia` |
| Enriquecimiento geográfico | Parcial | `enrich_denuncia_input` dentro de carga | Captura excepción y continúa sin informar error de geocodificación |
| Guardado temporal | Implementado | `static/uploads/<filename>` | Luego intenta eliminar el archivo |
| Persistencia del archivo original | No implementado | El archivo temporal se elimina | No hay repositorio documental |
| Registro de carga | No implementado | No existe tabla `upload_batches` o similar | No se puede auditar lote |
| Filas aceptadas/rechazadas | Parcial | Devuelve total procesado o error en primera fila inválida | No procesa parcialmente ni reporta todas las filas rechazadas |
| Vista de resultados | Parcial | Modal de éxito o alerta | No hay resumen detallado por fila |
| Descarga de plantilla | Visual/parcial | Botón descarga `/static/uploads/Datos Históricos de Denuncias.xlsx` | Depende de archivo existente; no se genera dinámicamente |

Diferenciación:

- Carga visual: implementada.
- Lectura real del archivo: implementada.
- Validación real: implementada parcialmente.
- Persistencia real en base de datos: implementada.
- Reporte real de errores: parcial, no persistente y solo primer error.

## 8. Validación, limpieza y normalización de datos

| Regla o proceso | Estado | Evidencia | Observación |
| --------------- | ------ | --------- | ----------- |
| Validación de extensión | Implementado | `name.endswith(...)` | Solo por nombre/extensión |
| Validación de columnas obligatorias | Implementado | Lista `required` en `denuncias.py` | 21 columnas requeridas |
| Limpieza de encabezados | Implementado | `df.columns = [str(c).strip() ...]` | Solo trim |
| Validación de fecha/hora | Implementado parcial | `_parse_dt` | Usa `dayfirst=True`, luego fallback |
| Validación de zona | Implementado | `_req_int` y rango 1..7 | Rango hardcodeado |
| Validación de turno | No implementado | Se guarda `_opt_str(row["turno"])` | No valida contra catálogo |
| Validación de tipo de incidencia | No implementado | Se guarda texto libre | No valida contra catálogo |
| Validación de estado | Parcial | Default `Registrada` si falta | No valida catálogo |
| Validación de edad | Parcial | Convierte a int si existe | No valida rango razonable |
| Detección de duplicados | No implementado | `raw_row_hash` existe pero no se llena | No hay restricción o chequeo |
| Limpieza de vacíos | Implementado parcial | `_opt_str` convierte NaN/vacío a `None` | Suficiente para strings básicos |
| Normalización de categorías | No implementado | No hay diccionarios de normalización | Riesgo de categorías duplicadas por escritura |
| Derivación de turno por hora | No implementado | Turno viene del archivo | No calcula desde `fecha_hora_suceso` |
| Cálculo de tiempo de respuesta | Implementado en dashboard | `get_reaccion_stats` calcula percentiles | No se persiste como campo |
| Geocodificación | Parcial | `enrich.py`, `geocoder.py`, `geocode_job.py` | Usa Nominatim y fallback; estado inconsistente en datos actuales |
| Cálculo de peso heatmap | Implementado | `app/utils/heat.py` | Heurística por tipo, resultado y antigüedad |
| Manejo de errores por fila | Parcial | `HTTPException(400, f"Error en fila...")` | Detiene todo el lote |

## 9. Gestión de incidencias o denuncias

Aunque el código usa la palabra "denuncia", funcionalmente el sistema se comporta como registro operativo o incidencia municipal. No debe interpretarse como reemplazo de denuncia formal PNP.

| Funcionalidad | Estado | Evidencia | Observación |
| ------------- | ------ | --------- | ----------- |
| Listado de incidencias | Implementado | `/listado-denuncias`, `templates/listado_denuncias.html` | Carga hasta 1000 registros desde backend |
| Tabla con campos clave | Implementado | Fecha, turno, zona, tipo, lugar, resultado, víctima | Vista operativa básica |
| Detalle de incidencia | Parcial | Modal JS `verDetalle(id)` | Usa datos ya cargados en cliente; no hay endpoint detalle |
| Filtro por zona | Implementado cliente | JS en plantilla | Filtra array local |
| Filtro por tipo | Implementado cliente | JS en plantilla | Solo valores cargados inicialmente |
| Filtro por turno | Implementado cliente | JS en plantilla | Client-side |
| Filtro por fecha | Implementado cliente | JS en plantilla | Por fecha exacta |
| Búsqueda libre | API parcial | `/api/denuncias/?q=` en router/crud esperado | La vista no la usa |
| Filtro server-side | API parcial | `listar(... zona, tipo, turno, desde, hasta, q)` | La función `crud.listar_denuncias` actual no acepta esos parámetros según el código leído, lo que sugiere inconsistencia |
| Edición/corrección | No implementado | No hay rutas edit para denuncias | Solo consulta |
| Eliminación | No implementado | No hay delete | No existe flujo |
| Exportación desde listado | No implementado | No hay botón/export real | Solo mapa exporta CSV |
| Relación con archivo de carga | No implementado | `source_file` nulo y no llenado | No se puede rastrear lote origen |

## 10. Dashboard e indicadores

| Indicador o gráfico | Estado | Fuente de datos | Observación |
| ------------------- | ------ | --------------- | ----------- |
| Total de denuncias | Implementado | `get_denuncia_count` / `stats-advanced` | Dato real |
| SLA menor a 20 min | Implementado | `get_reaccion_stats` | Calcula suceso-llegada contra 20 min |
| Reacción mediana | Implementado | Percentil 50 PostgreSQL | Dato real si existen fechas |
| Reacción p90 | Implementado | Percentil 90 PostgreSQL | Dato real si existen fechas |
| Denuncias por mes 12M | Implementado | `get_mes_labels_counts_12m` | Dato real |
| Estados por mes | Implementado | `get_estados_por_mes_6m` | Dato real |
| Estado de denuncias | Implementado | `get_estados_denuncia` | Dato real |
| Denuncias por turno | Implementado | `get_denuncias_por_turno` | Dato real |
| Top zonas | Implementado | `get_denuncias_por_zona` | Dato real |
| Lugar de ocurrencia | Implementado | `get_top_dict(lugar_ocurrencia)` | Dato real |
| Sexo de víctima | Implementado | `get_sexo_counts` | Dato real |
| Edad promedio y buckets | Implementado | `get_age_buckets`, `avg` | Dato real |
| Origen de denuncia | Implementado | `get_top_dict(origen_denuncia)` | Dato real |
| Tipos frecuentes | Implementado | `get_tipos_denuncia` | Dato real |
| Filtros de dashboard | Visual/no implementado | Badges "Últimos 12 meses", "Zonas: todas" | No hay controles de filtro reales |
| Calidad de datos | No implementado | No hay métricas de completitud | Falta indicador de nulos, geocodificación, duplicados |

Los indicadores están conectados a datos reales mediante `/api/denuncias/stats-advanced`. Sin embargo, este endpoint no está protegido con autenticación real.

## 11. Mapa, mapa de calor y georreferenciación

| Funcionalidad de mapa | Estado | Evidencia | Observación |
| --------------------- | ------ | --------- | ----------- |
| Librería de mapa | Implementado | Mapbox GL JS `v3.24.0` | CDN en `mapa_calor.html` |
| Estilo Mapbox | Implementado | `mapbox://styles/mapbox/standard`, fallback `streets-v12` | Modo día actual |
| Token Mapbox | Implementado parcial | `MAPBOX_ACCESS_TOKEN` en `.env` | Si falta, muestra warning y solo carga preview de datos |
| Puntos de incidencias | Implementado | `/api/map/points`, `pointsToGeoJson` | Requiere lat/lon |
| Heatmap | Implementado | Capa `denuncias-heatmap` | Usa `peso` |
| Clusters | Implementado | Source `denuncias-cluster` con `cluster: true` | Círculos y conteo |
| Puntos individuales | Implementado | `unclustered-point` | Popup con tipo, turno, fecha, zona, dirección |
| Filtros fecha/tipo/turno/zona/año | Implementado | JS y `/api/map/points` | Filtros reales |
| Polígonos de zonas | Implementado | `/api/map/zones`, tabla `zonas` | 7 polígonos reales de prueba |
| Etiquetas de zonas | Implementado | Capa `zones-label` | Reciente mejora visual |
| Exportación CSV del mapa | Implementado | `/api/map/points.csv` | Descarga puntos filtrados |
| Geocodificación online/offline | Parcial | `geocoder.py`, `geocode_job.py` | Nominatim + fallback |
| Fallback por zona | Implementado | `backfill_centroids.py`, `geocode_job.py` | Usa centroides si falla geocoding |
| Seguridad API mapa | Deficiente | Router usa stub `get_current_user` local | Página protegida, API no usa auth real |
| Estado de geocodificación | Inconsistente | BD: 100 con coordenadas, 100 `pending` | Falta actualizar `geocode_status` durante enriquecimiento |

El mapa es funcional, no estático. Usa datos reales de base de datos. Es parcial por seguridad API, trazabilidad geográfica y consistencia de estados de geocodificación.

## 12. Módulo de predicción o análisis de riesgo

| Elemento | Estado | Evidencia | Observación |
| -------- | ------ | --------- | ----------- |
| Pantalla de predicción | Implementado | `/prediccion-ia`, `templates/prediccion-ia.html` | Protegida por roles en HTML |
| Endpoint predictivo | Implementado parcial | `POST /api/prediccion/prediccion` | No protegido por auth real |
| Modelo ML | Parcial | `models/prediccion_delitos.pkl` existe | Se carga si existe; no se auditó calidad |
| Entrenamiento ML | Implementado parcial | `app/services/train_ml_model.py` | RandomForest con datos de `denuncias` |
| Algoritmo fallback | Implementado | Reglas por densidad diaria | Heurístico si no hay modelo o falla |
| Ranking de zonas | Implementado parcial | `/api/prediccion/zonas-riesgo` | Simple por conteo |
| Estadísticas por zona | Implementado | `/api/prediccion/estadisticas/zona/{zona}` | Conteos por turno/tipo |
| Riesgo bajo/medio/alto | Implementado | `nivel_riesgo` | También `SIN_DATOS` |
| Probabilidad | Parcial | `probabilidad` | Para reglas es heurística; para ML usa `predict_proba` |
| Sugerencia de personal | No implementado | No hay cálculo de dotación | Solo recomendaciones textuales |
| Recomendaciones | Implementado parcial | `generar_recomendaciones` | Textos fijos por riesgo |
| Métricas accuracy/F1 | Parcial | Se imprimen durante entrenamiento | No se guardan en BD ni se muestran en UI |
| Matriz de confusión | No implementado | No aparece en script | Falta |
| Persistencia de predicciones | No implementado | No hay tabla | No hay historial de consultas predictivas |
| Versionado de modelo | No implementado | Un solo `.pkl` | No hay metadata persistida ni rollback |

Conclusión: existe un módulo predictivo híbrido, pero aún debe clasificarse como parcial. No es solo visual, pero tampoco es un sistema ML productivo completo.

## 13. Exportación de reportes

| Tipo de exportación | Estado | Evidencia | Observación |
| ------------------- | ------ | --------- | ----------- |
| CSV de puntos filtrados del mapa | Implementado | `/api/map/points.csv` | Exporta id, fecha, tipo, turno, zona, lat, lon, dirección |
| Excel de plantilla/ejemplo | Parcial | Botón descarga archivo estático | No genera plantilla dinámica |
| Excel de reportes | No implementado | No hay endpoint | `main.js` tiene función simulada `exportToExcel` |
| PDF | No implementado | No se detectan librerías PDF | Falta |
| Reportes filtrados de listado | No implementado | No hay descarga en listado | Falta |
| Reportes agregados de dashboard | No implementado | No hay endpoint export | Falta |
| Reportes CODISEC/gerencia | No implementado | No hay plantillas | Falta |
| Descarga de resultados de validación | No implementado | Carga no persiste errores | Falta |

## 14. Auditoría y trazabilidad

| Evento auditado | Estado | Evidencia | Observación |
| --------------- | ------ | --------- | ----------- |
| Login exitoso | Implementado | `login_success` en `AuditAccess` | BD tiene eventos |
| Login fallido | Implementado | `login_fail` | BD tiene eventos |
| Logout | Implementado | `logout` | BD tiene eventos |
| Vista de páginas admin | Parcial | `audit_view` en rutas admin | No está en todas las vistas |
| Solicitud de reset | Implementado | `reset_request` | Audita aunque email no exista |
| Reset completado | Implementado | `reset_ok` | Audita usuario |
| Carga de archivos | No implementado | No hay auditoría en `upload_excel` | Falta |
| Errores de validación | No implementado | No se guardan | Falta |
| Exportación CSV | Parcial/no persistente | `LOGGER.info` en mapa | No guarda en tabla |
| Creación/edición de usuarios | No implementado | Rutas admin no insertan `AuditAccess` para cambios | Solo view |
| Cambio de roles | No implementado | No se audita `users_update` | Falta |
| Cambios en catálogos | No implementado | No hay CRUD real | Falta |
| Errores técnicos | Parcial | Logs de consola | No hay almacenamiento centralizado |

Existe tabla de auditoría, pero la trazabilidad es incompleta para un sistema institucional.

## 15. Administración de catálogos

| Catálogo | Estado | Evidencia | Observación |
| -------- | ------ | --------- | ----------- |
| Zonas | Parcial | Tabla `zonas`, `seed_zonas.py`, pantalla `/zonas` | Existe data y visualización; no hay CRUD real |
| Turnos | No implementado como catálogo | Valores salen de denuncias o listas hardcodeadas | No hay tabla `turnos` |
| Tipos de incidencia | No implementado como catálogo | Valores salen de denuncias o select hardcodeado en predicción | No hay tabla |
| Estados | No implementado como catálogo | Campo texto `estado_denuncia` | Sin validación |
| Roles | Parcial | Lista hardcodeada en templates y código | No hay tabla de roles/permisos |
| Comisarías | No implementado | Scripts antiguos mencionan comisarías, modelo actual no | No aplica al flujo actual |
| Fuentes de datos | Parcial | Campo `origen_denuncia` | No hay catálogo ni validación |
| Lugares de ocurrencia | No implementado como catálogo | Campo texto libre | Se usa en dashboard |

## 16. Seguridad técnica

| Control de seguridad | Estado | Evidencia | Riesgo si falta |
| -------------------- | ------ | --------- | --------------- |
| Hash de contraseñas | Implementado | bcrypt en `seguridad.py` | Bajo si se mantiene |
| JWT con expiración | Implementado | `exp` en token | Medio si `SECRET_KEY` débil |
| Cookie HttpOnly | Implementado | `httponly=True` | Reduce robo por JS |
| Cookie Secure | Parcial | Solo si `APP_BASE_URL` usa HTTPS | Riesgo en despliegue HTTP |
| `SECRET_KEY` por entorno | Parcial | Lee env, default `changeme-super-secret` | Alto si no se cambia |
| Secretos fuera del código | Parcial/deficiente | `.env` ignorado, pero `database.py` contiene defaults sensibles | Alto |
| Protección de rutas HTML | Parcial | `require_roles` en páginas | Bien para UI |
| Protección de APIs | Deficiente | APIs denuncias/predicción sin auth; mapa con stub | Alto |
| CSRF | No implementado | No hay tokens CSRF | Alto con cookies |
| Validación backend | Parcial | Carga valida columnas/zona/fecha | Falta validación integral |
| SQL injection | Parcialmente controlado | SQLAlchemy en consultas principales | Bajo/medio; revisar SQL dinámico en scripts |
| Sanitización XSS | Parcial/deficiente | Vistas usan `innerHTML` con datos de BD | Alto si se cargan datos maliciosos |
| HTTPS | No implementado en app | Sin proxy/config | Alto en producción |
| CORS | No implementado | No hay `CORSMiddleware` | No es problema si misma app; falta definición para integración |
| Manejo de errores | Parcial | `debug=True` en `FastAPI` | Alto: trazas en navegador |
| Dependencias vulnerables | No verificable | No se ejecutó scanner | Requiere `pip-audit` o similar |
| Archivos sensibles en repo | Parcial/deficiente | `.env` existe local e ignorado; `fix_admin.py` imprime password demo | Riesgo operacional |

## 17. Backups, restauración y continuidad

| Elemento de continuidad | Estado | Evidencia | Observación |
| ----------------------- | ------ | --------- | ----------- |
| Script de backup | No implementado | No se detectó | Falta `pg_dump` automatizado |
| Script de restauración | No implementado | No se detectó | Falta procedimiento |
| Documentación de backup | No implementado | README/guía no cubren | Falta |
| Carpeta de backups | No implementado | No se detectó | Falta |
| Snapshots | No verificable | Depende del proveedor PostgreSQL | No documentado |
| Plan de recuperación | No implementado | No hay RTO/RPO | Falta |
| Docker volume/persistencia | No implementado | No hay Docker | Falta |
| Procedimiento de migración segura | Parcial | SQL manual | Sin versionado ni rollback |

Debe implementarse luego:

- Backup diario con `pg_dump`.
- Retención mínima definida.
- Prueba periódica de restauración.
- RTO/RPO acordados.
- Documentación de recuperación.
- Separación entre base de desarrollo, pruebas y producción.

## 18. Monitoreo y logs

| Elemento de monitoreo | Estado | Evidencia | Observación |
| --------------------- | ------ | --------- | ----------- |
| Logs de aplicación | Parcial | `logging` en mapa/geocode, prints en scripts | Consola, no centralizado |
| Logs de errores | Parcial | `debug=True`, prints | No hay archivo/log service |
| Configuración logging global | No implementado | Solo `basicConfig` en geocode job | Falta estándar |
| Healthcheck DB | Implementado | `/health/db` | Público, sin auth |
| Healthcheck stats | Implementado | `/health/stats` | Público, sin auth |
| UptimeRobot/Netdata/Prometheus/Grafana | No implementado | No se detectó | Falta |
| Métricas de rendimiento | No implementado | No se detectó | Falta |
| Alertas | No implementado | No se detectó | Falta |
| Error tracking | No implementado | `main.js` comenta que en producción se enviaría a logging | Falta |

## 19. Despliegue e infraestructura

| Elemento de despliegue | Estado | Evidencia | Observación |
| ---------------------- | ------ | --------- | ----------- |
| Dockerfile | No implementado | No existe | Falta |
| docker-compose | No implementado | No existe | Falta |
| Nginx/proxy | No implementado | No existe config | Falta |
| systemd service | No implementado | No existe | Falta |
| Variables de entorno | Implementado parcial | `.env`, `python-dotenv` | Falta `.env.example` |
| Configuración producción | No implementado | `debug=True`, `--reload` en run_server | No listo |
| PostgreSQL remoto/local | Implementado | Config por URL o partes | Conexión real verificada |
| Cloud | Parcial/no documentado | Defaults apuntan a host remoto | No hay guía formal |
| Puertos | Implementado | `8000` en `run_server.py` | Desarrollo |
| README despliegue | Parcial | `GUIA_INICIO.md` | No cubre producción real |
| Migraciones reproducibles | Parcial | SQL manual | Sin Alembic |

Evaluación:

- Listo para despliegue local de desarrollo: sí, con `.env`, dependencias y PostgreSQL.
- Listo para pruebas/piloto controlado: parcialmente, si se protegen APIs y se documenta base.
- Listo para producción: no.

## 20. Funcionalidades existentes vs. objetivo del sistema

| Módulo objetivo | Existe | Estado | Evidencia | Qué falta para completarlo |
| --------------- | ------ | ------ | --------- | -------------------------- |
| Login y roles | Sí | Parcial | `autenticacion.py`, `seguridad.py`, `main.py` | Proteger APIs, CSRF, políticas de contraseña, hardening |
| Carga Excel/CSV | Sí | Implementado parcial | `denuncias.py`, `carga_denuncias.html` | Registro de lote, errores por fila, auth API |
| Validación de columnas | Sí | Implementado | Lista `required` | Mejor reporte de errores |
| Limpieza/normalización | Sí | Parcial | `_opt_str`, `_parse_dt` | Normalización de categorías, duplicados, catálogos |
| Guardado en base de datos | Sí | Implementado | `bulk_save_objects` | Trazabilidad de archivo |
| Listado de incidencias | Sí | Implementado parcial | `/listado-denuncias` | Server-side real, búsqueda, edición |
| Filtros | Sí | Parcial | Listado client-side, mapa server-side | Unificar filtros backend |
| Dashboard | Sí | Implementado | `/api/denuncias/stats-advanced` | Filtros, calidad de datos, auth API |
| Mapa | Sí | Implementado parcial | Mapbox GL JS | Auth API, estado geocoding consistente |
| Mapa de calor | Sí | Implementado | Capa heatmap | Validación de pesos/calidad |
| Predicción/riesgo | Sí | Parcial | `prediccion_ia.py`, `.pkl` | Versionado, métricas, persistencia, auth API |
| Exportación | Sí | Parcial | `/api/map/points.csv` | Excel/PDF/reportes gerenciales |
| Usuarios | Sí | Implementado parcial | `/admin/users` | Auditoría de cambios, validación fuerte |
| Auditoría | Sí | Parcial | `audit_access` | Cargas, exportaciones, cambios, errores |
| Catálogos | Sí | Visual/simulado/parcial | `zonas.html`, tabla `zonas` | CRUD real y catálogos formales |
| Backup | No | No implementado | No hay scripts | Crear backup/restore |
| Monitoreo | Sí | Parcial | `/health/db`, logs consola | Centralización, alertas, métricas |
| Despliegue | Sí | Parcial | `run_server.py`, guía | Docker/proxy/producción/migraciones |

## 21. Brechas técnicas prioritarias

| Prioridad | Brecha | Impacto | Recomendación técnica |
| --------- | ------ | ------- | --------------------- |
| Alta | APIs sin autenticación real | Exposición de datos y operaciones | Agregar `get_current_user`/`require_roles` a todos los routers API |
| Alta | Stub de usuario en `mapa_calor.py` | Falsa sensación de seguridad | Eliminar stub y usar `app.utils.seguridad.require_roles` |
| Alta | Secretos por defecto en código | Riesgo de filtración y acceso no autorizado | Eliminar defaults sensibles, crear `.env.example` sin secretos |
| Alta | `debug=True` | Exposición de trazas | Configurar debug por entorno y desactivarlo en producción |
| Alta | Sin CSRF | Riesgo en POST con cookies | Implementar tokens CSRF o patrón equivalente |
| Alta | Sin backup/restauración | Pérdida de datos | Crear scripts `pg_dump`/restore y cron/tarea programada |
| Alta | Carga sin registro de lote | Sin trazabilidad operacional | Crear tablas `upload_batches` y `upload_errors` |
| Media | Migraciones manuales sin versionado | Despliegues inconsistentes | Adoptar Alembic |
| Media | Geocode status inconsistente | Dificulta control de calidad del mapa | Actualizar status en carga/enrich y backfill |
| Media | Predicción sin métricas persistidas | Difícil defender calidad | Guardar metadata del modelo y métricas |
| Media | XSS por `innerHTML` con datos de BD | Riesgo si el Excel trae HTML | Render seguro o sanitización |
| Media | Scripts antiguos/desactualizados | Confusión y fallos | Retirar o actualizar `crear_excel.py`, `create_sample_data.py` |
| Baja | README incompleto | Dificulta mantenimiento | Actualizar documentación mínima |
| Baja | No hay tests | Riesgo de regresión | Agregar tests de carga, auth, API y dashboard |

## 22. Recomendaciones para completar el MVP

Seguridad y roles:

- Proteger `/api/denuncias/*`, `/api/prediccion/*`, `/api/map/*`, `/health/*` según rol.
- Eliminar el stub de autenticación de `app/routers/mapa_calor.py`.
- Desactivar `debug=True` por defecto.
- Eliminar secretos hardcodeados y crear `.env.example`.
- Implementar CSRF en formularios POST.
- Validar contraseñas mínimas y evitar credenciales demo en producción.

Carga y validación:

- Crear tabla de lotes de carga con usuario, archivo, fecha, total filas, aceptadas, rechazadas.
- Crear tabla de errores de validación por fila.
- Procesar parcialmente filas válidas y reportar rechazadas.
- Validar catálogos de zona, turno, tipo y estado.
- Implementar detección de duplicados con `raw_row_hash`.
- Llenar `source_file` y `raw_row_hash`.

Base de datos:

- Adoptar Alembic.
- Agregar índices revisados para filtros frecuentes.
- Corregir `geocode_status` cuando existen coordenadas.
- Crear tablas para catálogos y predicciones si se vuelven parte del MVP.

Dashboard:

- Agregar filtros reales por periodo, zona, turno y tipo.
- Añadir indicadores de calidad de datos: coordenadas faltantes, fechas inválidas, duplicados, estados de geocoding.
- Proteger endpoint `stats-advanced`.

Mapa:

- Mantener Mapbox y zonas GeoJSON actuales.
- Validar consistencia de `peso`, `latitud`, `longitud` y `geocode_status`.
- Registrar exportaciones CSV en auditoría.
- Agregar control de errores si Mapbox token falta o expira.

Predicción:

- Guardar metadata del modelo entrenado: fecha, dataset, accuracy, F1, features.
- Proteger endpoints.
- Versionar modelos.
- Registrar consultas predictivas si se usarán para decisiones.
- Separar claramente "heurístico" vs "ML" en respuesta.

Reportes:

- Exportar dashboard filtrado a Excel.
- Exportar listado filtrado a CSV/Excel.
- Crear plantilla PDF gerencial si se requiere.

Auditoría:

- Auditar cargas, exportaciones, creación/edición/desactivación de usuarios, cambios de roles y errores.
- Agregar usuario autenticado a cada evento.

Backup:

- Script de backup con `pg_dump`.
- Script de restauración documentado.
- Política de retención y pruebas de restauración.

Monitoreo:

- Logging estructurado.
- Healthcheck público mínimo y healthcheck interno protegido.
- Métricas básicas: latencia, errores, cantidad de cargas, fallos de geocoding.

Despliegue:

- Dockerfile o guía de despliegue manual.
- Configurar proxy HTTPS.
- Variables por entorno.
- Proceso de migración previo al arranque.

## 23. Riesgos técnicos actuales

| Riesgo | Causa | Impacto | Mitigación sugerida |
| ------ | ----- | ------- | ------------------- |
| Exposición de APIs | Falta dependencia de autenticación en routers API | Lectura/carga/predicción sin sesión | Proteger routers API por rol |
| Secretos en código | Defaults sensibles en `database.py` | Compromiso de BD | Eliminar secretos y usar env obligatorio |
| Debug activo | `FastAPI(... debug=True)` | Filtración de trazas | Config por entorno |
| CSRF | Cookies + formularios sin token | Acciones no autorizadas desde terceros | Implementar CSRF |
| XSS desde datos cargados | `innerHTML` con datos de BD | Ejecución de HTML/JS si Excel malicioso | Sanitizar o usar `textContent` |
| Sin trazabilidad de carga | No hay tabla de lotes | No se sabe qué archivo originó datos | Crear `upload_batches` |
| Sin errores persistidos | Errores solo HTTP | No hay análisis posterior de calidad | Crear `upload_errors` |
| Geocoding inconsistente | Coordenadas presentes con status pending | Mala calidad de indicadores | Corregir flujo de status |
| Predicción no gobernada | `.pkl` único sin metadata ni versionado | Difícil defender resultados | Versionar modelo y métricas |
| Sin backup | No hay scripts/procedimiento | Pérdida de datos | `pg_dump`, restore y pruebas |
| Sin despliegue reproducible | No hay Docker/Alembic/proxy | Dificultad para producción | Crear pipeline básico |
| Scripts obsoletos | Datos antiguos no coinciden con modelo actual | Confusión y errores | Depurar scripts |

## 24. Archivos o evidencias importantes encontrados

| Archivo | Por qué es importante | Uso sugerido |
| ------- | --------------------- | ------------ |
| `app/main.py` | Define app, rutas HTML, routers y healthchecks | Punto de entrada para entender navegación y permisos |
| `app/database.py` | Configura conexión PostgreSQL | Revisar seguridad de secretos y configuración por entorno |
| `app/models.py` | Define estructura de datos | Base para migraciones y diseño de BD |
| `app/routers/autenticacion.py` | Login/logout/reset | Revisar seguridad y auditoría |
| `app/utils/seguridad.py` | JWT, bcrypt, roles | Centralizar seguridad real |
| `app/routers/denuncias.py` | Carga y consulta de registros | Mejorar validación, auth API y trazabilidad |
| `app/crud.py` | Agregaciones y dashboard | Auditar rendimiento y filtros |
| `templates/dashboard.html` | Dashboard operativo | Evidencia de gráficos reales con Chart.js |
| `templates/listado_denuncias.html` | Consulta de registros | Evidencia de filtros cliente y detalle modal |
| `templates/carga_denuncias.html` | Carga Excel/CSV | Evidencia del flujo visual de ingesta |
| `app/routers/mapa_calor.py` | API geoespacial | Corregir seguridad y validar filtros |
| `static/js/mapa_calor.js` | Lógica Mapbox | Evidencia de heatmap, clusters, zonas, CSV |
| `templates/mapa_calor.html` | Vista del mapa | Evidencia de Mapbox y panel de filtros |
| `app/services/seed_zonas.py` | Zonas GeoJSON | Mantener polígonos actuales; no reemplazar por cuadrados |
| `app/services/enrich.py` | Enriquecimiento de carga | Punto para corregir geocode status y trazabilidad |
| `app/utils/geocoder.py` | Geocodificación Nominatim | Revisar rate limit, fallback y precisión |
| `app/utils/heat.py` | Peso del heatmap | Documentar regla de riesgo visual |
| `app/routers/prediccion_ia.py` | Predicción/riesgo | Proteger API y mejorar gobernanza ML |
| `app/services/train_ml_model.py` | Entrenamiento ML | Base para pipeline de modelo |
| `models/prediccion_delitos.pkl` | Modelo entrenado | No borrar sin reemplazo; versionar en futuro |
| `sql/migracion_auth.sql` | Tablas auth | Base de migración inicial |
| `db_migration_map.sql` | Migración geoespacial | Base para mapa/zona/cache |
| `scripts/semilla_admin.py` | Usuario inicial | Mantener con variables de entorno |
| `.gitignore` | Excluye `.env`, `.venv`, datos | Correcto, pero revisar archivos ya existentes |
| `GUIA_INICIO.md` | Guía de operación | Actualizar según estado real |
| `PREDICCION_IA.md` | Documentación IA | Ajustar respuesta real del endpoint |

## 25. Conclusión técnica final

SafeData Intelligence es un prototipo avanzado con funcionalidades reales de ingesta, almacenamiento, análisis, visualización geoespacial, predicción inicial y administración de usuarios. No es solamente una maqueta visual: existe base PostgreSQL real, datos cargados, dashboard conectado a consultas, mapa funcional con Mapbox, polígonos de zonas y un módulo predictivo híbrido.

Las partes más útiles como prototipo son:

- Carga real de Excel/CSV.
- Modelo de datos de incidencias municipales.
- Dashboard conectado a datos.
- Mapa de calor con puntos, clusters y zonas.
- Autenticación básica y roles en pantallas.
- Predicción inicial para análisis operativo.

Para producción faltan controles críticos:

- Seguridad real en todas las APIs.
- Eliminación de secretos hardcodeados.
- CSRF y hardening de cookies/configuración.
- Trazabilidad completa de cargas, errores y cambios.
- Backups, restauración y monitoreo.
- Migraciones versionadas.
- Despliegue reproducible y configuración de producción.
- Validación y normalización robusta de datos.

Para un MVP defendible se recomienda priorizar:

1. Proteger APIs por rol.
2. Crear trazabilidad de cargas.
3. Implementar backups.
4. Corregir configuración de producción y secretos.
5. Consolidar migraciones.
6. Añadir auditoría de cambios y exportaciones.
7. Documentar ejecución real actualizada.

El sistema puede defenderse como MVP académico/piloto si se corrigen las brechas altas. Sin esas correcciones, debe mantenerse como prototipo de análisis y no como sistema institucional productivo.

## 26. Glosario técnico breve

| Término | Definición breve |
| ------- | ---------------- |
| Backend | Parte del sistema que ejecuta lógica de negocio, APIs, autenticación y acceso a base de datos. |
| FastAPI | Framework web de Python usado para crear APIs y rutas web de alto rendimiento. |
| PostgreSQL | Motor de base de datos relacional usado para guardar denuncias, usuarios, zonas y auditoría. |
| JWT | Token firmado que permite identificar al usuario autenticado; aquí se guarda en cookie HttpOnly. |
| ORM | Capa que permite manipular tablas de base de datos como objetos Python; aquí se usa SQLAlchemy. |
| Dashboard | Panel visual de indicadores, KPIs y gráficos para análisis operativo. |
| Heatmap | Visualización de intensidad geográfica donde zonas con mayor concentración aparecen con colores más fuertes. |
| Geocodificación | Proceso de convertir una dirección textual en coordenadas de latitud y longitud. |
| Backup | Copia de seguridad de datos para recuperación ante fallos o pérdida. |
| Auditoría | Registro de eventos relevantes como accesos, cambios, cargas o exportaciones. |
| SLA | Acuerdo o umbral de nivel de servicio; aquí se usa como tiempo máximo deseado de respuesta. |
| RTO | Tiempo máximo tolerable para restaurar el servicio después de una interrupción. |
| RPO | Cantidad máxima de datos que se acepta perder medida como tiempo desde el último backup válido. |
