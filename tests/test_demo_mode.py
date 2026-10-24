"""Modo demo pública (DEMO_MODE=true): acciones destructivas bloqueadas y base restablecida."""
import time
from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from src import config, db
from src.seed import DEMO_PASSWORD, seed_database


@pytest.fixture()
def path(tmp_path, monkeypatch):
    p = tmp_path / "demo.db"
    seed_database(p, now=datetime.now().replace(microsecond=0))
    monkeypatch.setattr(config, "DB_PATH", p)
    monkeypatch.setenv("GROQ_API_KEY", " ")
    return p


def _client(monkeypatch, demo: bool):
    monkeypatch.setenv("DEMO_MODE", "true" if demo else "false")
    from api.main import app
    return TestClient(app)


def _admin(c):
    tok = c.post("/api/auth/login", json={"username": "gerente", "password": DEMO_PASSWORD}).json()["access_token"]
    return {"Authorization": f"Bearer {tok}"}


def _blocked(r, accion):
    assert r.status_code == 403, r.text
    assert "Desactivado en la demo pública" in r.json()["detail"] and accion in r.json()["detail"]


def test_demo_blocks_destructive_actions(path, monkeypatch):
    with _client(monkeypatch, demo=True) as c:
        h = _admin(c)
        info = c.get("/api/app-info").json()
        assert info["demo_mode"] is True and info["reset_hours"] == 24 and info["next_reset"]
        users = {u["username"]: u for u in c.get("/api/users", headers=h).json()["users"]}
        lucia = users["lucia"]

        _blocked(c.post("/api/admin/reseed", headers=h), "regenerar")
        _blocked(c.post("/api/admin/restore", headers=h, files={"file": ("x.db", b"SQLite format 3\x00")}), "restaurar")
        _blocked(c.delete(f"/api/users/{lucia['id']}", headers=h), "borrar")
        base = {"name": lucia["name"], "role": "tecnico", "technician_id": lucia["technician_id"], "active": True}
        _blocked(c.put(f"/api/users/{lucia['id']}", headers=h, json={**base, "password": "nueva123"}), "contraseñas")
        _blocked(c.put(f"/api/users/{lucia['id']}", headers=h, json={**base, "active": False}), "desactivar")
        _blocked(c.put(f"/api/users/{lucia['id']}", headers=h, json={**base, "role": "admin"}), "rol")

        # Lo no destructivo sigue funcionando en la demo
        assert c.put(f"/api/users/{lucia['id']}", headers=h, json={**base, "name": "Lucía editada"}).status_code == 200
        assert c.get("/api/admin/backup", headers=h).content.startswith(b"SQLite format 3")
        r = c.post("/api/users", headers=h, json={"username": "visitante", "name": "Visitante", "role": "recepcion",
                                                  "password": "visita123"})
        assert r.status_code == 201
        # El login de los usuarios demo sigue intacto
        assert c.post("/api/auth/login", json={"username": "lucia", "password": DEMO_PASSWORD}).status_code == 200


def test_actions_work_outside_demo(path, monkeypatch):
    with _client(monkeypatch, demo=False) as c:
        h = _admin(c)
        assert c.get("/api/app-info").json() == {"demo_mode": False, "reset_hours": None, "last_reset": None,
                                                 "next_reset": None}
        users = {u["username"]: u for u in c.get("/api/users", headers=h).json()["users"]}
        lucia = users["lucia"]
        base = {"name": lucia["name"], "role": "tecnico", "technician_id": lucia["technician_id"], "active": True}
        assert c.put(f"/api/users/{lucia['id']}", headers=h, json={**base, "password": "nueva123"}).status_code == 200
        assert c.post("/api/auth/login", json={"username": "lucia", "password": "nueva123"}).status_code == 200
        assert c.put(f"/api/users/{lucia['id']}", headers=h, json={**base, "active": False}).status_code == 200
        assert c.delete(f"/api/users/{lucia['id']}", headers=h).status_code == 200
        backup = c.get("/api/admin/backup", headers=h).content
        assert c.post("/api/admin/restore", headers=h, files={"file": ("ok.db", backup)}).status_code == 200
        assert c.post("/api/admin/reseed", headers=h).status_code == 200


def test_demo_resets_database_on_startup(path, monkeypatch):
    db.create_user("huella", "Cambio de un visitante", "recepcion", "x" * 60, db_path=path)
    with _client(monkeypatch, demo=True):
        assert db.get_user_auth("huella", path) is None  # se restableció al arrancar
    monkeypatch.setenv("DEMO_MODE", "false")
    db.create_user("huella", "Cambio", "recepcion", "x" * 60, db_path=path)
    with _client(monkeypatch, demo=False):
        assert db.get_user_auth("huella", path) is not None  # fuera de la demo no se toca


def test_demo_periodic_reset(path, monkeypatch):
    monkeypatch.setattr(config, "DEMO_RESET_HOURS", 1 / 3600)  # 1 segundo para la prueba
    with _client(monkeypatch, demo=True) as c:
        first = c.get("/api/app-info").json()["last_reset"]
        db.create_user("huella", "Cambio", "recepcion", "x" * 60, db_path=path)
        for _ in range(40):
            time.sleep(0.25)
            if c.get("/api/app-info").json()["last_reset"] != first:
                break
        assert c.get("/api/app-info").json()["last_reset"] != first
        assert db.get_user_auth("huella", path) is None
