from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from api.core import ADMIN, ALL_ROLES, STAFF, bad_request, clean, records, require_roles
from src import db
from src.time_study import normal_time, observed_average, required_observations, standard_time

router = APIRouter(prefix="/api", tags=["Catálogo y estudio de tiempos"])


def _service_rows():
    df = db.load_services()
    df["steps"] = df["steps"].fillna("").map(lambda s: [x for x in s.split("\n") if x])
    return df


@router.get("/services", summary="Catálogo con tiempo normal y estándar calculados")
def list_services(_: dict = Depends(require_roles(*ALL_ROLES))):
    return records(_service_rows())


@router.get("/services/{service_id}", summary="Ficha del servicio: pasos, refacciones y tiempos reales")
def service_detail(service_id: int, _: dict = Depends(require_roles(*ALL_ROLES))):
    df = _service_rows()
    match = df[df["id"] == service_id]
    if match.empty:
        raise HTTPException(404, "Servicio no encontrado.")
    items = db.load_items()
    done = items[(items["service_id"] == service_id) & items["actual_hours"].notna()]
    per_unit = (done["actual_hours"] / done["qty"]) if len(done) else done["actual_hours"]
    return clean({
        **records(match)[0],
        "parts": records(db.load_service_parts(service_id)),
        "stats": {"veces_realizado": int(len(done)),
                  "real_promedio_h": float(per_unit.mean()) if len(done) else None},
    })


class ServiceIn(BaseModel):
    name: str = Field(min_length=2)
    category: str = ""
    observed_avg_min: float = Field(gt=0)
    rating_factor: float = Field(gt=0, le=2)
    allowance_pct: float = Field(ge=0, le=1)
    steps: list[str] = []


class NewServiceIn(ServiceIn):
    code: str = Field(min_length=2, max_length=10)
    keywords: str = ""


@router.put("/services/{service_id}", summary="Editar servicio (solo administrador)")
def update_service(service_id: int, body: ServiceIn, _: dict = Depends(require_roles(ADMIN))):
    try:
        db.update_service(service_id, body.name, body.category, body.observed_avg_min,
                          body.rating_factor, body.allowance_pct)
        db.update_service_steps(service_id, body.steps)
    except ValueError as e:
        raise bad_request(e)
    return {"ok": True}


@router.post("/services", status_code=201, summary="Agregar servicio (solo administrador)")
def add_service(body: NewServiceIn, _: dict = Depends(require_roles(ADMIN))):
    try:
        sid = db.add_service(body.code.upper(), body.name, body.category, body.observed_avg_min,
                             body.rating_factor, body.allowance_pct, body.keywords)
        db.update_service_steps(sid, body.steps)
    except Exception as e:  # sqlite IntegrityError (código duplicado) o validación
        raise bad_request(e)
    return {"id": sid}


class TimeStudyIn(BaseModel):
    observations: list[float] = Field(min_length=1)
    rating_factor: float = Field(gt=0, le=2)
    allowance_pct: float = Field(ge=0, le=1)
    confidence: float = 0.95
    error: float = 0.05


@router.post("/time-study", summary="Calcula TN, TS y observaciones necesarias")
def time_study(body: TimeStudyIn, _: dict = Depends(require_roles(*ALL_ROLES))):
    try:
        avg = observed_average(body.observations)
        tn = normal_time(avg, body.rating_factor)
        ts = standard_time(tn, body.allowance_pct)
        needed = required_observations(body.observations, body.confidence, body.error) \
            if len(body.observations) >= 2 else None
    except ValueError as e:
        raise bad_request(e)
    return {"promedio_min": avg, "normal_min": tn, "estandar_min": ts, "estandar_h": ts / 60,
            "observaciones": len(body.observations), "observaciones_necesarias": needed,
            "suficientes": needed is not None and len(body.observations) >= needed}


@router.get("/parts", summary="Refacciones con precio y stock")
def list_parts(_: dict = Depends(require_roles(*STAFF))):
    return records(db.load_parts())


@router.get("/technicians", summary="Técnicos")
def technicians(_: dict = Depends(require_roles(*STAFF))):
    return records(db.load_technicians())


@router.get("/bays", summary="Bahías")
def bays(_: dict = Depends(require_roles(*STAFF))):
    return records(db.load_bays())
