"""AutoServicio Demo — API (datos ficticios).

Desarrollo:  uvicorn api.main:app --reload       Documentación:  http://localhost:8000/docs
En producción también sirve el frontend compilado (frontend/dist).
"""
import asyncio
import logging
from contextlib import asynccontextmanager, suppress
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from api.routers import admin, ai, analytics, auth, catalog, misc, orders, quotes, tech
from src import config, db
from src.seed import seed_database

DIST = config.ROOT_DIR / "frontend" / "dist"
log = logging.getLogger("autoservicio")
_state = {"last_reset": None}


def _reset_demo() -> None:
    seed_database()
    _state["last_reset"] = datetime.now(timezone.utc)
    log.info("Modo demo: base restablecida con datos ficticios.")


async def _demo_reset_loop() -> None:
    while True:
        await asyncio.sleep(config.DEMO_RESET_HOURS * 3600)
        try:
            await asyncio.to_thread(_reset_demo)
        except Exception:  # no tumbar el servidor si una regeneración falla
            log.exception("Modo demo: falló el restablecimiento de la base")


@asynccontextmanager
async def lifespan(_: FastAPI):
    task = None
    if config.demo_mode():
        _reset_demo()  # la demo pública siempre arranca con datos frescos
        task = asyncio.create_task(_demo_reset_loop())
    else:
        db.ensure_database()  # crea la base con datos ficticios si no existe
    yield
    if task:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task


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


@app.get("/api/app-info", tags=["Sistema"], summary="Modo demo y restablecimiento (público)")
def app_info():
    demo = config.demo_mode()
    last = _state["last_reset"]
    return {
        "demo_mode": demo,
        "reset_hours": config.DEMO_RESET_HOURS if demo else None,
        "last_reset": last.isoformat() if demo and last else None,
        "next_reset": (last + timedelta(hours=config.DEMO_RESET_HOURS)).isoformat() if demo and last else None,
    }


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
