"""Análisis para las ventanas de detalle (mes, técnico, KPI) y el drill-down de Pareto. Funciones puras."""
from datetime import date

import pandas as pd

from src import kpis
from src.config import CLOSED_STATUSES
from src.workcalendar import available_hours

KPI_DEFINITIONS = {
    "ingresos": {"nombre": "Ingresos", "formula": "Σ total (con IVA) de órdenes terminadas o entregadas",
                 "explicacion": "Dinero facturado por órdenes cerradas, según su fecha de recepción."},
    "ticket": {"nombre": "Ticket promedio", "formula": "Ingresos ÷ número de órdenes cerradas",
               "explicacion": "Cuánto gasta en promedio un cliente por visita."},
    "lead_time": {"nombre": "Lead time promedio", "formula": "Promedio de (fecha de entrega − fecha de recepción)",
                  "explicacion": "Días que el auto pasa en el taller desde que llega hasta que se entrega."},
    "eficiencia": {"nombre": "Eficiencia del taller", "formula": "Σ horas estándar ÷ Σ horas reales",
                   "explicacion": "Más de 100 % = se trabaja más rápido que el estándar del estudio de tiempos."},
    "utilizacion": {"nombre": "Utilización de bahías",
                    "formula": "Σ horas reales usadas ÷ (bahías × días laborables × 8 h)",
                    "explicacion": "Qué parte del tiempo disponible de las bahías se usó."},
    "backlog": {"nombre": "Backlog", "formula": "Órdenes en estado recibida o en proceso (y sus horas estándar)",
                "explicacion": "Trabajo pendiente que ya está en el taller."},
}


def _month(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series).dt.to_period("M")


def _month_bounds(period: pd.Period) -> tuple[date, date]:
    return period.start_time.date(), period.end_time.date()


def monthly_kpis(orders: pd.DataFrame, items: pd.DataFrame, n_bays: int) -> pd.DataFrame:
    """Una fila por mes de recepción con los KPIs del dashboard (para tendencias)."""
    if orders.empty:
        return pd.DataFrame(columns=["mes", "ingresos", "ordenes", "ticket", "lead_time", "eficiencia",
                                     "utilizacion", "recibidas"])
    o = orders.assign(mes=_month(orders["created_at"]))
    i = items.assign(mes=_month(items["created_at"]))
    rows = []
    for mes, grp in o.groupby("mes"):
        closed = grp[grp["status"].isin(CLOSED_STATUSES)]
        done = i[(i["mes"] == mes) & i["actual_hours"].notna()]
        start, end = _month_bounds(mes)
        cap = available_hours(start, end, resources=n_bays)
        rows.append({
            "mes": mes.strftime("%Y-%m"),
            "recibidas": int(len(grp)),
            "ordenes": int(len(closed)),
            "ingresos": float(closed["total"].sum()),
            "ticket": float(closed["total"].mean()) if len(closed) else 0.0,
            "lead_time": kpis.average_lead_time_days(grp),
            "eficiencia": float(done["std_hours"].sum() / done["actual_hours"].sum()) if len(done) else None,
            "utilizacion": float(grp["actual_hours"].fillna(0).sum() / cap) if cap else 0.0,
        })
    return pd.DataFrame(rows)


def revenue_by_service(items: pd.DataFrame) -> pd.DataFrame:
    df = items[items["status"].isin(CLOSED_STATUSES)]
    if df.empty:
        return pd.DataFrame(columns=["service_name", "ingreso", "veces"])
    return (df.groupby("service_name").agg(ingreso=("line_subtotal", "sum"), veces=("id", "size"))
            .sort_values("ingreso", ascending=False).reset_index())


def technician_ranking(orders: pd.DataFrame, items: pd.DataFrame) -> pd.DataFrame:
    """Por técnico: órdenes cerradas, ingresos y eficiencia."""
    closed = orders[orders["status"].isin(CLOSED_STATUSES)]
    rev = closed.groupby("technician").agg(ordenes=("id", "size"), ingresos=("total", "sum"))
    eff = kpis.efficiency_by_technician(items).set_index("technician")["eficiencia"] if len(items) else pd.Series(dtype=float)
    out = rev.join(eff, how="outer").fillna({"ordenes": 0, "ingresos": 0.0}).reset_index()
    return out.sort_values("ingresos", ascending=False).reset_index(drop=True)


def _delta(curr: float | None, prev: float | None) -> float | None:
    if curr is None or prev in (None, 0):
        return None
    return curr / prev - 1


def month_detail(orders: pd.DataFrame, items: pd.DataFrame, month: str, n_bays: int) -> dict:
    """Detalle de un mes (AAAA-MM): órdenes, ingresos por servicio, comparativo y técnicos destacados."""
    period = pd.Period(month, freq="M")
    om = orders[_month(orders["created_at"]) == period]
    im = items[_month(items["created_at"]) == period]
    monthly = monthly_kpis(orders, items, n_bays).set_index("mes")
    prev_key = (period - 1).strftime("%Y-%m")
    curr = monthly.loc[month].to_dict() if month in monthly.index else {}
    prev = monthly.loc[prev_key].to_dict() if prev_key in monthly.index else {}
    comparison = []
    for key in ["ingresos", "ordenes", "ticket", "eficiencia", "lead_time"]:
        c, p = curr.get(key), prev.get(key)
        comparison.append({"kpi": key, "nombre": KPI_DEFINITIONS.get(key, {}).get("nombre", "Órdenes cerradas"),
                           "actual": c, "anterior": p, "variacion": _delta(c, p)})
    return {"mes": month, "mes_anterior": prev_key if prev else None, "ordenes": om,
            "ingresos_por_servicio": revenue_by_service(im), "comparativo": comparison,
            "tecnicos": technician_ranking(om, im)}


def technician_detail(orders: pd.DataFrame, items: pd.DataFrame, technician: str,
                      start: date, end: date) -> dict:
    o = orders[orders["technician"] == technician]
    i = items[items["technician"] == technician]
    done = i[i["actual_hours"].notna()]
    hours = float(o["actual_hours"].fillna(0).sum())
    cap = available_hours(start, end, resources=1)
    trend = []
    if len(done):
        g = done.assign(mes=_month(done["created_at"])).groupby("mes")[["std_hours", "actual_hours"]].sum()
        trend = [{"mes": m.strftime("%Y-%m"), "eficiencia": float(r.std_hours / r.actual_hours)}
                 for m, r in g.iterrows()]
    top = (i.groupby("service_name").size().sort_values(ascending=False).head(6)
           .rename("veces").reset_index()) if len(i) else pd.DataFrame(columns=["service_name", "veces"])
    return {
        "technician": technician,
        "eficiencia": float(done["std_hours"].sum() / done["actual_hours"].sum()) if len(done) else None,
        "utilizacion": hours / cap if cap else 0.0,
        "horas_reales": hours, "horas_disponibles": cap,
        "ordenes_cerradas": int(o["status"].isin(CLOSED_STATUSES).sum()),
        "ordenes_pendientes": int((~o["status"].isin(CLOSED_STATUSES)).sum()),
        "tendencia": trend, "servicios_frecuentes": top,
    }


def kpi_detail(key: str, orders: pd.DataFrame, items: pd.DataFrame, bays: list[str],
               start: date, end: date) -> dict:
    """Valor del KPI, cómo se calculó (numerador/denominador) y su tendencia mensual."""
    if key not in KPI_DEFINITIONS:
        raise ValueError(f"KPI desconocido: {key}")
    closed = kpis.closed(orders)
    done = items[items["actual_hours"].notna()]
    if key == "ingresos":
        calc = {"valor": float(closed["total"].sum()), "partes": {"Órdenes cerradas": len(closed)}}
    elif key == "ticket":
        calc = {"valor": kpis.average_ticket(orders),
                "partes": {"Ingresos": float(closed["total"].sum()), "Órdenes cerradas": len(closed)}}
    elif key == "lead_time":
        calc = {"valor": kpis.average_lead_time_days(orders),
                "partes": {"Órdenes entregadas": int(orders["delivered_at"].notna().sum())}}
    elif key == "eficiencia":
        std, act = float(done["std_hours"].sum()), float(done["actual_hours"].sum())
        calc = {"valor": std / act if act else None,
                "partes": {"Horas estándar": round(std, 1), "Horas reales": round(act, 1)}}
    elif key == "utilizacion":
        used = float(orders["actual_hours"].fillna(0).sum())
        cap = available_hours(start, end, resources=len(bays))
        calc = {"valor": used / cap if cap else 0.0,
                "partes": {"Horas usadas": round(used, 1), "Horas disponibles": round(cap, 1),
                           "Bahías": len(bays)}}
    else:
        bl = kpis.backlog(orders)
        calc = {"valor": bl["ordenes"], "partes": {"Horas estándar pendientes": round(bl["horas_estandar"], 1),
                                                    **{k.capitalize(): v for k, v in bl["por_estado"].items()}}}
    trend_df = monthly_kpis(orders, items, len(bays))
    trend_col = {"ingresos": "ingresos", "ticket": "ticket", "lead_time": "lead_time", "eficiencia": "eficiencia",
                 "utilizacion": "utilizacion", "backlog": "recibidas"}[key]
    trend = [{"mes": r["mes"], "valor": r[trend_col]} for r in trend_df.to_dict("records")]
    return {"key": key, **KPI_DEFINITIONS[key], **calc, "tendencia": trend,
            "nota_tendencia": "Órdenes recibidas por mes" if key == "backlog" else None}


def service_detail(orders: pd.DataFrame, items: pd.DataFrame, service_id: int) -> dict:
    """Nivel 2 del Pareto: histórico mensual, técnicos, real vs. estándar."""
    i = items[items["service_id"] == service_id]
    closed = i[i["status"].isin(CLOSED_STATUSES)]
    monthly = []
    if len(closed):
        g = closed.assign(mes=_month(closed["created_at"])).groupby("mes").agg(
            veces=("id", "size"), ingreso=("line_subtotal", "sum"))
        monthly = [{"mes": m.strftime("%Y-%m"), "veces": int(r.veces), "ingreso": float(r.ingreso)}
                   for m, r in g.iterrows()]
    done = i[i["actual_hours"].notna()].copy()
    done["real_unit"] = done["actual_hours"] / done["qty"]
    done["std_unit"] = done["std_hours"] / done["qty"]
    techs = pd.DataFrame(columns=["technician", "veces", "real_promedio_h", "estandar_h", "eficiencia"])
    if len(done):
        techs = done.groupby("technician").agg(
            veces=("id", "size"), real_promedio_h=("real_unit", "mean"), estandar_h=("std_unit", "mean"),
            std_total=("std_hours", "sum"), real_total=("actual_hours", "sum")).reset_index()
        techs["eficiencia"] = techs["std_total"] / techs["real_total"]
        techs = techs.drop(columns=["std_total", "real_total"]).sort_values("veces", ascending=False)
    return {
        "mensual": monthly, "tecnicos": techs,
        "veces": int(len(closed)), "ingreso": float(closed["line_subtotal"].sum()),
        "real_promedio_h": float(done["real_unit"].mean()) if len(done) else None,
        "estandar_h": float(done["std_unit"].iloc[-1]) if len(done) else None,
        "valores_control": done.sort_values("created_at")[["folio", "technician", "created_at", "real_unit"]],
    }
