"""Carga vs. capacidad semanal por técnico."""
from datetime import date, timedelta

import pandas as pd

from src.config import HOURS_PER_DAY
from src.workcalendar import available_hours


def weekly_load(orders: pd.DataFrame, technicians: list[str], week_monday: date,
                hours_per_day: float = HOURS_PER_DAY) -> pd.DataFrame:
    """Horas estándar programadas en la semana vs. horas disponibles por técnico.

    orders: columnas technician, scheduled_date, std_hours.
    """
    week_end = week_monday + timedelta(days=6)
    capacity = available_hours(week_monday, week_end, resources=1, hours_per_day=hours_per_day)
    sched = pd.to_datetime(orders["scheduled_date"]).dt.date
    in_week = orders[(sched >= week_monday) & (sched <= week_end)]
    load = in_week.groupby("technician")["std_hours"].sum()
    count = in_week.groupby("technician").size()
    rows = []
    for tech in technicians:
        h = float(load.get(tech, 0.0))
        rows.append({
            "technician": tech,
            "ordenes": int(count.get(tech, 0)),
            "carga_horas": round(h, 2),
            "capacidad_horas": capacity,
            "utilizacion": h / capacity if capacity else 0.0,
            "holgura_horas": round(capacity - h, 2),
            "sobrecarga": h > capacity,
        })
    return pd.DataFrame(rows)
