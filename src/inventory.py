"""Inventario de refacciones: demanda, stock de seguridad, punto de reorden y lote económico.

Demanda diaria d̄ y su desviación σd se calculan con TODOS los días laborables del periodo
(los días sin consumo cuentan como 0).

Stock de seguridad SS = z · σd · √L
Punto de reorden  ROP = d̄ · L + SS
Lote económico    EOQ = √(2 · D · S / H)   (D anual, S costo por pedido, H costo anual de mantener)
"""
import math
from datetime import date, timedelta
from statistics import NormalDist, mean, pstdev

import pandas as pd

from src.workcalendar import is_workday

WORKDAYS_PER_YEAR = 6 * 52


def daily_demand(consumption: pd.DataFrame, start: date, end: date) -> tuple[float, float]:
    """Media y desviación estándar diaria. consumption: columnas date (date) y qty (> 0)."""
    days = [start + timedelta(days=i) for i in range((end - start).days + 1)]
    days = [d for d in days if is_workday(d)]
    if not days:
        raise ValueError("El periodo no tiene días laborables.")
    by_day = consumption.groupby("date")["qty"].sum().to_dict() if len(consumption) else {}
    series = [float(by_day.get(d, 0.0)) for d in days]
    return mean(series), pstdev(series)


def safety_stock(std_daily: float, lead_time_days: float, service_level: float = 0.95) -> float:
    if not 0 < service_level < 1:
        raise ValueError("El nivel de servicio debe estar entre 0 y 1.")
    if lead_time_days < 0:
        raise ValueError("El tiempo de entrega no puede ser negativo.")
    return NormalDist().inv_cdf(service_level) * std_daily * math.sqrt(lead_time_days)


def reorder_point(mean_daily: float, std_daily: float, lead_time_days: float,
                  service_level: float = 0.95) -> float:
    return mean_daily * lead_time_days + safety_stock(std_daily, lead_time_days, service_level)


def eoq(annual_demand: float, order_cost: float, holding_cost: float) -> float:
    if holding_cost <= 0:
        raise ValueError("El costo de mantener debe ser positivo.")
    if annual_demand <= 0:
        return 0.0
    return math.sqrt(2 * annual_demand * order_cost / holding_cost)


def stock_status(stock: float, rop: float) -> str:
    if stock <= 0:
        return "agotado"
    if stock <= rop:
        return "reordenar"
    return "ok"


def inventory_table(parts: pd.DataFrame, consumption: pd.DataFrame, start: date, end: date,
                    service_level: float = 0.95, order_cost: float = 150.0,
                    holding_rate: float = 0.25) -> pd.DataFrame:
    """parts: id, code, name, price, stock, lead_time_days. consumption: part_id, date, qty."""
    rows = []
    for p in parts.itertuples():
        cons = consumption[consumption["part_id"] == p.id] if len(consumption) else consumption
        d_mean, d_std = daily_demand(cons, start, end)
        ss = safety_stock(d_std, p.lead_time_days, service_level)
        rop = d_mean * p.lead_time_days + ss
        lot = eoq(d_mean * WORKDAYS_PER_YEAR, order_cost, max(p.price * holding_rate, 0.01))
        rows.append({"id": p.id, "code": p.code, "name": p.name, "price": p.price,
                     "stock": p.stock, "lead_time_days": p.lead_time_days,
                     "demanda_diaria": d_mean, "desv_diaria": d_std, "stock_seguridad": ss,
                     "punto_reorden": rop, "eoq": lot,
                     "cobertura_dias": p.stock / d_mean if d_mean > 0 else None,
                     "estado": stock_status(p.stock, rop)})
    return pd.DataFrame(rows)
