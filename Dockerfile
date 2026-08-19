# Usa una imagen oficial y ligera de Python
FROM python:3.12-slim

# Evitar archivos .pyc y forzar salida inmediata de logs
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Directorio de trabajo
WORKDIR /app

# Crear usuario sin privilegios
RUN addgroup --system appgroup \
    && adduser --system --ingroup appgroup appuser

# Copiar requirements primero
COPY requirements.txt .

# Instalar dependencias
RUN python -m pip install --upgrade pip \
    && python -m pip install --no-cache-dir -r requirements.txt

# Copiar aplicación
COPY . .

# Crear directorios que la aplicación necesita escribir
RUN mkdir -p /app/database/usuarios \
    /app/database/chroma \
    /app/data \
    && chown -R appuser:appgroup /app

# Variables de rutas
ENV USER_DB_DIR=/app/database/usuarios
ENV CHROMA_DB_DIR=/app/database/chroma
ENV UPLOAD_DIR=/app/data

# Ejecutar como usuario NO root
USER appuser

EXPOSE 8000

CMD [
    "uvicorn",
    "main:app",
    "--host",
    "0.0.0.0",
    "--port",
    "8000"
]