"""Búsqueda global (paleta Ctrl+K) y notificaciones por rol."""
from datetime import date, timedelta

from fastapi import APIRouter, Depends

from api.core import ADMIN, ALL_ROLES, RECEPCION, TECNICO, clean, current_user, require_roles
from src import clock
from src import db
from src.capacity import weekly_load
from src.config import PENDING_STATUSES
from src.inventory import inventory_table
from src.workcalendar import week_start

router = APIRouter(prefix="/api", tags=["Búsqueda y notificaciones"])

# Debe coincidir con frontend/src/lib/modules.ts
MODULES = [
    ("mi-dia", "Mi día", "Órdenes de hoy y cronómetro", (TECNICO,)),
    ("mis-indicadores", "Mis indicadores", "Eficiencia y tendencia personal", (TECNICO,)),
    ("servicios", "Servicios", "Catálogo, fichas y estudio de tiempos", ALL_ROLES),
    ("cotizador", "Cotizador", "Cotización por fórmula, Excel, PDF e IA", (ADMIN, RECEPCION)),
    ("ordenes", "Órdenes", "Crear, asignar y avanzar órdenes", (ADMIN, RECEPCION)),
    ("clientes", "Clientes", "Historial por cliente", (ADMIN, RECEPCION)),
    ("dashboard", "Dashboard", "KPIs con detalle por mes, técnico y KPI", (ADMIN,)),
    ("pareto", "Pareto", "80/20 con drill-down", (ADMIN,)),
    ("capacidad", "Capacidad", "Carga vs. capacidad semanal", (ADMIN,)),
    ("secuenciacion", "Secuenciación", "FIFO, SPT, EDD, Gantt y reasignar", (ADMIN,)),
    ("control", "Control estadístico", "Gráficas X̄ y X̄-R", (ADMIN,)),
    ("inventario", "Inventario", "Stock, punto de reorden y EOQ", (ADMIN,)),
    ("usuarios", "Usuarios", "Cuentas y roles", (ADMIN,)),
    ("configuracion", "Configuración", "Parámetros, respaldo y datos demo", (ADMIN,)),
]


@router.get("/search", summary="Busca módulos, servicios, órdenes y técnicos según el rol")
def search(q: str = "", user: dict = Depends(current_user)):
    ql = q.strip().lower()
    role = user["role"]
    out = []
    for key, title, desc, roles in MODULES:
        if role in roles and (not ql or ql in title.lower() or ql in desc.lower()):
            out.append({"type": "modulo", "id": key, "title": title, "subtitle": desc, "path": f"/{key}"})
    if len(ql) >= 2:
        services = db.load_services()
        hit = services[services["name"].str.lower().str.contains(ql) | services["code"].str.lower().str.contains(ql)
                       | services["keywords"].fillna("").str.lower().str.contains(ql)]
        for r in hit.head(6).itertuples():
            out.append({"type": "servicio", "id": int(r.id), "title": f"{r.code} · {r.name}",
                        "subtitle": f"{r.category} · {r.std_hours:.2f} h estándar", "path": f"/servicios/{r.id}"})
        orders = db.load_orders()
        if role == TECNICO:
            orders = orders[orders["technician_id"] == user["technician_id"]]
        hit = orders[orders["folio"].str.lower().str.contains(ql) | orders["customer"].str.lower().str.contains(ql)
                     | orders["vehicle"].fillna("").str.lower().str.contains(ql)]
        for r in hit.sort_values("created_at", ascending=False).head(6).itertuples():
            path = "/mi-dia" if role == TECNICO else f"/ordenes/{r.id}"
            out.append({"type": "orden", "id": int(r.id), "title": f"{r.folio} · {r.customer}",
                        "subtitle": f"{r.status} · {r.vehicle}", "path": path})
        if role != TECNICO:
            techs = db.load_technicians()
            for r in techs[techs["name"].str.lower().str.contains(ql)].itertuples():
                path = f"/dashboard?tecnico={r.id}" if role == ADMIN else f"/ordenes?tecnico={r.id}"
                out.append({"type": "tecnico", "id": int(r.id), "title": r.name, "subtitle": r.specialty,
                            "path": path})
    return out[:25]


@router.get("/notifications", summary="Avisos según el rol")
def notifications(user: dict = Depends(require_roles(*ALL_ROLES))):
    today = clock.today()
    orders = db.load_orders()
    pending = orders[orders["status"].isin(PENDING_STATUSES)]
    notes = []
    if user["role"] == TECNICO:
        mine = pending[pending["technician_id"] == user["technician_id"]]
        late = mine[mine["due_date"] < today]
        if len(late):
            notes.append({"level": "critical", "title": f"{len(late)} orden(es) vencida(s)",
                          "detail": ", ".join(late["folio"].head(5)), "path": "/mi-dia"})
        due = mine[mine["due_date"] == today]
        if len(due):
            notes.append({"level": "warning", "title": f"{len(due)} orden(es) vencen hoy",
                          "detail": ", ".join(due["folio"].head(5)), "path": "/mi-dia"})
        return clean(notes)

    late = pending[pending["due_date"] < today]
    if len(late):
        notes.append({"level": "critical", "title": f"{len(late)} órdenes vencidas",
                      "detail": "Pendientes con fecha compromiso pasada", "path": "/ordenes?filtro=vencidas"})
    ready = orders[orders["status"] == "terminada"]
    if len(ready):
        notes.append({"level": "info", "title": f"{len(ready)} órdenes listas para entregar",
                      "detail": "Avisa al cliente", "path": "/ordenes?estado=terminada"})
    if user["role"] == ADMIN:
        load = weekly_load(orders, db.load_technicians()["name"].tolist(), week_start(today))
        over = load[load["sobrecarga"]]
        if len(over):
            notes.append({"level": "warning", "title": f"Sobrecarga: {len(over)} técnico(s) esta semana",
                          "detail": ", ".join(over["technician"]), "path": "/capacidad"})
        inv = inventory_table(db.load_parts(), db.load_consumption(), today - timedelta(days=90), today,
                              db.get_settings()["service_level"])
        low = inv[inv["estado"] != "ok"]
        if len(low):
            notes.append({"level": "warning", "title": f"{len(low)} refacciones por reordenar",
                          "detail": ", ".join(low["name"].head(3)), "path": "/inventario"})
    return clean(notes)
