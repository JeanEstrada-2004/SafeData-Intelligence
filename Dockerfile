# Dockerfile para SafeData-Intelligence
# Construye una imagen ligera para ejecutar FastAPI (uvicorn).
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000

WORKDIR /app

# Dependencias del sistema necesarias para paquetes Python (psycopg2, etc.)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       build-essential gcc libpq-dev curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copia requisitos e instala dependencias Python
COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip setuptools wheel \
    && pip install --no-cache-dir -r /app/requirements.txt

# Copia el resto del proyecto
COPY . /app

# Crear usuario no-root
RUN groupadd -r app && useradd --no-log-init -r -g app app \
    && chown -R app:app /app
USER app

EXPOSE 8000

# Comando por defecto; Render inyecta la variable PORT en tiempo de ejecución
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --lifespan auto"]
