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


# Constantes para gráficas X̄-R por tamaño de subgrupo n.
XBAR_R_CONSTANTS = {
    2: (1.880, 0.0, 3.267), 3: (1.023, 0.0, 2.574), 4: (0.729, 0.0, 2.282),
    5: (0.577, 0.0, 2.114), 6: (0.483, 0.0, 2.004), 7: (0.419, 0.076, 1.924),
    8: (0.373, 0.136, 1.864), 9: (0.337, 0.184, 1.816), 10: (0.308, 0.223, 1.777),
}


def xbar_r_chart(values: list[float], subgroup_size: int = 5) -> tuple[pd.DataFrame, dict]:
    """Gráfica X̄-R con subgrupos consecutivos (se descarta el último subgrupo incompleto).

    X̄: LC = X̿, LSC/LIC = X̿ ± A2·R̄.   R: LC = R̄, LSC = D4·R̄, LIC = D3·R̄.
    """
    if subgroup_size not in XBAR_R_CONSTANTS:
        raise ValueError("El tamaño de subgrupo debe estar entre 2 y 10.")
    data = [float(v) for v in values]
    k = len(data) // subgroup_size
    if k < 2:
        raise ValueError("Se requieren al menos 2 subgrupos completos.")
    groups = [data[i * subgroup_size:(i + 1) * subgroup_size] for i in range(k)]
    a2, d3, d4 = XBAR_R_CONSTANTS[subgroup_size]
    xbars = [mean(g) for g in groups]
    ranges = [max(g) - min(g) for g in groups]
    xbarbar, rbar = mean(xbars), mean(ranges)
    limits = {
        "xbar": {"lc": xbarbar, "lsc": xbarbar + a2 * rbar, "lic": max(0.0, xbarbar - a2 * rbar)},
        "r": {"lc": rbar, "lsc": d4 * rbar, "lic": d3 * rbar},
        "n": subgroup_size, "a2": a2, "d3": d3, "d4": d4,
    }
    df = pd.DataFrame({"subgrupo": range(1, k + 1), "xbar": xbars, "rango": ranges})
    df["xbar_fuera"] = (df["xbar"] > limits["xbar"]["lsc"]) | (df["xbar"] < limits["xbar"]["lic"])
    df["rango_fuera"] = (df["rango"] > limits["r"]["lsc"]) | (df["rango"] < limits["r"]["lic"] - 1e-12)
    return df, limits
