from datetime import date

import pandas as pd
import pytest

from src import kpis


@pytest.fixture
def orders():
    return pd.DataFrame({
        "created_at": pd.to_datetime(["2026-09-01 09:00", "2026-09-15 10:00", "2026-10-02 09:00", "2026-10-05 09:00"]),
        "delivered_at": pd.to_datetime(["2026-09-02 09:00", "2026-09-16 22:00", None, None]),
        "status": ["entregada", "entregada", "terminada", "recibida"],
        "total": [1000.0, 3000.0, 2000.0, 500.0],
        "bay": ["B1", "B1", "B2", "B2"],
        "std_hours": [2.0, 4.0, 3.0, 1.5],
        "actual_hours": [2.5, 4.0, 2.0, None],
        "technician": ["A", "B", "A", "B"],
    })


def test_revenue_by_month(orders):
    rev = kpis.revenue_by_month(orders)
    assert rev["ingresos"].tolist() == [4000.0, 2000.0]
    assert rev["ordenes"].tolist() == [2, 1]


def test_average_ticket_ignores_open_orders(orders):
    assert kpis.average_ticket(orders) == pytest.approx(2000.0)


def test_efficiency():
    assert kpis.efficiency(3, 4) == pytest.approx(0.75)
    with pytest.raises(ValueError):
        kpis.efficiency(3, 0)


def test_efficiency_by_technician(orders):
    eff = kpis.efficiency_by_technician(orders).set_index("technician")
    assert eff.loc["A", "eficiencia"] == pytest.approx(5 / 4.5)
    assert eff.loc["B", "eficiencia"] == pytest.approx(1.0)


def test_bay_utilization(orders):
    # Semana lun 7 - dom 13 sep 2026 → 6 días × 8 h = 48 h por bahía
    util = kpis.bay_utilization(orders, ["B1", "B2", "B3"], date(2026, 9, 7), date(2026, 9, 13)).set_index("bay")
    assert util.loc["B1", "utilizacion"] == pytest.approx(6.5 / 48)
    assert util.loc["B3", "utilizacion"] == 0


def test_lead_time(orders):
    # 1 día y 1.5 días → 1.25 días
    assert kpis.average_lead_time_days(orders) == pytest.approx(1.25)


def test_backlog(orders):
    bl = kpis.backlog(orders)
    assert bl["ordenes"] == 1
    assert bl["horas_estandar"] == pytest.approx(1.5)


def test_filter_by_date(orders):
    assert len(kpis.filter_by_date(orders, date(2026, 10, 1), date(2026, 10, 31))) == 2


def test_summary_has_kpis(orders):
    s = kpis.summary(orders, orders, ["B1", "B2"], date(2026, 9, 1), date(2026, 10, 31))
    assert s["ticket_promedio"] == pytest.approx(2000.0)
    assert s["backlog_ordenes"] == 1
    assert set(s["eficiencia_por_tecnico"]) == {"A", "B"}
