from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from api.core import ALL_ROLES, STAFF, TECNICO, bad_request, clean, records, require_roles
from src import db
from src.orders import next_status, time_variance

router = APIRouter(prefix="/api", tags=["Órdenes y clientes"])

LIST_COLS = ["id", "folio", "status", "customer", "phone", "vehicle", "technician", "technician_id", "bay",
             "bay_id", "created_at", "scheduled_date", "due_date", "std_hours", "actual_hours", "total"]


@router.get("/orders", summary="Órdenes con filtros")
def list_orders(status: str | None = None, q: str | None = None, technician_id: int | None = None,
                service_id: int | None = None, limit: int = 500,
                _: dict = Depends(require_roles(*STAFF))):
    df = db.load_orders()
    if status:
        df = df[df["status"].isin(status.split(","))]
    if technician_id:
        df = df[df["technician_id"] == technician_id]
    if service_id:
        items = db.load_items()
        df = df[df["id"].isin(items[items["service_id"] == service_id]["order_id"])]
    if q:
        ql = q.lower()
        df = df[df["folio"].str.lower().str.contains(ql) | df["customer"].str.lower().str.contains(ql)
                | df["vehicle"].fillna("").str.lower().str.contains(ql)]
    df = df.sort_values("created_at", ascending=False).head(limit).copy()
    df["vencida"] = df["status"].isin(["recibida", "en proceso"]) & (df["due_date"] < date.today())
    return records(df[LIST_COLS + ["vencida"]])


@router.get("/orders/{order_id}", summary="Detalle de una orden")
def order_detail(order_id: int, user: dict = Depends(require_roles(*ALL_ROLES))):
    try:
        data = db.get_order(order_id)
    except ValueError:
        raise HTTPException(404, "Orden no encontrada.")
    order = data["order"]
    if user["role"] == TECNICO and order["technician_id"] != user["technician_id"]:
        raise HTTPException(403, "Solo puedes consultar tus propias órdenes.")
    actual = order.get("actual_hours")
    variance = time_variance(order["std_hours"], actual) if actual and actual == actual else None
    return clean({"order": order, "items": data["items"], "timer": db.timer_state(order_id),
                  "next_status": next_status(order["status"]), "variance": variance})


class OrderIn(BaseModel):
    customer: str = Field(min_length=2)
    phone: str = ""
    vehicle: str = ""
    items: list[dict] = Field(min_length=1, description="[{service_id, qty}]")
    technician_id: int
    bay_id: int
    scheduled_date: date
    due_date: date
    notes: str = ""


@router.post("/orders", status_code=201, summary="Crear orden (precio calculado por fórmula)")
def create_order(body: OrderIn, _: dict = Depends(require_roles(*STAFF))):
    try:
        qty = {int(i["service_id"]): int(i.get("qty", 1)) for i in body.items}
        folio = db.create_order(body.customer, body.phone, body.vehicle, qty, body.technician_id,
                                body.bay_id, body.due_date, body.scheduled_date, body.notes)
    except (ValueError, KeyError) as e:
        raise bad_request(e)
    return {"folio": folio}


class AssignmentIn(BaseModel):
    technician_id: int
    bay_id: int
    scheduled_date: date


@router.patch("/orders/{order_id}/assignment", summary="Asignar técnico, bahía y fecha")
def assign(order_id: int, body: AssignmentIn, _: dict = Depends(require_roles(*STAFF))):
    db.update_assignment(order_id, body.technician_id, body.bay_id, body.scheduled_date)
    return {"ok": True}


class AdvanceIn(BaseModel):
    status: str
    actual_hours: dict[int, float] | None = None


@router.post("/orders/{order_id}/advance", summary="Avanzar estado (al terminar: tiempo real por servicio)")
def advance(order_id: int, body: AdvanceIn, _: dict = Depends(require_roles(*STAFF))):
    try:
        db.advance_order(order_id, body.status, body.actual_hours)
    except ValueError as e:
        raise bad_request(e)
    return {"ok": True}


@router.get("/customers", summary="Clientes (derivados de las órdenes)")
def customers(q: str | None = None, _: dict = Depends(require_roles(*STAFF))):
    df = db.load_customers()
    if q:
        ql = q.lower()
        df = df[df["customer"].str.lower().str.contains(ql) | df["phone"].fillna("").str.contains(ql)
                | df["vehiculos"].str.lower().str.contains(ql)]
    return records(df)


@router.get("/customers/orders", summary="Historial de un cliente")
def customer_orders(customer: str, phone: str = "", _: dict = Depends(require_roles(*STAFF))):
    df = db.load_orders()
    df = df[(df["customer"] == customer) & (df["phone"].fillna("") == phone)]
    return records(df.sort_values("created_at", ascending=False)[LIST_COLS])
