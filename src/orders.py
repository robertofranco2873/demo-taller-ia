"""Reglas de negocio de las órdenes de trabajo (sin base de datos)."""
from datetime import date

from src.config import STATUSES

# Columna de fecha que se registra al entrar a cada estado.
STATUS_TIMESTAMP = {
    "en proceso": "started_at",
    "terminada": "finished_at",
    "entregada": "delivered_at",
}


def next_status(current: str) -> str | None:
    """Siguiente estado del flujo recibida → en proceso → terminada → entregada."""
    if current not in STATUSES:
        raise ValueError(f"Estado desconocido: {current}")
    i = STATUSES.index(current)
    return STATUSES[i + 1] if i + 1 < len(STATUSES) else None


def validate_transition(current: str, new: str, actual_hours: list[float | None] | None = None) -> None:
    """Solo se permite avanzar un paso. Para terminar se exige el tiempo real de cada servicio."""
    expected = next_status(current)
    if new != expected:
        raise ValueError(f"No se puede pasar de '{current}' a '{new}'. Siguiente estado válido: {expected}.")
    if new == "terminada":
        if not actual_hours or any(h is None or h <= 0 for h in actual_hours):
            raise ValueError("Registra el tiempo real (> 0 h) de cada servicio antes de terminar la orden.")


def split_actual_hours(std_by_item: dict[int, float], total_hours: float) -> dict[int, float]:
    """Reparte el tiempo real total entre los servicios en proporción a su tiempo estándar."""
    if total_hours <= 0:
        raise ValueError("El tiempo real debe ser positivo.")
    std_total = sum(std_by_item.values())
    if std_total <= 0:
        share = total_hours / len(std_by_item)
        return {k: round(share, 4) for k in std_by_item}
    return {k: round(total_hours * v / std_total, 4) for k, v in std_by_item.items()}


def priority(due_date: date, today: date) -> str:
    """Etiqueta de prioridad para la vista del técnico."""
    if due_date < today:
        return "vencida"
    if due_date == today:
        return "hoy"
    return "próxima"


def time_variance(std_hours: float, actual_hours: float) -> dict:
    """Comparación tiempo real vs. estándar de una orden."""
    diff = actual_hours - std_hours
    return {
        "diferencia_h": diff,
        "variacion_pct": diff / std_hours if std_hours else 0.0,
        "eficiencia": std_hours / actual_hours if actual_hours else 0.0,
    }
