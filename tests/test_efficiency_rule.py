"""Regla de eficiencia: excluir tiempos < 25 % del estándar y limitar a 0-200 %."""
from datetime import datetime, timedelta

import pandas as pd
import pytest

from src import analytics, db, kpis
from src.orders import time_variance
from src.seed import seed_database


def items(rows):
    return pd.DataFrame(rows, columns=["technician", "std_hours", "actual_hours", "created_at", "service_id", "qty",
                                       "status", "folio", "id", "line_subtotal", "service_name"])


def row(tech, std, actual, i=0):
    return [tech, std, actual, pd.Timestamp("2026-10-20"), 1, 1, "entregada", f"OT-{i}", i, 100.0, "Servicio"]


def test_cap_and_validity():
    assert kpis.cap_efficiency(3.5) == 2.0
    assert kpis.cap_efficiency(-1) == 0.0
    assert kpis.cap_efficiency(None) is None
    assert kpis.efficiency(1, 0.01) == 2.0  # 10000 % → 200 %
    assert kpis.is_valid_time(2.0, 0.5) is True    # exactamente 25 %: cuenta
    assert kpis.is_valid_time(2.0, 0.49) is False  # menos del 25 %: se excluye
    assert kpis.is_valid_time(2.0, None) is False


def test_outlier_is_excluded_from_technician_efficiency():
    df = items([row("A", 2.0, 2.0, 1), row("A", 2.0, 0.02, 2), row("B", 1.0, 1.25, 3)])
    eff = kpis.efficiency_by_technician(df).set_index("technician")
    assert eff.loc["A", "eficiencia"] == pytest.approx(1.0)  # sin el registro de 0.02 h
    assert eff.loc["B", "eficiencia"] == pytest.approx(0.8)
    assert kpis.ratio_efficiency(df) == pytest.approx(3.0 / 3.25)


def test_very_fast_but_valid_is_capped():
    df = items([row("A", 4.0, 1.5, 1)])  # 267 %, válido (> 25 %) pero se limita
    assert kpis.efficiency_by_technician(df).iloc[0]["eficiencia"] == pytest.approx(2.0)
    assert kpis.ratio_efficiency(df) == pytest.approx(2.0)


def test_kpi_detail_reports_excluded_records():
    df = items([row("A", 2.0, 2.0, 1), row("A", 2.0, 0.02, 2)])
    orders = pd.DataFrame({"status": ["entregada"], "total": [100.0], "created_at": [pd.Timestamp("2026-10-20")],
                           "delivered_at": [pd.Timestamp("2026-10-21")], "actual_hours": [2.02], "std_hours": [4.0]})
    d = analytics.kpi_detail("eficiencia", orders, df, ["B1"], datetime(2026, 10, 1).date(), datetime(2026, 10, 31).date())
    assert d["valor"] == pytest.approx(1.0)
    assert d["partes"]["Registros excluidos (< 25 % del estándar)"] == 1
    assert "25 %" in d["explicacion"] and "200 %" in d["explicacion"]


def test_time_variance_is_capped():
    assert time_variance(4.0, 0.1)["eficiencia"] == 2.0


def test_finish_with_tiny_timer_does_not_count(tmp_path):
    p = tmp_path / "eff.db"
    now = datetime(2026, 10, 23, 13, 0)
    seed_database(p, now=now)
    orders = db.load_orders(p)
    oid = int(orders[orders["status"] == "recibida"].iloc[0]["id"])
    db.start_timer(oid, now, p)
    r = db.finish_with_timer(oid, now + timedelta(seconds=20), p)
    assert r["efficiency"] <= 2.0
    assert r["counts_for_kpis"] is False
    # y no distorsiona la eficiencia del técnico
    eff = kpis.efficiency_by_technician(db.load_items(p))
    assert (eff["eficiencia"] <= 2.0).all()
