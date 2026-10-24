"""Estudio de tiempos: tiempo normal, tiempo estándar y número de observaciones."""
import math
from statistics import NormalDist, mean, stdev


def observed_average(observations: list[float]) -> float:
    """Promedio de los tiempos observados (minutos)."""
    values = [float(x) for x in observations]
    if not values:
        raise ValueError("Se requiere al menos una observación.")
    if any(v <= 0 for v in values):
        raise ValueError("Los tiempos observados deben ser positivos.")
    return mean(values)


def normal_time(observed_avg: float, rating_factor: float) -> float:
    """Tiempo normal = tiempo observado promedio × factor de calificación."""
    if observed_avg <= 0:
        raise ValueError("El tiempo observado debe ser positivo.")
    if rating_factor <= 0:
        raise ValueError("El factor de calificación debe ser positivo.")
    return observed_avg * rating_factor


def standard_time(normal: float, allowance_pct: float) -> float:
    """Tiempo estándar = tiempo normal × (1 + % suplementos). allowance_pct en fracción (0.15 = 15 %)."""
    if allowance_pct < 0:
        raise ValueError("Los suplementos no pueden ser negativos.")
    return normal * (1 + allowance_pct)


def standard_hours(observed_avg_min: float, rating_factor: float, allowance_pct: float) -> float:
    """Tiempo estándar en horas a partir de minutos observados."""
    return standard_time(normal_time(observed_avg_min, rating_factor), allowance_pct) / 60.0


def required_observations(observations: list[float], confidence: float = 0.95, error: float = 0.05) -> int:
    """Observaciones necesarias: n = (z·s / (e·x̄))², redondeado hacia arriba.

    z = valor normal para el nivel de confianza (bilateral); e = error relativo aceptado.
    """
    values = [float(x) for x in observations]
    if len(values) < 2:
        raise ValueError("Se requieren al menos 2 observaciones.")
    if not 0 < confidence < 1 or not 0 < error < 1:
        raise ValueError("Confianza y error deben estar entre 0 y 1.")
    z = NormalDist().inv_cdf(0.5 + confidence / 2)
    n = (z * stdev(values) / (error * observed_average(values))) ** 2
    return max(1, math.ceil(n - 1e-9))
