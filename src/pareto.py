"""Análisis de Pareto (80/20)."""
import pandas as pd


def pareto_table(df: pd.DataFrame, category_col: str, value_col: str | None = None,
                 threshold: float = 0.8) -> pd.DataFrame:
    """Tabla de Pareto ordenada de mayor a menor.

    Si value_col es None se usa la frecuencia (conteo de filas).
    Clase A = categorías necesarias para llegar al umbral acumulado (incluye la que lo cruza).
    """
    if df.empty:
        return pd.DataFrame(columns=[category_col, "valor", "pct", "pct_acumulado", "clase"])
    if value_col is None:
        grouped = df.groupby(category_col).size()
    else:
        grouped = df.groupby(category_col)[value_col].sum()
    out = grouped.sort_values(ascending=False).rename("valor").reset_index()
    total = out["valor"].sum()
    out["pct"] = out["valor"] / total if total else 0.0
    out["pct_acumulado"] = out["pct"].cumsum()
    previous = out["pct_acumulado"].shift(fill_value=0.0)
    out["clase"] = ["A" if p < threshold - 1e-12 else "B" for p in previous]
    return out


def vital_few(table: pd.DataFrame) -> int:
    """Número de categorías de la clase A."""
    return int((table["clase"] == "A").sum())
