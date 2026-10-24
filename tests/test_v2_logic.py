from datetime import date, datetime, timedelta
from io import BytesIO

import pandas as pd
import pytest

from src import db
from src.export import quote_to_pdf
from src.inventory import daily_demand, eoq, inventory_table, reorder_point, safety_stock, stock_status
from src.orders import priority, split_actual_hours
from src.quote import Quote, QuoteLine
from src.security import hash_password, verify_password
from src.seed import seed_database
from src.sequencing import Job, compare_rules_resources, schedule_resources
from src.spc import xbar_r_chart
from src.time_study import required_observations

NOW = datetime(2026, 10, 23, 13, 0)


# ---------- estudio de tiempos ----------

def test_required_observations():
    # x̄ = 10, s = 1 → n = (1.96·1 / (0.05·10))² = 15.37 → 16
    obs = [9, 10, 11, 9, 10, 11, 9, 10, 11, 10]
    s = pd.Series(obs).std()
    expected = (1.959964 * s / (0.05 * 10)) ** 2
    assert required_observations(obs) == int(expected) + 1


def test_required_observations_more_error_needs_less():
    obs = [10, 12, 9, 14, 11]
    assert required_observations(obs, error=0.10) < required_observations(obs, error=0.05)


def test_required_observations_invalid():
    with pytest.raises(ValueError):
        required_observations([10])
    with pytest.raises(ValueError):
        required_observations([10, 11], confidence=1.2)


# ---------- X̄-R ----------

def test_xbar_r_limits():
    values = [1, 2, 3, 4, 5, 2, 3, 4, 5, 6]  # 2 subgrupos de 5: x̄ 3 y 4, R 4 y 4
    df, lim = xbar_r_chart(values, 5)
    assert df["xbar"].tolist() == [3, 4]
    assert lim["xbar"]["lc"] == pytest.approx(3.5)
    assert lim["xbar"]["lsc"] == pytest.approx(3.5 + 0.577 * 4)
    assert lim["r"]["lsc"] == pytest.approx(2.114 * 4)
    assert lim["r"]["lic"] == 0


def test_xbar_r_drops_incomplete_and_validates():
    df, _ = xbar_r_chart(list(range(1, 13)), 5)
    assert len(df) == 2
    with pytest.raises(ValueError):
        xbar_r_chart([1, 2, 3], 5)
    with pytest.raises(ValueError):
        xbar_r_chart(list(range(30)), 11)


# ---------- secuenciación con recursos ----------

JOBS = [Job("A", 4, 4, 1, "T1"), Job("B", 2, 10, 2, "T1"), Job("C", 3, 5, 3, "T2")]


def test_schedule_respects_assignment():
    df = schedule_resources(JOBS, "FIFO", ["T1", "T2"], ["B1", "B2"])
    assert df.set_index("orden").loc["B", "recurso"] == "T1"
    assert df.set_index("orden").loc["B", "inicio_h"] == 4  # espera a que T1 termine A


def test_schedule_bay_is_bottleneck():
    df = schedule_resources(JOBS, "FIFO", ["T1", "T2"], ["B1"]).set_index("orden")
    # Una sola bahía (FIFO A, B, C): B usa la bahía de 4 a 6; C, aunque T2 está libre, espera a las 6.
    assert df.loc["B", "inicio_h"] == 4
    assert df.loc["C", "inicio_h"] == 6


def test_schedule_free_assignment_uses_idle_technician():
    df = schedule_resources(JOBS, "FIFO", ["T1", "T2"], ["B1", "B2", "B3"], respect_assignment=False).set_index("orden")
    assert df.loc["B", "recurso"] == "T2"
    assert compare_rules_resources(JOBS, ["T1", "T2"], ["B1", "B2"]).shape[0] == 3


# ---------- inventario ----------

def test_daily_demand_counts_zero_days():
    cons = pd.DataFrame({"date": [date(2026, 10, 19)], "qty": [6.0]})
    m, s = daily_demand(cons, date(2026, 10, 19), date(2026, 10, 24))  # 6 días laborables
    assert m == pytest.approx(1.0)
    assert s == pytest.approx(pd.Series([6, 0, 0, 0, 0, 0]).std(ddof=0))


def test_reorder_point_and_safety_stock():
    ss = safety_stock(2.0, 4, 0.95)
    assert ss == pytest.approx(1.644854 * 2 * 2, rel=1e-4)
    assert reorder_point(3.0, 2.0, 4, 0.95) == pytest.approx(12 + ss)


def test_eoq_and_status():
    assert eoq(1000, 50, 4) == pytest.approx((2 * 1000 * 50 / 4) ** 0.5)
    assert eoq(0, 50, 4) == 0
    assert stock_status(0, 5) == "agotado"
    assert stock_status(4, 5) == "reordenar"
    assert stock_status(6, 5) == "ok"


def test_inventory_table():
    parts = pd.DataFrame({"id": [1], "code": ["R01"], "name": ["Aceite"], "price": [100.0],
                          "stock": [2.0], "lead_time_days": [3.0]})
    cons = pd.DataFrame({"part_id": [1, 1], "date": [date(2026, 10, 19), date(2026, 10, 20)], "qty": [3.0, 3.0]})
    t = inventory_table(parts, cons, date(2026, 10, 19), date(2026, 10, 24))
    assert t.iloc[0]["estado"] == "reordenar"
    assert t.iloc[0]["demanda_diaria"] == pytest.approx(1.0)


# ---------- órdenes, PDF y contraseñas ----------

def test_split_actual_hours():
    assert split_actual_hours({1: 1.0, 2: 3.0}, 2.0) == {1: 0.5, 2: 1.5}
    assert split_actual_hours({1: 0.0, 2: 0.0}, 2.0) == {1: 1.0, 2: 1.0}
    with pytest.raises(ValueError):
        split_actual_hours({1: 1.0}, 0)


def test_priority():
    today = date(2026, 10, 23)
    assert priority(today - timedelta(days=1), today) == "vencida"
    assert priority(today, today) == "hoy"
    assert priority(today + timedelta(days=2), today) == "próxima"


def test_quote_pdf():
    pdf = quote_to_pdf(Quote([QuoteLine("S01", "Cambio de aceite", 0.7, 880)], 450, 0.15), "Ana", "Versa")
    assert pdf[:4] == b"%PDF"
    assert len(pdf) > 1000


def test_password_hashing():
    h = hash_password("secreto1")
    assert verify_password("secreto1", h)
    assert not verify_password("otra-clave", h)
    with pytest.raises(ValueError):
        hash_password("123")


# ---------- base de datos V2 ----------

@pytest.fixture()
def path(tmp_path):
    p = tmp_path / "v2.db"
    seed_database(p, now=NOW)
    return p


def test_seed_v2_tables(path):
    users = db.list_users(path)
    assert {u["role"] for u in users} == {"admin", "recepcion", "tecnico"}
    parts = db.load_parts(path)
    assert (parts["stock"] >= 0).all()
    assert db.load_services(path)["steps"].str.len().gt(0).all()
    assert not db.is_empty(path)


def test_inventory_stock_matches_movements(path):
    with db.connect(path) as conn:
        rows = conn.execute("""SELECT p.stock, COALESCE(SUM(m.qty), 0) FROM parts p
                               LEFT JOIN inventory_movements m ON m.part_id = p.id GROUP BY p.id""").fetchall()
    for stock, total in rows:
        assert stock == pytest.approx(total)


def test_timer_flow_consumes_parts(path):
    orders = db.load_orders(path)
    oid = int(orders[(orders["status"] == "recibida")].iloc[0]["id"])
    items = db.load_items(path)
    service_ids = items[items["order_id"] == oid]["service_id"].tolist()
    stock_before = db.load_parts(path).set_index("id")["stock"].sum()

    db.start_timer(oid, NOW, path)
    with pytest.raises(ValueError):
        db.start_timer(oid, NOW, path)  # ya corriendo
    db.pause_timer(oid, NOW + timedelta(hours=1), path)
    db.start_timer(oid, NOW + timedelta(hours=2), path)
    result = db.finish_with_timer(oid, NOW + timedelta(hours=2, minutes=30), path)
    assert result["actual_hours"] == pytest.approx(1.5)

    order = db.get_order(oid, path)
    assert order["order"]["status"] == "terminada"
    assert sum(i["actual_hours"] for i in order["items"]) == pytest.approx(1.5, abs=1e-3)
    with db.connect(path) as conn:
        has_parts = conn.execute(
            f"SELECT COUNT(*) FROM service_parts WHERE service_id IN ({','.join('?' * len(service_ids))})",
            service_ids).fetchone()[0]
    if has_parts:
        assert db.load_parts(path)["stock"].sum() < stock_before


def test_finish_requires_timer(path):
    orders = db.load_orders(path)
    oid = int(orders[(orders["status"] == "recibida")].iloc[0]["id"])
    with pytest.raises(ValueError):
        db.finish_with_timer(oid, NOW, path)


def test_users_crud(path):
    uid = db.create_user("nuevo", "Nuevo", "recepcion", hash_password("abcdef"), db_path=path)
    with pytest.raises(ValueError):
        db.create_user("nuevo", "Otro", "recepcion", hash_password("abcdef"), db_path=path)
    with pytest.raises(ValueError):
        db.create_user("tec", "Tec", "tecnico", hash_password("abcdef"), None, db_path=path)
    db.update_user(uid, "Nuevo nombre", "admin", None, True, db_path=path)
    assert db.get_user(uid, path)["role"] == "admin"
    db.delete_user(uid, path)
    assert db.get_user(uid, path) is None


def test_inventory_movements(path):
    pid = int(db.load_parts(path).iloc[0]["id"])
    before = float(db.load_parts(path).iloc[0]["stock"])
    assert db.add_movement(pid, 10, "entrada", db_path=path) == pytest.approx(before + 10)
    assert db.add_movement(pid, 3, "salida", db_path=path) == pytest.approx(before + 7)
    with pytest.raises(ValueError):
        db.add_movement(pid, 10_000, "salida", db_path=path)
    with pytest.raises(ValueError):
        db.add_movement(pid, -5, "entrada", db_path=path)


def test_apply_assignments_only_pending(path):
    orders = db.load_orders(path)
    pending = int(orders[orders["status"] == "recibida"].iloc[0]["id"])
    closed = int(orders[orders["status"] == "entregada"].iloc[0]["id"])
    n = db.apply_assignments([
        {"order_id": pending, "technician_id": 2, "bay_id": 3, "scheduled_date": date(2026, 10, 26)},
        {"order_id": closed, "technician_id": 2, "bay_id": 3, "scheduled_date": date(2026, 10, 26)},
    ], path)
    assert n == 1


def test_customers(path):
    c = db.load_customers(path)
    assert len(c) > 10
    assert {"customer", "phone", "ordenes", "total"} <= set(c.columns)


def test_settings_validation(path):
    db.save_settings(500, 0.2, 1.1, 0.9, db_path=path)
    s = db.get_settings(path)
    assert s["efficiency_goal"] == pytest.approx(1.1)
    with pytest.raises(ValueError):
        db.save_settings(500, 0.2, 3.0, db_path=path)


# ---------- prioridad manual y días del Gantt ----------

def test_manual_sequence_by_priority():
    from src.sequencing import MANUAL, sequence
    jobs = [Job("A", 1, 5, 1, priority=2), Job("B", 1, 5, 2, priority=1), Job("C", 1, 5, 0)]
    assert [j.id for j in sequence(jobs, MANUAL)] == ["B", "A", "C"]  # sin prioridad va al final


def test_compare_includes_manual():
    jobs = [Job("A", 2, 4, 1, "T1", 2), Job("B", 1, 4, 2, "T1", 1)]
    table = compare_rules_resources(jobs, ["T1"], ["B1"], include_manual=True)
    assert table["regla"].tolist() == ["FIFO", "SPT", "EDD", "MANUAL"]


def test_work_day_segments():
    from src.workcalendar import work_day_segments
    segs = work_day_segments(datetime(2026, 10, 24, 13, 0), 20)  # sábado 13:00
    assert segs[0]["date"] == date(2026, 10, 24)
    assert segs[0]["end_h"] == pytest.approx(4) and segs[0]["start_clock"] == pytest.approx(13)
    assert segs[1]["date"] == date(2026, 10, 26)  # salta el domingo
    assert segs[1]["start_h"] == pytest.approx(4) and segs[1]["end_h"] == pytest.approx(12)
    assert segs[-1]["end_h"] >= 20


def test_migration_adds_priority_column(tmp_path):
    import sqlite3
    p = tmp_path / "old.db"
    seed_database(p, now=NOW)
    conn = sqlite3.connect(p)
    conn.execute("ALTER TABLE orders DROP COLUMN priority")
    conn.commit()
    conn.close()
    assert not db.ensure_database(p)  # no regenera: migra
    assert "priority" in db.load_orders(p).columns


def test_pinned_technician_respected_in_free_assignment():
    jobs = [Job("A", 4, 9, 1, "T1"), Job("B", 1, 9, 2, "T1", pinned=True)]
    df = schedule_resources(jobs, "FIFO", ["T1", "T2"], ["B1", "B2"], respect_assignment=False).set_index("orden")
    assert df.loc["B", "recurso"] == "T1"  # sin fijar se habría ido a T2 (libre)
    assert df.loc["B", "inicio_h"] == 4
