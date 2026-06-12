# Changelog MVP

## 2026-06-11

### Seguridad y acceso

- Se endurecio `SECRET_KEY`: en produccion es obligatorio configurar un valor seguro.
- Se agrego politica minima de contrasenas para creacion y recuperacion.
- Se agrego proteccion de origen para peticiones con cookie autenticada.
- Se protegieron APIs de denuncias, mapa, prediccion y healthchecks sensibles por rol.
- Se agrego auditoria estructurada con metodo, estado y detalle JSON.

### Carga de datos

- Se agrego trazabilidad por lote (`upload_batches`).
- Se agrego registro de errores por fila (`upload_errors`).
- La carga ahora reporta filas aceptadas, rechazadas, advertidas y duplicadas.
- Se agregaron descargas CSV/XLSX de errores de carga.
- Se agrego hash de archivo y hash por fila para detectar duplicados.
- Se agregaron validaciones de fechas, edad, zona, turno, tipo, campos minimos y coordenadas.

### Denuncias y exportacion

- El listado de denuncias ahora usa filtros server-side.
- Se agregaron filtros por zona, tipo, turno, estado, fechas y texto.
- Se agregaron exportaciones CSV/XLSX respetando filtros.
- El detalle de denuncia muestra lote y archivo origen cuando existe.

### Catologos y administracion

- Se agrego modulo de catalogos administrativos.
- Se agregaron categorias base: tipos de denuncia, turnos, estados y fuentes.
- Los catalogos activos se usan en validaciones de carga.

### Auditoria

- Se agrego pantalla administrativa para consultar eventos.
- Se registran accesos, login/logout, cambios de usuario, cambios de catalogo, cargas, exportaciones y predicciones.

### Mapa y geodatos

- El mapa usa autenticacion real y roles.
- Los puntos exponen calidad de geocodificacion.
- Los popups muestran la precision de la coordenada.
- La exportacion CSV del mapa queda auditada.

### Prediccion

- Se registra cada consulta predictiva en `prediction_logs`.
- La respuesta indica si fue modelo ML, heuristica historica o falta de datos.
- Se agrego explicacion textual y advertencia de uso responsable.

### Operacion

- Se agregaron migraciones SQL idempotentes.
- Se agregaron scripts de backup y restauracion PostgreSQL.
- Se agrego `.env.example`.
- Se actualizo documentacion de despliegue, migraciones, backup y ejecucion.
