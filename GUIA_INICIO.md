# 🚀 Guía de Inicio - SafeData Intelligence

Guía completa para configurar y ejecutar el sistema de denuncias ciudadanas con predicción de riesgo por IA.

---

## 📋 Requisitos Previos

### Software Necesario

- **Python 3.13** o superior
- **PostgreSQL** (base de datos en Render u otro servidor)
- **Git** (opcional, para clonar el repositorio)
- **Navegador web** moderno (Chrome, Firefox, Edge)

---

## 🔧 Instalación Paso a Paso

### 1. Clonar o Descargar el Proyecto

```bash
# Si usas Git
git clone <url-del-repositorio>
cd SafeData-Intelligence-main

# O descomprime el archivo ZIP descargado
```

### 2. Instalar Dependencias de Python

Abre PowerShell o CMD en la carpeta del proyecto y ejecuta:

```powershell
pip install fastapi uvicorn sqlalchemy psycopg2-binary python-multipart jinja2 pandas openpyxl python-dotenv requests scikit-learn numpy
```

**Dependencias incluidas:**

- `fastapi` - Framework web
- `uvicorn` - Servidor ASGI
- `sqlalchemy` - ORM para base de datos
- `psycopg2-binary` - Conector PostgreSQL
- `jinja2` - Motor de plantillas
- `pandas` & `openpyxl` - Manejo de Excel
- `scikit-learn` & `numpy` - Machine Learning
- `python-dotenv` - Variables de entorno
- `requests` - Peticiones HTTP

### 3. Configurar Base de Datos

Crea un archivo `.env` en la raíz del proyecto con tus credenciales:

```env
# Base de datos PostgreSQL
DATABASE_URL=postgresql://usuario:contraseña@host:puerto/nombre_bd

# Ejemplo con Render:
# DATABASE_URL=postgresql://safedata_db_user:password@dpg-xxxxx-a.oregon-postgres.render.com/safedata_db

# Configuración de correo (opcional)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
EMAIL_SENDER=tu-email@gmail.com
EMAIL_PASSWORD=tu-contraseña-de-aplicacion

# Clave secreta para JWT
SECRET_KEY=tu-clave-secreta-aqui
```

### 4. Crear la Base de Datos

Ejecuta el script de migración SQL:

```powershell
python -m scripts.ejecutar_sql
```

O ejecuta manualmente el archivo `sql/migracion_auth.sql` en tu PostgreSQL.

### 5. Crear Usuario Administrador

```powershell
python -m scripts.semilla_admin
```

**Credenciales por defecto:**

- **Usuario:** `admin@safedata.com`
- **Contraseña:** `Admin123!`

⚠️ **Importante:** Cambia estas credenciales después del primer inicio de sesión.

---

## 🎯 Iniciar el Servidor

### Método Principal (Recomendado)

```powershell
python run_server.py
```

El servidor iniciará automáticamente en:

- **Aplicación:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs

### Método Alternativo (Manual)

```powershell
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## 🧪 Entrenar el Modelo de IA (Opcional)

Si tienes denuncias en la base de datos y quieres entrenar el modelo de predicción:

```powershell
python -m app.services.train_ml_model
```

**Requisitos:**

- Mínimo 50 denuncias en la base de datos
- El modelo se guardará en `models/prediccion_delitos.pkl`
- El servidor cargará automáticamente el modelo al iniciar

**Salida esperada:**

```
✅ Datos cargados: 120 registros
📊 Conjunto de entrenamiento: 96 muestras
📊 Conjunto de prueba: 24 muestras
✅ Modelo entrenado exitosamente
Precisión en datos de prueba: 62.50%
✅ Modelo guardado en models/prediccion_delitos.pkl
```

---

## 🌐 Acceder a la Aplicación

### 1. Página Principal

Abre tu navegador en: http://localhost:8000

### 2. Iniciar Sesión

- **URL:** http://localhost:8000/iniciar-sesion
- **Usuario:** `admin@safedata.com`
- **Contraseña:** `Admin123!`

### 3. Funcionalidades Disponibles

#### 📊 Dashboard

- Visualización de estadísticas
- Gráficos de denuncias por zona, turno y tipo
- Indicadores clave

#### 🗺️ Mapa de Calor

- Visualización geoespacial de denuncias
- Filtros por zona y período
- Clustering de incidentes

#### 🤖 Predicción de Riesgo (IA)

- Selecciona zona y turno
- Opcionalmente tipo de incidente
- Obtén predicción de nivel de riesgo (ALTO/MEDIO/BAJO)
- Visualización de estadísticas históricas

#### 📋 Listado de Denuncias

- Visualiza todas las denuncias registradas
- Filtros y búsqueda

#### 📤 Carga de Denuncias

- Importa denuncias desde archivo Excel
- Formato esperado: zona, tipo, turno, fecha, coordenadas

#### 👥 Administración de Usuarios

- Crear, editar y eliminar usuarios
- Asignar roles y permisos

---

## 📁 Estructura del Proyecto

```
SafeData-Intelligence-main/
├── app/
│   ├── main.py                  # Aplicación principal FastAPI
│   ├── models.py                # Modelos de base de datos
│   ├── schemas.py               # Schemas Pydantic
│   ├── database.py              # Configuración de BD
│   ├── crud.py                  # Operaciones CRUD
│   ├── routers/                 # Endpoints API
│   │   ├── autenticacion.py
│   │   ├── denuncias.py
│   │   ├── mapa_calor.py
│   │   ├── prediccion_ia.py     # 🤖 Predicción ML
│   │   └── admin_usuarios.py
│   ├── services/                # Servicios auxiliares
│   │   ├── train_ml_model.py    # Entrenamiento ML
│   │   ├── geocode_job.py
│   │   └── seed_zonas.py
│   └── utils/                   # Utilidades
│       ├── seguridad.py
│       └── correo.py
├── templates/                   # Plantillas HTML
│   ├── prediccion-ia.html       # 🎯 Interfaz de predicción
│   ├── mapa_calor.html
│   ├── dashboard.html
│   └── ...
├── static/                      # Archivos estáticos
│   ├── css/
│   └── js/
├── models/                      # Modelos ML entrenados
│   └── prediccion_delitos.pkl   # 🧠 Modelo Random Forest
├── scripts/                     # Scripts de utilidad
│   ├── semilla_admin.py
│   └── ejecutar_sql.py
├── sql/                         # Scripts SQL
│   └── migracion_auth.sql
├── run_server.py                # 🚀 Iniciar servidor
├── requirements.txt             # Dependencias
└── .env                         # Variables de entorno (crear)
```

---

## 🛠️ Solución de Problemas Comunes

### Error: "No module named 'X'"

```powershell
# Reinstala las dependencias
pip install -r requirements.txt
```

### Error de conexión a base de datos

1. Verifica que el archivo `.env` tenga la URL correcta
2. Comprueba que PostgreSQL esté ejecutándose
3. Valida las credenciales de acceso

### El modelo ML no se carga

1. Verifica que existe `models/prediccion_delitos.pkl`
2. Si no existe, entrena el modelo:
   ```powershell
   python -m app.services.train_ml_model
   ```

### Puerto 8000 ya está en uso

```powershell
# Usa otro puerto
uvicorn app.main:app --reload --port 8001
```

### Errores de caché de Python

```powershell
# Limpia archivos .pyc y __pycache__
Get-ChildItem -Path . -Include __pycache__,*.pyc -Recurse -Force | Remove-Item -Force -Recurse
```

---

## 🔒 Seguridad

### Cambiar Contraseña de Administrador

1. Inicia sesión con las credenciales por defecto
2. Ve a "Administración de Usuarios"
3. Edita el usuario admin y cambia la contraseña

### Variables de Entorno Sensibles

⚠️ **NUNCA** subas el archivo `.env` a repositorios públicos

- Usa `.env.example` para compartir el formato
- Agrega `.env` a tu `.gitignore`

---

## 📊 Uso del Sistema de Predicción

### 1. Asegúrate de tener datos

El sistema necesita denuncias históricas para hacer predicciones precisas.

### 2. Entrena el modelo (primera vez)

```powershell
python -m app.services.train_ml_model
```

### 3. Accede a la predicción

- Ve a http://localhost:8000/prediccion-ia
- Selecciona **zona** y **turno**
- Opcionalmente selecciona **tipo de incidente**
- Haz clic en **"Predecir Riesgo"**

### 4. Interpreta los resultados

#### Nivel de Riesgo

- 🔴 **ALTO** - Alta probabilidad de incidentes
- 🟡 **MEDIO** - Probabilidad moderada
- 🟢 **BAJO** - Baja probabilidad
- ⚪ **SIN DATOS** - No hay información histórica

#### Estadísticas Mostradas

- Total de denuncias en ese contexto
- Distribución por tipo de incidente
- Recomendaciones basadas en el nivel de riesgo

---

## 🔄 Actualizar el Modelo

Si agregas nuevas denuncias y quieres mejorar las predicciones:

```powershell
# 1. Detén el servidor (Ctrl+C)

# 2. Entrena nuevamente
python -m app.services.train_ml_model

# 3. Reinicia el servidor
python run_server.py
```

---

## 📝 Notas Adicionales

### Formatos Soportados para Carga de Datos

- Excel (.xlsx, .xls)
- CSV (próximamente)

### Navegadores Compatibles

- ✅ Google Chrome (recomendado)
- ✅ Microsoft Edge
- ✅ Mozilla Firefox
- ✅ Safari

### Rendimiento

- El modelo ML se carga en memoria al iniciar
- Primera predicción puede tardar ~500ms
- Predicciones subsecuentes son instantáneas (<50ms)

---

## 🆘 Soporte

### Logs del Servidor

Los logs se muestran en la terminal donde ejecutaste `python run_server.py`

### Documentación API Interactiva

Accede a http://localhost:8000/docs para:

- Probar endpoints
- Ver schemas de datos
- Generar código de ejemplo

### Verificar Estado del Sistema

```powershell
# Ver versión de Python
python --version

# Ver dependencias instaladas
pip list

# Verificar conexión a BD
python -c "from app.database import engine; print('✅ Conexión exitosa' if engine else '❌ Error')"
```

---

## 🎓 Próximos Pasos

1. **Personaliza las zonas** - Edita `app/main.py` línea 149 para ajustar tus zonas
2. **Configura correos** - Completa las variables SMTP en `.env` para notificaciones
3. **Importa datos históricos** - Usa la función de carga masiva
4. **Entrena el modelo** - Con suficientes datos, obtén predicciones precisas
5. **Explora la API** - Integra con otras aplicaciones

---

## ✅ Checklist de Inicio Rápido

- [ ] Python 3.13 instalado
- [ ] Dependencias instaladas (`pip install ...`)
- [ ] Archivo `.env` configurado
- [ ] Base de datos creada (script SQL ejecutado)
- [ ] Usuario admin creado
- [ ] Servidor iniciado (`python run_server.py`)
- [ ] Acceso a http://localhost:8000
- [ ] Inicio de sesión exitoso
- [ ] (Opcional) Modelo ML entrenado

---

**¡Listo para usar SafeData Intelligence!** 🎉

Para dudas o problemas, revisa la sección de "Solución de Problemas Comunes" o consulta los logs del servidor.
