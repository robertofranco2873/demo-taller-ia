"""Vista "Mi día" del técnico: sus órdenes, cronómetro e indicadores personales."""
from datetime import date

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException

from api.core import TECNICO, bad_request, clean, records, require_roles
from src import db
from src.analytics import technician_detail
from src.config import PENDING_STATUSES
from src.orders import priority

router = APIRouter(prefix="/api/me", tags=["Técnico: Mi día"])
tech_only = Depends(require_roles(TECNICO))
PRIORITY_ORDER = {"vencida": 0, "hoy": 1, "próxima": 2}


def _own_order(order_id: int, user: dict) -> dict:
    orders = db.load_orders()
    match = orders[orders["id"] == order_id]
    if match.empty:
        raise HTTPException(404, "Orden no encontrada.")
    if int(match.iloc[0]["technician_id"]) != user["technician_id"]:
        raise HTTPException(403, "Esta orden no está asignada a ti.")
    return match.iloc[0].to_dict()


@router.get("/day", summary="Mis órdenes pendientes ordenadas por prioridad")
def my_day(user: dict = tech_only):
    today = date.today()
    orders = db.load_orders()
    mine = orders[(orders["technician_id"] == user["technician_id"]) & orders["status"].isin(PENDING_STATUSES)]
    items = db.load_items()
    services = db.load_services().set_index("id")
    result = []
    for o in mine.itertuples():
        its = items[items["order_id"] == o.id]
        result.append({
            "id": o.id, "folio": o.folio, "status": o.status, "customer": o.customer, "vehicle": o.vehicle,
            "bay": o.bay, "due_date": o.due_date, "scheduled_date": o.scheduled_date, "std_hours": o.std_hours,
            "notes": o.notes, "priority": priority(o.due_date, today), "timer": db.timer_state(int(o.id)),
            "sequence": None if pd.isna(o.priority) else int(o.priority),
            "services": [{"id": int(i.service_id), "code": i.service_code, "name": i.service_name, "qty": int(i.qty),
                          "std_hours": float(i.std_hours),
                          "steps": [s for s in (services.loc[i.service_id, "steps"] or "").split("\n") if s]}
                         for i in its.itertuples()],
        })
    # Si el gerente fijó una secuencia (Secuenciación → Reasignar), manda; si no, vencidas → hoy → próximas.
    result.sort(key=lambda r: (r["sequence"] is None, r["sequence"] or 0, PRIORITY_ORDER[r["priority"]],
                               r["due_date"], r["scheduled_date"]))
    finished_today = orders[(orders["technician_id"] == user["technician_id"])
                            & (orders["finished_at"].dt.date == today)]
    return clean({"date": today, "technician": user["technician"], "orders": result,
                  "finished_today": int(len(finished_today)),
                  "today_hours": float(sum(r["std_hours"] for r in result if r["priority"] != "próxima"))})


@router.post("/orders/{order_id}/start", summary="Iniciar o reanudar el cronómetro")
def start(order_id: int, user: dict = tech_only):
    _own_order(order_id, user)
    try:
        db.start_timer(order_id)
    except ValueError as e:
        raise bad_request(e)
    return db.timer_state(order_id)


@router.post("/orders/{order_id}/pause", summary="Pausar el cronómetro")
def pause(order_id: int, user: dict = tech_only):
    _own_order(order_id, user)
    try:
        db.pause_timer(order_id)
    except ValueError as e:
        raise bad_request(e)
    return db.timer_state(order_id)


@router.post("/orders/{order_id}/finish", summary="Terminar la orden con el tiempo del cronómetro")
def finish(order_id: int, user: dict = tech_only):
    _own_order(order_id, user)
    try:
        result = db.finish_with_timer(order_id)
    except ValueError as e:
        raise bad_request(e)
    goal = db.get_settings()["efficiency_goal"]
    return {**result, "goal": goal, "goal_reached": result["efficiency"] >= goal}


@router.get("/indicators", summary="Mis indicadores personales")
def indicators(user: dict = tech_only):
    orders, items = db.load_orders(), db.load_items()
    start = orders["created_at"].min().date()
    d = technician_detail(orders, items, user["technician"], start, date.today())
    mine = orders[orders["technician_id"] == user["technician_id"]]
    weekly = []
    done = mine.dropna(subset=["finished_at"])
    if len(done):
        g = done.assign(semana=done["finished_at"].dt.to_period("W-SUN").dt.start_time.dt.date).groupby("semana")
        weekly = [{"semana": k, "terminadas": int(len(v)),
                   "eficiencia": float(v["std_hours"].sum() / v["actual_hours"].sum())}
                  for k, v in g if v["actual_hours"].sum() > 0][-12:]
    return clean({**d, "servicios_frecuentes": records(d["servicios_frecuentes"]), "semanal": weekly,
                  "meta": db.get_settings()["efficiency_goal"]})
