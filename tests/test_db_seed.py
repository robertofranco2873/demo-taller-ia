from datetime import date, datetime

import pytest

from src import db
from src.seed import generate, seed_database

NOW = datetime(2026, 10, 23, 13, 0)


@pytest.fixture(scope="module")
def db_path(tmp_path_factory):
    path = tmp_path_factory.mktemp("data") / "test.db"
    seed_database(path, now=NOW)
    return path


def test_generate_is_deterministic():
    a, b = generate(NOW), generate(NOW)
    assert a["orders"] == b["orders"]
    assert 350 <= len(a["orders"]) <= 480


def test_seeded_data_shape(db_path):
    services = db.load_services(db_path)
    assert 20 <= len(services) <= 30
    assert (services["std_hours"] > 0).all()
    orders = db.load_orders(db_path)
    assert set(orders["status"]) <= {"recibida", "en proceso", "terminada", "entregada"}
    assert orders["technician"].nunique() == 4
    assert orders["bay"].nunique() == 3
    assert (orders["status"].isin(["recibida", "en proceso"])).sum() > 0


def test_order_lifecycle(db_path):
    services = db.load_services(db_path)
    sid = int(services.iloc[0]["id"])
    folio = db.create_order("Cliente prueba", "", "Auto", {sid: 2}, 1, 1,
                            date(2026, 10, 30), date(2026, 10, 26), db_path=db_path)
    orders = db.load_orders(db_path)
    order = orders[orders["folio"] == folio].iloc[0]
    assert order["status"] == "recibida"
    assert order["std_hours"] == pytest.approx(services.iloc[0]["std_hours"] * 2)
    oid = int(order["id"])
    db.advance_order(oid, "en proceso", db_path=db_path)
    with pytest.raises(ValueError):
        db.advance_order(oid, "terminada", db_path=db_path)  # falta tiempo real
    items = db.load_items(db_path)
    item_id = int(items[items["order_id"] == oid].iloc[0]["id"])
    db.advance_order(oid, "terminada", actual_hours={item_id: 1.5}, db_path=db_path)
    db.advance_order(oid, "entregada", db_path=db_path)
    order = db.load_orders(db_path).set_index("id").loc[oid]
    assert order["status"] == "entregada"
    assert order["actual_hours"] == pytest.approx(1.5)


def test_invalid_transition(db_path):
    orders = db.load_orders(db_path)
    oid = int(orders[orders["status"] == "recibida"].iloc[0]["id"])
    with pytest.raises(ValueError):
        db.advance_order(oid, "entregada", db_path=db_path)


def test_update_service_validates(db_path):
    sid = int(db.load_services(db_path).iloc[0]["id"])
    with pytest.raises(ValueError):
        db.update_service(sid, "x", "y", -1, 1, 0.1, db_path=db_path)
    db.update_service(sid, "Nuevo nombre", "Mantenimiento", 60, 1.0, 0.2, db_path=db_path)
    s = db.load_services(db_path).set_index("id").loc[sid]
    assert s["std_hours"] == pytest.approx(1.2)
