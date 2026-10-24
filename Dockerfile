# AutoServicio Demo (datos ficticios): un solo servicio. FastAPI sirve la API y el frontend compilado.
# Imágenes base fijadas a versiones exactas (Debian bookworm) para builds reproducibles.

# 1) Compilar el frontend
FROM node:24.21.0-bookworm-slim AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# 2) Backend Python
FROM python:3.12.14-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8000 \
    APP_TZ=America/Mexico_City
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY api/ api/
COPY src/ src/
COPY --from=web /web/dist frontend/dist
# Usuario sin privilegios; solo puede escribir en data/ (la base SQLite).
RUN useradd --create-home --uid 10001 app && mkdir -p data && chown -R app:app data
USER app
EXPOSE 8000
# La base se crea sola con datos ficticios; con DEMO_MODE=true se restablece al arrancar y cada 24 h.
CMD ["sh", "-c", "uvicorn api.main:app --host 0.0.0.0 --port ${PORT} --proxy-headers --forwarded-allow-ips='*'"]
