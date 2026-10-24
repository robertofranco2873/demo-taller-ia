# AutoServicio Demo (datos ficticios) — un solo servicio: FastAPI sirve la API y el frontend compilado.

# 1) Compilar el frontend
FROM node:24-slim AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# 2) Backend Python
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=8000
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY api/ api/
COPY src/ src/
COPY --from=web /web/dist frontend/dist
RUN mkdir -p data
EXPOSE 8000
# La base SQLite se crea sola con datos ficticios al arrancar (si no existe).
CMD ["sh", "-c", "uvicorn api.main:app --host 0.0.0.0 --port ${PORT}"]
