"""Gráfica de control X̄ (valores individuales) con límites ±3σ."""
from statistics import mean, stdev

import pandas as pd


def control_limits(values: list[float], k: float = 3.0) -> dict:
    """LC = media; LSC = media + kσ; LIC = max(0, media − kσ). σ = desviación estándar muestral."""
    data = [float(v) for v in values]
    if len(data) < 2:
        raise ValueError("Se requieren al menos 2 datos para calcular límites.")
    center = mean(data)
    sigma = stdev(data)
    return {"lc": center, "sigma": sigma, "lsc": center + k * sigma, "lic": max(0.0, center - k * sigma)}


def run_rule(values: list[float], center: float, length: int = 7) -> list[bool]:
    """Marca puntos que forman una racha de `length` o más del mismo lado de la línea central."""
    flags = [False] * len(values)
    side_prev, run_start = 0, 0
    for i, v in enumerate(values):
        side = 1 if v > center else (-1 if v < center else 0)
        if side == 0 or side != side_prev:
            run_start = i
        side_prev = side
        if side != 0 and i - run_start + 1 >= length:
            for j in range(run_start, i + 1):
                flags[j] = True
    return flags


def control_chart(values: list[float], k: float = 3.0, run_length: int = 7) -> tuple[pd.DataFrame, dict]:
    """Tabla con cada punto, límites y señales de variación anormal."""
    limits = control_limits(values, k)
    df = pd.DataFrame({"n": range(1, len(values) + 1), "valor": [float(v) for v in values]})
    df["fuera_de_limites"] = (df["valor"] > limits["lsc"]) | (df["valor"] < limits["lic"])
    df["racha"] = run_rule(df["valor"].tolist(), limits["lc"], run_length)
    return df, limits
