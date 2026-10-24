"""Calendario laboral del taller (lunes a sábado, 8 h por día)."""
from datetime import date, datetime, timedelta

from src.config import HOURS_PER_DAY, WORKDAY_START_HOUR, WORKDAYS


def is_workday(d: date) -> bool:
    return d.weekday() in WORKDAYS


def workdays_between(start: date, end: date) -> int:
    """Número de días laborables entre start y end, ambos inclusive."""
    if end < start:
        return 0
    days = (end - start).days + 1
    return sum(1 for i in range(days) if is_workday(start + timedelta(days=i)))


def available_hours(start: date, end: date, resources: int = 1,
                    hours_per_day: float = HOURS_PER_DAY) -> float:
    """Horas disponibles = días laborables × horas por día × número de recursos."""
    return workdays_between(start, end) * hours_per_day * resources


def week_start(d: date) -> date:
    """Lunes de la semana de d."""
    return d - timedelta(days=d.weekday())


def add_workdays(d: date, n: int) -> date:
    """Fecha que resulta de avanzar n días laborables desde d."""
    current = d
    while n > 0:
        current += timedelta(days=1)
        if is_workday(current):
            n -= 1
    return current


def add_work_hours(dt: datetime, hours: float, hours_per_day: float = HOURS_PER_DAY) -> datetime:
    """Suma horas de trabajo a dt respetando la jornada laboral."""
    remaining = float(hours)
    current = dt
    while True:
        day_start = current.replace(hour=WORKDAY_START_HOUR, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(hours=hours_per_day)
        if not is_workday(current.date()) or current >= day_end:
            current = day_start + timedelta(days=1)
            continue
        if current < day_start:
            current = day_start
        if remaining <= 1e-9:
            return current
        available = (day_end - current).total_seconds() / 3600
        step = min(remaining, available)
        current += timedelta(hours=step)
        remaining -= step
        if remaining <= 1e-9:
            return current


def work_day_segments(now: datetime, horizon_h: float, hours_per_day: float = HOURS_PER_DAY) -> list[dict]:
    """Divide el horizonte (horas laborables desde `now`) en días.

    Cada segmento: fecha, inicio y fin en horas laborables desde `now` y la hora de reloj
    con la que arranca (el primer día puede empezar a media jornada).
    """
    start = add_work_hours(now, 0)
    day_start = start.replace(hour=WORKDAY_START_HOUR, minute=0, second=0, microsecond=0)
    first_len = hours_per_day - (start - day_start).total_seconds() / 3600
    segments, offset, current = [], 0.0, start
    length = first_len
    clock = WORKDAY_START_HOUR + (hours_per_day - first_len)
    while offset < horizon_h - 1e-9 or not segments:
        segments.append({"date": current.date(), "start_h": offset, "end_h": offset + length, "start_clock": clock})
        offset += length
        current = add_work_hours(current.replace(hour=WORKDAY_START_HOUR, minute=0, second=0, microsecond=0),
                                 hours_per_day)
        current = add_work_hours(current, 0)  # siguiente día laborable a las 9:00
        length, clock = hours_per_day, float(WORKDAY_START_HOUR)
    return segments


def work_hours_until(now: datetime, due: date, hours_per_day: float = HOURS_PER_DAY) -> float:
    """Horas laborables desde `now` hasta el cierre del día `due` (negativo si ya venció)."""
    day_start = now.replace(hour=WORKDAY_START_HOUR, minute=0, second=0, microsecond=0)
    elapsed_today = 0.0
    if is_workday(now.date()):
        elapsed_today = min(max((now - day_start).total_seconds() / 3600, 0.0), hours_per_day)
    today = now.date()
    if due >= today:
        return workdays_between(today, due) * hours_per_day - elapsed_today
    return -(workdays_between(due + timedelta(days=1), today) * hours_per_day - (hours_per_day - elapsed_today))
