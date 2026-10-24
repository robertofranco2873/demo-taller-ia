"""Reloj del taller: toda la app obtiene "ahora" y "hoy" de aquí, en la zona APP_TZ.

En la nube el servidor corre en UTC; sin esto, en México el "día" cambiaría a las 18:00.
Las fechas se guardan sin zona (hora local del taller), como en toda la base.
"""
import os
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

DEFAULT_TZ = "America/Mexico_City"


def tz_name() -> str:
    return (os.getenv("APP_TZ") or DEFAULT_TZ).strip()


def app_tz() -> ZoneInfo:
    try:
        return ZoneInfo(tz_name())
    except (ZoneInfoNotFoundError, ValueError):
        raise ValueError(f"APP_TZ inválida: «{tz_name()}». Usa un nombre IANA, p. ej. America/Mexico_City.")


def _utcnow() -> datetime:
    """Instante actual en UTC (las pruebas lo reemplazan para simular fechas)."""
    return datetime.now(timezone.utc)


def now(utc: datetime | None = None) -> datetime:
    """Fecha y hora local del taller, sin zona y sin microsegundos."""
    instant = utc or _utcnow()
    if instant.tzinfo is None:
        instant = instant.replace(tzinfo=timezone.utc)
    return instant.astimezone(app_tz()).replace(tzinfo=None, microsecond=0)


def today(utc: datetime | None = None) -> date:
    return now(utc).date()
