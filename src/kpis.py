"""Indicadores del dashboard. Funciones puras sobre DataFrames.

orders: una fila por orden con columnas created_at, delivered_at, status, total,
        technician, bay, std_hours, actual_hours.
items:  una fila por servicio de una orden con technician, std_hours, actual_hours.
"""
from datetime import date

import pandas as pd

from src.config import CLOSED_STATUSES, PENDING_STATUSES
from src.workcalendar import available_hours


def filter_by_date(df: pd.DataFrame, start: date, end: date, col: str = "created_at") -> pd.DataFrame:
    """Filas cuya fecha `col` está entre start y end (inclusive)."""
    dates = pd.to_datetime(df[col]).dt.date
    return df[(dates >= start) & (dates <= end)]


def closed(orders: pd.DataFrame) -> pd.DataFrame:
    return orders[orders["status"].isin(CLOSED_STATUSES)]


def revenue_by_month(orders: pd.DataFrame) -> pd.DataFrame:
    """Ingresos (total con IVA) de órdenes terminadas/entregadas, agrupados por mes de recepción."""
    df = closed(orders)
    if df.empty:
        return pd.DataFrame(columns=["mes", "ingresos", "ordenes"])
    month = pd.to_datetime(df["created_at"]).dt.to_period("M").dt.to_timestamp()
    out = (df.assign(mes=month).groupby("mes")
           .agg(ingresos=("total", "sum"), ordenes=("total", "size")).reset_index())
    return out


def average_ticket(orders: pd.DataFrame) -> float:
    """Ticket promedio = ingresos / número de órdenes cerradas."""
    df = closed(orders)
    return float(df["total"].mean()) if not df.empty else 0.0


# Regla de eficiencia (se documenta en el globo del KPI):
# 1) Se excluyen registros con tiempo real < 25 % del estándar (casi siempre, cronómetro olvidado).
# 2) La eficiencia mostrada se limita a 0-200 %.
MIN_VALID_RATIO = 0.25
EFFICIENCY_CAP = 2.0
EFFICIENCY_RULE = ("Se excluyen los registros con tiempo real menor al 25 % del estándar (suelen ser un cronómetro "
                   "olvidado) y el resultado se limita a 0-200 %.")


def cap_efficiency(value: float | None) -> float | None:
    """Limita la eficiencia al rango 0-200 %."""
    if value is None or value != value:
        return None
    return min(max(float(value), 0.0), EFFICIENCY_CAP)


def is_valid_time(std_hours: float, actual_hours: float | None) -> bool:
    if actual_hours is None or actual_hours != actual_hours or actual_hours <= 0:
        return False
    return actual_hours >= MIN_VALID_RATIO * std_hours


def valid_times(items: pd.DataFrame) -> pd.DataFrame:
    """Registros con tiempo real utilizable para eficiencia (excluye < 25 % del estándar)."""
    df = items.dropna(subset=["actual_hours"])
    return df[(df["actual_hours"] > 0) & (df["actual_hours"] >= MIN_VALID_RATIO * df["std_hours"])]


def ratio_efficiency(df: pd.DataFrame) -> float | None:
    """Σ estándar ÷ Σ real sobre registros válidos, con tope."""
    v = valid_times(df)
    act = float(v["actual_hours"].sum())
    return cap_efficiency(float(v["std_hours"].sum()) / act) if act > 0 else None


def efficiency(std_hours: float, actual_hours: float) -> float:
    """Eficiencia = tiempo estándar / tiempo real."""
    if actual_hours <= 0:
        raise ValueError("El tiempo real debe ser positivo.")
    return cap_efficiency(std_hours / actual_hours)


def efficiency_by_technician(items: pd.DataFrame) -> pd.DataFrame:
    """Eficiencia por técnico con los servicios que ya tienen tiempo real registrado."""
    df = valid_times(items)
    if df.empty:
        return pd.DataFrame(columns=["technician", "std_hours", "actual_hours", "eficiencia"])
    out = df.groupby("technician")[["std_hours", "actual_hours"]].sum().reset_index()
    out["eficiencia"] = (out["std_hours"] / out["actual_hours"]).clip(0, EFFICIENCY_CAP)
    return out.sort_values("eficiencia", ascending=False).reset_index(drop=True)


def bay_utilization(orders: pd.DataFrame, bays: list[str], start: date, end: date) -> pd.DataFrame:
    """Utilización = horas usadas (tiempo real) / horas disponibles, por bahía."""
    capacity = available_hours(start, end, resources=1)
    used = orders.dropna(subset=["actual_hours"]).groupby("bay")["actual_hours"].sum()
    rows = []
    for bay in bays:
        h = float(used.get(bay, 0.0))
        rows.append({"bay": bay, "horas_usadas": h, "horas_disponibles": capacity,
                     "utilizacion": h / capacity if capacity else 0.0})
    return pd.DataFrame(rows)


def average_lead_time_days(orders: pd.DataFrame) -> float:
    """Lead time promedio (días) = entrega − recepción, en órdenes entregadas."""
    df = orders.dropna(subset=["delivered_at"])
    if df.empty:
        return 0.0
    delta = pd.to_datetime(df["delivered_at"]) - pd.to_datetime(df["created_at"])
    return float(delta.dt.total_seconds().mean() / 86400)


def backlog(orders: pd.DataFrame) -> dict:
    """Órdenes pendientes (recibidas o en proceso) y sus horas estándar."""
    df = orders[orders["status"].isin(PENDING_STATUSES)]
    return {"ordenes": int(len(df)), "horas_estandar": float(df["std_hours"].sum()),
            "por_estado": df["status"].value_counts().to_dict()}


def summary(orders: pd.DataFrame, items: pd.DataFrame, bays: list[str], start: date, end: date) -> dict:
    """KPIs ya calculados (lo que la IA puede leer para redactar el resumen)."""
    eff = efficiency_by_technician(items)
    util = bay_utilization(orders, bays, start, end)
    rev = revenue_by_month(orders)
    bl = backlog(orders)
    return {
        "periodo": f"{start.isoformat()} a {end.isoformat()}",
        "ordenes_recibidas": int(len(orders)),
        "ordenes_cerradas": int(len(closed(orders))),
        "tasa_cierre": round(len(closed(orders)) / len(orders), 3) if len(orders) else 0.0,
        "ingresos_totales": round(float(closed(orders)["total"].sum()), 2),
        "ingresos_por_mes": {r.mes.strftime("%Y-%m"): round(float(r.ingresos), 2) for r in rev.itertuples()},
        "ticket_promedio": round(average_ticket(orders), 2),
        "lead_time_promedio_dias": round(average_lead_time_days(orders), 2),
        "eficiencia_por_tecnico": {r.technician: round(float(r.eficiencia), 3) for r in eff.itertuples()},
        "utilizacion_bahias": {r.bay: round(float(r.utilizacion), 3) for r in util.itertuples()},
        "backlog_ordenes": bl["ordenes"],
        "backlog_horas_estandar": round(bl["horas_estandar"], 2),
    }
