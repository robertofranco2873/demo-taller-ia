import shutil
import sqlite3
import tempfile
from datetime import date, timedelta
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field

from api.core import ADMIN, STAFF, bad_request, clean, records, require_roles
from src import config, db
from src.inventory import inventory_table
from src.security import ROLE_LABELS, hash_password
from src.seed import seed_database

router = APIRouter(prefix="/api", tags=["Administración e inventario"])
admin_only = Depends(require_roles(ADMIN))


# ---------- inventario ----------

@router.get("/inventory", summary="Inventario con stock de seguridad, punto de reorden y EOQ")
def inventory(days: int = 90, _: dict = admin_only):
    end = date.today()
    start = end - timedelta(days=days)
    table = inventory_table(db.load_parts(), db.load_consumption(), start, end, db.get_settings()["service_level"])
    return clean({"rows": records(table), "service_level": db.get_settings()["service_level"],
                  "window_days": days,
                  "formulas": {"stock_seguridad": "SS = z · σd · √L", "punto_reorden": "ROP = d̄ · L + SS",
                               "eoq": "EOQ = √(2 · D · S / H), S = $150 por pedido, H = 25 % del precio al año"}})


@router.get("/inventory/{part_id}/movements", summary="Movimientos de una refacción")
def movements(part_id: int, _: dict = admin_only):
    return clean(db.load_movements(part_id))


class MovementIn(BaseModel):
    qty: float
    kind: str = Field(pattern="^(entrada|salida|ajuste)$")
    note: str = ""


@router.post("/inventory/{part_id}/movements", summary="Registrar entrada, salida o ajuste")
def add_movement(part_id: int, body: MovementIn, _: dict = admin_only):
    try:
        return {"stock": db.add_movement(part_id, body.qty, body.kind, body.note)}
    except ValueError as e:
        raise bad_request(e)


class PartIn(BaseModel):
    price: float = Field(ge=0)
    lead_time_days: float = Field(ge=0, le=60)


@router.put("/parts/{part_id}", summary="Editar precio y tiempo de entrega")
def update_part(part_id: int, body: PartIn, _: dict = admin_only):
    db.update_part(part_id, body.price, body.lead_time_days)
    return {"ok": True}


# ---------- usuarios ----------

@router.get("/users", summary="Usuarios")
def users(_: dict = admin_only):
    return {"users": db.list_users(), "roles": ROLE_LABELS}


class UserIn(BaseModel):
    username: str = Field(min_length=3, max_length=30, pattern=r"^[a-zA-Z0-9._-]+$")
    name: str = Field(min_length=2)
    role: str
    password: str = Field(min_length=6)
    technician_id: int | None = None


class UserUpdate(BaseModel):
    name: str = Field(min_length=2)
    role: str
    technician_id: int | None = None
    active: bool = True
    password: str | None = None


@router.post("/users", status_code=201, summary="Crear usuario")
def create_user(body: UserIn, _: dict = admin_only):
    try:
        return {"id": db.create_user(body.username, body.name, body.role, hash_password(body.password),
                                     body.technician_id)}
    except ValueError as e:
        raise bad_request(e)


@router.put("/users/{user_id}", summary="Editar usuario")
def update_user(user_id: int, body: UserUpdate, user: dict = admin_only):
    if user_id == user["id"] and (body.role != "admin" or not body.active):
        raise HTTPException(400, "No puedes quitarte el rol de administrador ni desactivarte.")
    try:
        db.update_user(user_id, body.name, body.role, body.technician_id, body.active,
                       hash_password(body.password) if body.password else None)
    except ValueError as e:
        raise bad_request(e)
    return {"ok": True}


@router.delete("/users/{user_id}", summary="Eliminar usuario")
def delete_user(user_id: int, user: dict = admin_only):
    if user_id == user["id"]:
        raise HTTPException(400, "No puedes eliminar tu propio usuario.")
    db.delete_user(user_id)
    return {"ok": True}


# ---------- configuración ----------

@router.get("/settings", summary="Parámetros (tarifa, margen, meta de eficiencia, nivel de servicio)")
def get_settings(_: dict = Depends(require_roles(*STAFF))):
    return db.get_settings()


class SettingsIn(BaseModel):
    labor_rate: float = Field(ge=0)
    margin_pct: float = Field(ge=0, le=3)
    efficiency_goal: float = Field(ge=0.5, le=1.5)
    service_level: float = Field(ge=0.5, lt=1)


@router.put("/settings", summary="Guardar parámetros")
def put_settings(body: SettingsIn, _: dict = admin_only):
    try:
        db.save_settings(body.labor_rate, body.margin_pct, body.efficiency_goal, body.service_level)
    except ValueError as e:
        raise bad_request(e)
    return db.get_settings()


@router.post("/admin/reseed", summary="Regenerar los datos ficticios (borra todo)")
def reseed(_: dict = admin_only):
    return seed_database()


@router.get("/admin/backup", summary="Descargar respaldo de la base SQLite", response_class=Response)
def backup(_: dict = admin_only):
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "respaldo.db"
        src, dst = sqlite3.connect(config.DB_PATH), sqlite3.connect(target)
        try:
            src.backup(dst)
        finally:  # en Windows hay que cerrar antes de leer/borrar el archivo
            src.close()
            dst.close()
        data = target.read_bytes()
    return Response(data, media_type="application/x-sqlite3",
                    headers={"Content-Disposition": f'attachment; filename="taller_{date.today():%Y%m%d}.db"'})


@router.post("/admin/restore", summary="Restaurar la base desde un respaldo")
async def restore(file: UploadFile = File(...), _: dict = admin_only):
    data = await file.read()
    if not data.startswith(b"SQLite format 3\x00"):
        raise HTTPException(400, "El archivo no es una base SQLite válida.")
    with tempfile.TemporaryDirectory() as tmp:
        candidate = Path(tmp) / "nueva.db"
        candidate.write_bytes(data)
        if db.is_empty(candidate):
            raise HTTPException(400, "El respaldo no es de esta versión de la app o está vacío.")
        if not db.list_users(candidate):
            raise HTTPException(400, "El respaldo no tiene usuarios.")
        shutil.copyfile(candidate, config.DB_PATH)
    return {"ok": True}
