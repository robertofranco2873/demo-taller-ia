from datetime import date, datetime, timedelta

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from api.core import ADMIN, bad_request, clean, parse_range, records, require_roles
from src import analytics, db, kpis
from src.capacity import weekly_load
from src.config import PENDING_STATUSES
from src.pareto import pareto_table, vital_few
from src.sequencing import MANUAL, MANUAL_LABEL, RULES, Job, compare_rules_resources, schedule_resources
from src.spc import control_chart, xbar_r_chart
from src.workcalendar import add_work_hours, week_start, work_day_segments, work_hours_until

router = APIRouter(prefix="/api", tags=["Análisis (administrador)"])
admin_only = Depends(require_roles(ADMIN))


def _data(start: date | None, end: date | None):
    all_orders = db.load_orders()
    s, e = parse_range(start, end, all_orders)
    orders = kpis.filter_by_date(all_orders, s, e)
    items = kpis.filter_by_date(db.load_items(), s, e)
    return orders, items, s, e


# ---------- dashboard ----------

@router.get("/dashboard", summary="KPIs y datos de gráficas del dashboard")
def dashboard(start: date | None = None, end: date | None = None, _: dict = admin_only):
    orders, items, s, e = _data(start, end)
    bays = db.load_bays()["name"].tolist()
    summary = kpis.summary(orders, items, bays, s, e)
    eff = kpis.efficiency_by_technician(items)
    tech_ids = dict(zip(db.load_technicians()["name"], db.load_technicians()["id"]))
    eff["technician_id"] = eff["technician"].map(tech_ids)
    monthly = analytics.monthly_kpis(orders, items, len(bays))
    pending = orders[orders["status"].isin(PENDING_STATUSES)].sort_values("due_date")
    return clean({
        "range": {"start": s, "end": e,
                  "min": db.load_orders()["created_at"].min().date(), "max": date.today()},
        "kpis": {
            "ingresos": summary["ingresos_totales"], "ticket": summary["ticket_promedio"],
            "lead_time": summary["lead_time_promedio_dias"],
            "eficiencia": float(eff["std_hours"].sum() / eff["actual_hours"].sum()) if len(eff) else None,
            "utilizacion": float(kpis.bay_utilization(orders, bays, s, e)["utilizacion"].mean()),
            "backlog": summary["backlog_ordenes"], "backlog_horas": summary["backlog_horas_estandar"],
        },
        "definitions": analytics.KPI_DEFINITIONS,
        "efficiency_goal": db.get_settings()["efficiency_goal"],
        "monthly": records(monthly),
        "efficiency": records(eff),
        "bays": records(kpis.bay_utilization(orders, bays, s, e)),
        "backlog": records(pending[["id", "folio", "status", "technician", "due_date", "std_hours"]]),
        "summary": summary,
    })


@router.get("/dashboard/month/{month}", summary="Detalle de un mes (AAAA-MM)")
def dashboard_month(month: str, _: dict = admin_only):
    try:
        d = analytics.month_detail(db.load_orders(), db.load_items(), month, len(db.load_bays()))
    except ValueError as e:
        raise bad_request(e)
    cols = ["id", "folio", "status", "customer", "technician", "total", "created_at"]
    return clean({**d, "ordenes": records(d["ordenes"][cols].sort_values("created_at")),
                  "ingresos_por_servicio": records(d["ingresos_por_servicio"]),
                  "tecnicos": records(d["tecnicos"])})


@router.get("/dashboard/technician/{technician_id}", summary="Detalle de un técnico")
def dashboard_technician(technician_id: int, start: date | None = None, end: date | None = None,
                         _: dict = admin_only):
    techs = db.load_technicians().set_index("id")
    if technician_id not in techs.index:
        raise HTTPException(404, "Técnico no encontrado.")
    orders, items, s, e = _data(start, end)
    d = analytics.technician_detail(orders, items, techs.loc[technician_id, "name"], s, e)
    return clean({**d, "servicios_frecuentes": records(d["servicios_frecuentes"]),
                  "meta": db.get_settings()["efficiency_goal"]})


@router.get("/dashboard/kpi/{key}", summary="Fórmula, cálculo y tendencia de un KPI")
def dashboard_kpi(key: str, start: date | None = None, end: date | None = None, _: dict = admin_only):
    orders, items, s, e = _data(start, end)
    try:
        return clean(analytics.kpi_detail(key, orders, items, db.load_bays()["name"].tolist(), s, e))
    except ValueError as err:
        raise HTTPException(404, str(err))


# ---------- Pareto con drill-down ----------

@router.get("/pareto", summary="Nivel 1: Pareto de servicios por ingreso o frecuencia")
def pareto(by: str = Query("ingreso", pattern="^(ingreso|frecuencia)$"), start: date | None = None,
           end: date | None = None, _: dict = admin_only):
    _, items, s, e = _data(start, end)
    items = items[items["status"].isin(["terminada", "entregada"])]
    table = pareto_table(items, "service_name", "line_subtotal" if by == "ingreso" else None)
    ids = dict(zip(db.load_services()["name"], db.load_services()["id"]))
    table["service_id"] = table["service_name"].map(ids)
    share = float(table.loc[table["clase"] == "A", "pct"].sum()) if len(table) else 0.0
    return clean({"by": by, "range": {"start": s, "end": e}, "rows": records(table),
                  "vital_few": vital_few(table) if len(table) else 0, "total": len(table), "share": share})


@router.get("/pareto/service/{service_id}", summary="Nivel 2: detalle del servicio")
def pareto_service(service_id: int, start: date | None = None, end: date | None = None, _: dict = admin_only):
    orders, items, s, e = _data(start, end)
    services = db.load_services().set_index("id")
    if service_id not in services.index:
        raise HTTPException(404, "Servicio no encontrado.")
    d = analytics.service_detail(orders, items, service_id)
    ctrl = None
    values = d["valores_control"]
    if len(values) >= 2:
        df, lim = control_chart(values["real_unit"].tolist())
        df["folio"] = values["folio"].values
        df["technician"] = values["technician"].values
        ctrl = {"points": records(df), "limits": lim}
    return clean({**{k: v for k, v in d.items() if k != "valores_control"},
                  "service": {"id": service_id, "code": services.loc[service_id, "code"],
                              "name": services.loc[service_id, "name"],
                              "std_hours": services.loc[service_id, "std_hours"]},
                  "tecnicos": records(d["tecnicos"]), "control": ctrl})


@router.get("/pareto/service/{service_id}/orders", summary="Nivel 3: órdenes del servicio")
def pareto_service_orders(service_id: int, start: date | None = None, end: date | None = None,
                          _: dict = admin_only):
    orders, items, s, e = _data(start, end)
    it = items[items["service_id"] == service_id][["order_id", "qty", "std_hours", "actual_hours", "line_subtotal"]]
    df = it.merge(orders[["id", "folio", "status", "customer", "vehicle", "technician", "created_at", "total"]],
                  left_on="order_id", right_on="id").sort_values("created_at", ascending=False)
    return records(df.drop(columns=["id"]))


# ---------- carga vs. capacidad ----------

@router.get("/capacity", summary="Carga vs. capacidad de una semana")
def capacity(week: date | None = None, _: dict = admin_only):
    orders = db.load_orders()
    techs = db.load_technicians()
    monday = week_start(week or date.today())
    load = weekly_load(orders, techs["name"].tolist(), monday)
    load["technician_id"] = techs["id"].values
    weeks = []
    this = week_start(date.today())
    for k in range(-8, 4):
        w = this + timedelta(weeks=k)
        wl = weekly_load(orders, techs["name"].tolist(), w)
        weeks.append({"week": w, "rows": records(wl[["technician", "utilizacion", "sobrecarga"]])})
    return clean({"week": monday, "rows": records(load), "overview": weeks})


# ---------- secuenciación ----------

def _jobs(mode: str, technician_id: int | None, priorities: dict[str, int] | None,
          reassign: dict[str, int] | None = None):
    """Órdenes pendientes como trabajos.

    Prioridad: la enviada por el usuario o la guardada en la orden.
    reassign = {folio: id de técnico}: mueve la orden a otro técnico y la fija (se respeta en cualquier alcance).
    """
    orders = db.load_orders()
    pending = orders[orders["status"].isin(PENDING_STATUSES)]
    techs = db.load_technicians()
    names = techs["name"].tolist()
    if mode == "technician":
        if technician_id is None or technician_id not in set(techs["id"]):
            raise HTTPException(400, "Indica un técnico válido.")
        name = techs.set_index("id").loc[technician_id, "name"]
        pending = pending[pending["technician"] == name]
        names = [name]
    now = add_work_hours(datetime.now().replace(microsecond=0), 0)
    tech_name = dict(zip(techs["id"], techs["name"]))
    moves = {}
    for folio, tid in (reassign or {}).items():
        if tid not in tech_name:
            raise HTTPException(400, f"Técnico inválido para {folio}.")
        moves[folio] = tech_name[tid]
    if mode == "technician" and any(moves.get(f, n) not in names for f, n in zip(pending["folio"], pending["technician"])):
        raise HTTPException(400, "En «Por técnico» no se pueden mover órdenes a otro técnico; usa «Respetar asignación».")

    def prio(r):
        if priorities is not None:
            return priorities.get(r.folio)
        return None if pd.isna(r.priority) else float(r.priority)

    jobs = [Job(r.folio, float(r.std_hours), work_hours_until(now, r.due_date), r.created_at.timestamp(),
                moves.get(r.folio, r.technician), prio(r), pinned=r.folio in moves) for r in pending.itertuples()]
    return jobs, names, now, pending


def _schedule(rule: str, mode: str, technician_id: int | None, priorities: dict[str, int] | None = None,
              reassign: dict[str, int] | None = None):
    if rule not in RULES and rule != MANUAL:
        raise HTTPException(400, f"Regla desconocida: {rule}")
    jobs, names, now, pending = _jobs(mode, technician_id, priorities, reassign)
    bays = db.load_bays()["name"].tolist()
    respect = mode != "shop"
    sched = schedule_resources(jobs, rule, names, bays, respect) if jobs else None
    return jobs, names, bays, now, pending, respect, sched


def _sequencing_response(rule: str, mode: str, technician_id: int | None, priorities: dict[str, int] | None,
                         reassign: dict[str, int] | None = None):
    jobs, names, bays, now, pending, respect, sched = _schedule(rule, mode, technician_id, priorities, reassign)
    rules = {**RULES, MANUAL: MANUAL_LABEL}
    has_manual = any(j.priority is not None for j in jobs)
    if not jobs:
        return {"jobs": 0, "comparison": [], "schedule": [], "days": [], "now": now.isoformat(), "rules": rules,
                "technicians": names, "has_manual": False}
    info = pending.set_index("folio")
    sched["inicio"] = [add_work_hours(now, h).isoformat() for h in sched["inicio_h"]]
    sched["fin"] = [add_work_hours(now, h).isoformat() for h in sched["fin_h"]]
    sched["compromiso"] = [info.loc[f, "due_date"] for f in sched["orden"]]
    sched["cliente"] = [info.loc[f, "customer"] for f in sched["orden"]]
    sched["vehiculo"] = [info.loc[f, "vehicle"] for f in sched["orden"]]
    sched["estado"] = [info.loc[f, "status"] for f in sched["orden"]]
    sched["tecnico_actual"] = [info.loc[f, "technician"] for f in sched["orden"]]  # el guardado en la orden
    sched["prioridad_guardada"] = [None if pd.isna(info.loc[f, "priority"]) else int(info.loc[f, "priority"])
                                   for f in sched["orden"]]
    horizon = float(sched["fin_h"].max())
    dias = ["lun", "mar", "mié", "jue", "vie", "sáb", "dom"]
    days = [{**d, "label": f"{dias[d['date'].weekday()]} {d['date']:%d/%m}"} for d in work_day_segments(now, horizon)]
    return clean({"jobs": len(jobs), "hours": sum(j.processing for j in jobs), "now": now, "rules": rules,
                  "comparison": records(compare_rules_resources(jobs, names, bays, respect, include_manual=has_manual)),
                  "schedule": records(sched), "days": days, "technicians": names, "has_manual": has_manual,
                  "mode": mode, "rule": rule})


@router.get("/sequencing", summary="Comparativa FIFO/SPT/EDD (y manual si hay prioridades guardadas) y programa")
def sequencing(rule: str = "EDD", mode: str = Query("assigned", pattern="^(assigned|shop|technician)$"),
               technician_id: int | None = None, _: dict = admin_only):
    return _sequencing_response(rule, mode, technician_id, None)


class SimulateIn(BaseModel):
    rule: str = MANUAL
    mode: str = Field("assigned", pattern="^(assigned|shop|technician)$")
    technician_id: int | None = None
    priorities: dict[str, int] | None = Field(None, description="{folio: prioridad}; 1 = primero")
    technicians: dict[str, int] | None = Field(None, description="{folio: id de técnico} para mover órdenes")


@router.post("/sequencing/simulate", summary="Simula el programa con prioridades manuales (no guarda nada)")
def sequencing_simulate(body: SimulateIn, _: dict = admin_only):
    return _sequencing_response(body.rule, body.mode, body.technician_id, body.priorities, body.technicians)


class ApplyIn(SimulateIn):
    rule: str = "EDD"
    mode: str = "shop"


@router.post("/sequencing/apply", summary="Reasignar: aplica la propuesta (técnico, bahía, fecha y prioridad)")
def sequencing_apply(body: ApplyIn, _: dict = admin_only):
    jobs, names, bays, now, pending, respect, sched = _schedule(body.rule, body.mode, body.technician_id,
                                                                body.priorities, body.technicians)
    if sched is None:
        return {"updated": 0}
    tech_id = dict(zip(db.load_technicians()["name"], db.load_technicians()["id"]))
    bay_id = dict(zip(db.load_bays()["name"], db.load_bays()["id"]))
    order_id = dict(zip(pending["folio"], pending["id"]))
    n = db.apply_assignments([
        {"order_id": int(order_id[r.orden]), "technician_id": int(tech_id[r.recurso]),
         "bay_id": int(bay_id[r.bahia]), "scheduled_date": add_work_hours(now, r.inicio_h).date(),
         "priority": int(r.posicion)}
        for r in sched.itertuples()])
    return {"updated": n}


# ---------- control estadístico ----------

def _spc_values(service_id: int, technician_id: int | None, last_n: int):
    items = db.load_items()
    items = items[(items["service_id"] == service_id) & items["actual_hours"].notna()].sort_values("created_at")
    if technician_id:
        items = items[items["technician_id"] == technician_id]
    items = items.tail(last_n)
    return items, (items["actual_hours"] / items["qty"]).tolist()


@router.get("/spc/services", summary="Servicios con suficientes tiempos reales")
def spc_services(_: dict = admin_only):
    items = db.load_items().dropna(subset=["actual_hours"])
    counts = items.groupby(["service_id", "service_name"]).size().rename("registros").reset_index()
    return records(counts[counts["registros"] >= 10].sort_values("registros", ascending=False))


@router.get("/spc/individuals", summary="Gráfica X̄ de individuales ±3σ")
def spc_individuals(service_id: int, technician_id: int | None = None, last_n: int = 50, _: dict = admin_only):
    items, values = _spc_values(service_id, technician_id, last_n)
    if len(values) < 2:
        raise HTTPException(400, "Se necesitan al menos 2 registros de tiempo real.")
    df, lim = control_chart(values)
    df["folio"] = items["folio"].values
    df["technician"] = items["technician"].values
    df["fecha"] = items["created_at"].dt.date.astype(str).values
    std = db.load_services().set_index("id").loc[service_id, "std_hours"]
    return clean({"points": records(df), "limits": lim, "std_hours": std,
                  "signals": int((df["fuera_de_limites"] | df["racha"]).sum())})


@router.get("/spc/xbar-r", summary="Gráfica X̄-R por subgrupos")
def spc_xbar_r(service_id: int, technician_id: int | None = None, subgroup: int = 5, last_n: int = 100,
               _: dict = admin_only):
    _, values = _spc_values(service_id, technician_id, last_n)
    try:
        df, lim = xbar_r_chart(values, subgroup)
    except ValueError as e:
        raise bad_request(e)
    return clean({"subgroups": records(df), "limits": lim})
