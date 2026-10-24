"""AutoServicio Demo — API (datos ficticios).

Desarrollo:  uvicorn api.main:app --reload       Documentación:  http://localhost:8000/docs
En producción también sirve el frontend compilado (frontend/dist).
"""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from api.routers import admin, ai, analytics, auth, catalog, misc, orders, quotes, tech
from src import config, db

DIST = config.ROOT_DIR / "frontend" / "dist"


@asynccontextmanager
async def lifespan(_: FastAPI):
    db.ensure_database()  # crea la base con datos ficticios si no existe
    yield


app = FastAPI(
    title="AutoServicio Demo API",
    version="2.0.0",
    description=(f"{config.DEMO_NOTICE}\n\nAPI REST del taller: estudio de tiempos, cotizador, órdenes, "
                 "KPIs, Pareto, capacidad, secuenciación, control estadístico, inventario e IA opcional. "
                 "Autenticación con JWT (Bearer); permisos por rol validados en cada endpoint."),
    lifespan=lifespan,
)
# Solo para desarrollo con Vite en otro puerto; en producción el frontend se sirve desde aquí.
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
                   allow_methods=["*"], allow_headers=["*"])

for r in (auth, catalog, quotes, orders, analytics, admin, tech, ai, misc):
    app.include_router(r.router)


@app.get("/api/health", tags=["Sistema"])
def health():
    return {"ok": True, "demo": True}


if DIST.exists():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        if path.startswith("api/"):
            raise HTTPException(404, "Ruta de API no encontrada.")
        file = (DIST / path).resolve()
        if path and file.is_file() and DIST.resolve() in file.parents:
            return FileResponse(file)
        return FileResponse(DIST / "index.html")
