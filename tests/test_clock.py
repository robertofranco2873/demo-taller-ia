"""Zona horaria del taller (APP_TZ): el "hoy" no debe cambiar a las 18:00 de México aunque el servidor esté en UTC."""
from datetime import date, datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from src import clock, config
from src.seed import DEMO_PASSWORD, seed_database

UTC = timezone.utc


@pytest.mark.parametrize("utc_instant, local_day, local_hour", [
    (datetime(2026, 10, 23, 23, 59, tzinfo=UTC), date(2026, 10, 23), 17),  # 17:59 en CDMX
    (datetime(2026, 10, 24, 0, 0, tzinfo=UTC), date(2026, 10, 23), 18),    # 18:00: en UTC ya es 24
    (datetime(2026, 10, 24, 5, 59, tzinfo=UTC), date(2026, 10, 23), 23),
    (datetime(2026, 10, 24, 6, 0, tzinfo=UTC), date(2026, 10, 24), 0),     # medianoche en CDMX
])
def test_day_change_follows_app_tz(monkeypatch, utc_instant, local_day, local_hour):
    monkeypatch.delenv("APP_TZ", raising=False)  # por defecto America/Mexico_City (UTC−6, sin horario de verano)
    assert clock.today(utc_instant) == local_day
    assert clock.now(utc_instant).hour == local_hour
    assert clock.now(utc_instant).tzinfo is None


def test_other_timezone(monkeypatch):
    instant = datetime(2026, 10, 24, 0, 30, tzinfo=UTC)
    monkeypatch.setenv("APP_TZ", "UTC")
    assert clock.today(instant) == date(2026, 10, 24)
    monkeypatch.setenv("APP_TZ", "Europe/Madrid")
    assert clock.now(instant).hour == 2


def test_invalid_timezone(monkeypatch):
    monkeypatch.setenv("APP_TZ", "Marte/Olympus")
    with pytest.raises(ValueError, match="APP_TZ"):
        clock.now()


def test_naive_instant_is_treated_as_utc():
    assert clock.now(datetime(2026, 10, 24, 0, 0)) == datetime(2026, 10, 23, 18, 0)


def test_api_uses_app_tz_for_overdue(tmp_path, monkeypatch):
    """18:30 en CDMX (00:30 UTC del día siguiente): una orden que vence "hoy" no debe salir vencida."""
    monkeypatch.delenv("APP_TZ", raising=False)
    monkeypatch.setenv("DEMO_MODE", "false")
    utc_instant = datetime(2026, 10, 24, 0, 30, tzinfo=UTC)
    monkeypatch.setattr(clock, "_utcnow", lambda: utc_instant)
    p = tmp_path / "tz.db"
    seed_database(p)  # la semilla también usa el reloj del taller
    monkeypatch.setattr(config, "DB_PATH", p)
    from api.main import app
    with TestClient(app) as c:
        tok = c.post("/api/auth/login", json={"username": "recepcion", "password": DEMO_PASSWORD}).json()["access_token"]
        h = {"Authorization": f"Bearer {tok}"}
        local_today = date(2026, 10, 23)
        folio = c.post("/api/orders", headers=h, json={
            "customer": "Cliente TZ (ficticio)", "items": [{"service_id": 1}], "technician_id": 1, "bay_id": 1,
            "scheduled_date": str(local_today), "due_date": str(local_today)}).json()["folio"]
        row = next(o for o in c.get(f"/api/orders?q={folio}", headers=h).json() if o["folio"] == folio)
        assert row["vencida"] is False
        assert row["created_at"].startswith("2026-10-23T18:30")
        # Con el servidor "en UTC" la misma orden ya saldría vencida: eso es lo que se evita.
        monkeypatch.setenv("APP_TZ", "UTC")
        row = next(o for o in c.get(f"/api/orders?q={folio}", headers=h).json() if o["folio"] == folio)
        assert row["vencida"] is True
        monkeypatch.delenv("APP_TZ")
        assert c.get("/api/me/day", headers={"Authorization": "Bearer " + c.post(
            "/api/auth/login", json={"username": "tecnico", "password": DEMO_PASSWORD}).json()["access_token"]}
                     ).json()["date"] == str(local_today)
    assert clock.today() == local_today and clock.today() != (utc_instant + timedelta(0)).date()
