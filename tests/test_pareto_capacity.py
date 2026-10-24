from datetime import date

import pandas as pd
import pytest

from src.capacity import weekly_load
from src.pareto import pareto_table, vital_few


def test_pareto_by_value():
    df = pd.DataFrame({"svc": ["A", "B", "C", "D", "A"], "v": [50, 25, 15, 5, 5]})
    t = pareto_table(df, "svc", "v")
    assert t["svc"].tolist() == ["A", "B", "C", "D"]
    assert t["pct_acumulado"].iloc[-1] == pytest.approx(1.0)
    # A=55 %, B=80 % → A y B son clase A (la que alcanza el 80 % se incluye)
    assert t["clase"].tolist() == ["A", "A", "B", "B"]
    assert vital_few(t) == 2


def test_pareto_by_frequency():
    df = pd.DataFrame({"svc": ["A", "A", "A", "B"]})
    t = pareto_table(df, "svc")
    assert t["valor"].tolist() == [3, 1]


def test_pareto_empty():
    assert pareto_table(pd.DataFrame({"svc": [], "v": []}), "svc", "v").empty


def test_weekly_load_flags_overload():
    monday = date(2026, 10, 19)
    orders = pd.DataFrame({
        "technician": ["A", "A", "B", "A"],
        "scheduled_date": [date(2026, 10, 19), date(2026, 10, 24), date(2026, 10, 20), date(2026, 10, 26)],
        "std_hours": [30.0, 25.0, 10.0, 99.0],  # la última es de otra semana
    })
    t = weekly_load(orders, ["A", "B", "C"], monday).set_index("technician")
    assert t.loc["A", "capacidad_horas"] == 48
    assert t.loc["A", "carga_horas"] == 55
    assert bool(t.loc["A", "sobrecarga"]) is True
    assert bool(t.loc["B", "sobrecarga"]) is False
    assert t.loc["C", "carga_horas"] == 0
