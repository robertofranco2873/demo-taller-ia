from datetime import date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from src import config, db
from src.seed import DEMO_PASSWORD, seed_database

ROLES_USERS = {"admin": "gerente", "recepcion": "recepcion", "tecnico": "tecnico"}


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    path = tmp_path_factory.mktemp("api") / "api.db"
    seed_database(path, now=datetime.now().replace(microsecond=0))
    mp = pytest.MonkeyPatch()
    mp.setattr(config, "DB_PATH", path)
    mp.setenv("GROQ_API_KEY", "")
    from api.main import app
    with TestClient(app) as c:
        yield c
    mp.undo()


@pytest.fixture(scope="module")
def tokens(client):
    out = {}
    for role, user in ROLES_USERS.items():
        r = client.post("/api/auth/login", json={"username": user, "password": DEMO_PASSWORD})
        assert r.status_code == 200, r.text
        out[role] = {"Authorization": f"Bearer {r.json()['access_token']}"}
    return out


# ---------- autenticación ----------

def test_login_wrong_password(client):
    r = client.post("/api/auth/login", json={"username": "gerente", "password": "incorrecta"})
    assert r.status_code == 401


def test_requires_token(client):
    assert client.get("/api/services").status_code == 401
    assert client.get("/api/services", headers={"Authorization": "Bearer basura"}).status_code == 401


def test_me_and_demo_users(client, tokens):
    assert client.get("/api/auth/me", headers=tokens["tecnico"]).json()["technician_id"] == 1
    demo = client.get("/api/auth/demo-users").json()
    assert {u["role"] for u in demo} == {"admin", "recepcion", "tecnico"}


def test_password_is_hashed_in_db(client):
    user = db.get_user_auth("gerente")
    assert user["password_hash"].startswith("$2") and DEMO_PASSWORD not in user["password_hash"]


# ---------- matriz de permisos (validados en el backend) ----------

A, R, T = "admin", "recepcion", "tecnico"
PERMISSIONS = [
    ("get", "/api/services", {A, R, T}),
    ("get", "/api/services/1", {A, R, T}),
    ("put", "/api/services/1", {A}),
    ("post", "/api/time-study", {A, R, T}),
    ("get", "/api/parts", {A, R}),
    ("get", "/api/technicians", {A, R}),
    ("post", "/api/quotes", {A, R}),
    ("post", "/api/quotes/pdf", {A, R}),
    ("get", "/api/orders", {A, R}),
    ("post", "/api/orders", {A, R}),
    ("get", "/api/customers", {A, R}),
    ("get", "/api/dashboard", {A}),
    ("get", "/api/dashboard/kpi/ticket", {A}),
    ("get", "/api/pareto", {A}),
    ("get", "/api/capacity", {A}),
    ("get", "/api/sequencing", {A}),
    ("post", "/api/sequencing/apply", {A}),
    ("get", "/api/spc/services", {A}),
    ("get", "/api/inventory", {A}),
    ("get", "/api/users", {A}),
    ("post", "/api/users", {A}),
    ("get", "/api/settings", {A, R}),
    ("put", "/api/settings", {A}),
    ("get", "/api/admin/backup", {A}),
    ("post", "/api/admin/reseed", {A}),
    ("get", "/api/me/day", {T}),
    ("get", "/api/me/indicators", {T}),
    ("get", "/api/ai/status", {A, R, T}),
    ("post", "/api/ai/diagnosis", {A, R}),
    ("post", "/api/ai/summary", {A}),
    ("post", "/api/ai/whatsapp", {A, R}),
    ("get", "/api/notifications", {A, R, T}),
]


@pytest.mark.parametrize("method, path, allowed", PERMISSIONS, ids=[f"{m} {p}" for m, p, _ in PERMISSIONS])
@pytest.mark.parametrize("role", [A, R, T])
def test_permission_matrix(client, tokens, method, path, allowed, role):
    if path == "/api/admin/reseed" and role in allowed:
        pytest.skip("Se prueba aparte para no borrar los datos del módulo.")
    r = client.request(method.upper(), path, headers=tokens[role], json={} if method in ("post", "put") else None)
    if role in allowed:
        assert r.status_code != 403, f"{role} debería poder usar {method.upper()} {path}"
    else:
        assert r.status_code == 403, f"{role} NO debería poder usar {method.upper()} {path} ({r.status_code})"


# ---------- funcional ----------

def test_services_and_detail(client, tokens):
    services = client.get("/api/services", headers=tokens["tecnico"]).json()
    assert len(services) >= 20 and services[0]["std_hours"] > 0
    detail = client.get(f"/api/services/{services[0]['id']}", headers=tokens["tecnico"]).json()
    assert detail["steps"] and "parts" in detail


def test_time_study(client, tokens):
    r = client.post("/api/time-study", headers=tokens["admin"],
                    json={"observations": [10, 11, 9, 10], "rating_factor": 1.1, "allowance_pct": 0.15}).json()
    assert r["normal_min"] == pytest.approx(11)
    assert r["estandar_min"] == pytest.approx(12.65)
    assert r["observaciones_necesarias"] >= 1


def test_quote_and_exports(client, tokens):
    body = {"items": [{"service_id": 1, "qty": 1}, {"service_id": 3, "qty": 2}], "customer": "Ana"}
    q = client.post("/api/quotes", headers=tokens["recepcion"], json=body).json()
    assert q["total"] == pytest.approx(round(q["subtotal"] * 1.16, 2), abs=0.01)
    assert len(q["lines"]) == 2
    pdf = client.post("/api/quotes/pdf", headers=tokens["recepcion"], json=body)
    assert pdf.content[:4] == b"%PDF"
    xls = client.post("/api/quotes/excel", headers=tokens["recepcion"], json=body)
    assert xls.content[:2] == b"PK"
    assert client.post("/api/quotes", headers=tokens["recepcion"],
                       json={"items": [{"service_id": 9999}]}).status_code == 404


def test_order_lifecycle_by_reception(client, tokens):
    h = tokens["recepcion"]
    r = client.post("/api/orders", headers=h, json={
        "customer": "Cliente API (ficticio)", "items": [{"service_id": 1, "qty": 1}], "technician_id": 2,
        "bay_id": 1, "scheduled_date": str(date.today()), "due_date": str(date.today() + timedelta(days=2))})
    assert r.status_code == 201
    folio = r.json()["folio"]
    order = next(o for o in client.get(f"/api/orders?q={folio}", headers=h).json() if o["folio"] == folio)
    oid = order["id"]
    assert client.post(f"/api/orders/{oid}/advance", headers=h, json={"status": "en proceso"}).status_code == 200
    detail = client.get(f"/api/orders/{oid}", headers=h).json()
    item_id = detail["items"][0]["id"]
    bad = client.post(f"/api/orders/{oid}/advance", headers=h, json={"status": "terminada"})
    assert bad.status_code == 400
    ok = client.post(f"/api/orders/{oid}/advance", headers=h,
                     json={"status": "terminada", "actual_hours": {str(item_id): 0.8}})
    assert ok.status_code == 200
    assert client.get(f"/api/orders/{oid}", headers=h).json()["order"]["status"] == "terminada"


def test_technician_cannot_see_others_orders(client, tokens):
    orders = client.get("/api/orders?status=recibida", headers=tokens["admin"]).json()
    other = next(o for o in orders if o["technician_id"] != 1)
    assert client.get(f"/api/orders/{other['id']}", headers=tokens["tecnico"]).status_code == 403
    assert client.post(f"/api/me/orders/{other['id']}/start", headers=tokens["tecnico"]).status_code == 403


def test_my_day_timer_flow(client, tokens):
    h = tokens["tecnico"]
    day = client.get("/api/me/day", headers=h).json()
    assert day["orders"], "El técnico demo debe tener órdenes pendientes"
    prios = [o["priority"] for o in day["orders"]]
    assert prios == sorted(prios, key=["vencida", "hoy", "próxima"].index)
    target = next(o for o in day["orders"] if not o["timer"]["running"])
    oid = target["id"]
    assert client.post(f"/api/me/orders/{oid}/start", headers=h).json()["running"] is True
    assert client.post(f"/api/me/orders/{oid}/start", headers=h).status_code == 400
    assert client.post(f"/api/me/orders/{oid}/pause", headers=h).json()["running"] is False
    client.post(f"/api/me/orders/{oid}/start", headers=h)
    done = client.post(f"/api/me/orders/{oid}/finish", headers=h)
    assert done.status_code == 200, done.text
    assert {"efficiency", "goal_reached"} <= set(done.json())
    ind = client.get("/api/me/indicators", headers=h).json()
    assert ind["ordenes_cerradas"] >= 1 and ind["tendencia"]


def test_dashboard_and_details(client, tokens):
    h = tokens["admin"]
    d = client.get("/api/dashboard", headers=h).json()
    assert d["kpis"]["ticket"] > 0 and d["monthly"] and d["efficiency"]
    month = d["monthly"][-2]["mes"]
    m = client.get(f"/api/dashboard/month/{month}", headers=h).json()
    assert m["ordenes"] and len(m["comparativo"]) == 5 and m["tecnicos"]
    t = client.get("/api/dashboard/technician/1", headers=h).json()
    assert t["eficiencia"] > 0 and t["tendencia"]
    for key in ["ingresos", "ticket", "lead_time", "eficiencia", "utilizacion", "backlog"]:
        k = client.get(f"/api/dashboard/kpi/{key}", headers=h).json()
        assert k["formula"] and k["tendencia"]
    assert client.get("/api/dashboard/kpi/inventado", headers=h).status_code == 404
    start = date.today() - timedelta(days=30)
    filt = client.get(f"/api/dashboard?start={start}&end={date.today()}", headers=h).json()
    assert filt["kpis"]["ingresos"] < d["kpis"]["ingresos"]


def test_pareto_drilldown(client, tokens):
    h = tokens["admin"]
    p = client.get("/api/pareto?by=ingreso", headers=h).json()
    assert p["rows"][0]["clase"] == "A" and 0 < p["vital_few"] < p["total"]
    sid = p["rows"][0]["service_id"]
    lvl2 = client.get(f"/api/pareto/service/{sid}", headers=h).json()
    assert lvl2["mensual"] and lvl2["tecnicos"] and lvl2["control"]["limits"]["lc"] > 0
    lvl3 = client.get(f"/api/pareto/service/{sid}/orders", headers=h).json()
    assert lvl3 and "folio" in lvl3[0]
    freq = client.get("/api/pareto?by=frecuencia", headers=h).json()
    assert freq["rows"][0]["valor"] >= freq["rows"][-1]["valor"]


def test_capacity(client, tokens):
    c = client.get("/api/capacity", headers=tokens["admin"]).json()
    assert len(c["rows"]) == 4 and len(c["overview"]) == 12


def test_sequencing_and_apply(client, tokens):
    h = tokens["admin"]
    for mode in ["assigned", "shop"]:
        s = client.get(f"/api/sequencing?mode={mode}&rule=SPT", headers=h).json()
        assert {"FIFO", "SPT", "EDD"} <= {r["regla"] for r in s["comparison"]} and s["schedule"][0]["inicio"]
    one = client.get("/api/sequencing?mode=technician&technician_id=1", headers=h).json()
    assert {r["recurso"] for r in one["schedule"]} == {db.load_technicians().iloc[0]["name"]}
    r = client.post("/api/sequencing/apply", headers=h, json={"rule": "EDD", "mode": "shop"})
    assert r.json()["updated"] > 0


def test_spc_endpoints(client, tokens):
    h = tokens["admin"]
    services = client.get("/api/spc/services", headers=h).json()
    sid = services[0]["service_id"]
    ind = client.get(f"/api/spc/individuals?service_id={sid}", headers=h).json()
    assert ind["limits"]["lsc"] > ind["limits"]["lc"]
    by_tech = client.get(f"/api/spc/individuals?service_id={sid}&technician_id=1", headers=h)
    assert by_tech.status_code in (200, 400)
    xr = client.get(f"/api/spc/xbar-r?service_id={sid}&subgroup=5", headers=h).json()
    assert xr["limits"]["n"] == 5 and xr["subgroups"]


def test_inventory(client, tokens):
    h = tokens["admin"]
    inv = client.get("/api/inventory", headers=h).json()
    assert inv["rows"] and {"punto_reorden", "eoq", "estado"} <= set(inv["rows"][0])
    pid = inv["rows"][0]["id"]
    r = client.post(f"/api/inventory/{pid}/movements", headers=h, json={"qty": 5, "kind": "entrada"})
    assert r.status_code == 200
    assert client.get(f"/api/inventory/{pid}/movements", headers=h).json()[0]["kind"] == "entrada"


def test_users_admin(client, tokens):
    h = tokens["admin"]
    r = client.post("/api/users", headers=h, json={"username": "nuevo.tec", "name": "Nuevo", "role": "tecnico",
                                                  "password": "clave123", "technician_id": 3})
    assert r.status_code == 201
    login = client.post("/api/auth/login", json={"username": "nuevo.tec", "password": "clave123"})
    assert login.status_code == 200
    uid = r.json()["id"]
    client.put(f"/api/users/{uid}", headers=h, json={"name": "Nuevo", "role": "tecnico", "technician_id": 3,
                                                    "active": False})
    assert client.post("/api/auth/login", json={"username": "nuevo.tec", "password": "clave123"}).status_code == 401
    me = client.get("/api/auth/me", headers=h).json()
    assert client.delete(f"/api/users/{me['id']}", headers=h).status_code == 400


def test_settings_and_backup(client, tokens):
    h = tokens["admin"]
    s = client.get("/api/settings", headers=h).json()
    s["efficiency_goal"] = 1.05
    assert client.put("/api/settings", headers=h, json=s).json()["efficiency_goal"] == 1.05
    backup = client.get("/api/admin/backup", headers=h)
    assert backup.content.startswith(b"SQLite format 3")
    r = client.post("/api/admin/restore", headers=h, files={"file": ("x.db", b"no es sqlite")})
    assert r.status_code == 400
    r = client.post("/api/admin/restore", headers=h, files={"file": ("ok.db", backup.content)})
    assert r.status_code == 200


def test_ai_disabled_without_key(client, tokens):
    assert client.get("/api/ai/status", headers=tokens["recepcion"]).json()["enabled"] is False
    r = client.post("/api/ai/diagnosis", headers=tokens["recepcion"], json={"problem": "hace ruido al frenar"})
    assert r.status_code == 503


def test_ai_diagnosis_with_mocked_groq(client, tokens, monkeypatch):
    from src.ai import groq_client

    class Resp:
        status_code = 200

        def json(self):
            return {"choices": [{"message": {"content":
                    '{"servicios": [{"codigo": "S03", "motivo": "ruido", "confianza": 0.9}, {"codigo": "ZZ9"}]}'}}]}

    monkeypatch.setenv("GROQ_API_KEY", "clave")
    monkeypatch.setattr(groq_client.requests, "post", lambda *a, **k: Resp())
    r = client.post("/api/ai/diagnosis", headers=tokens["recepcion"], json={"problem": "hace ruido al frenar"})
    assert r.status_code == 200
    body = r.json()
    assert [s["codigo"] for s in body["servicios"]] == ["S03"] and body["descartados"] == ["ZZ9"]
    assert body["quote"]["total"] > 0


def test_ai_groq_errors_map_to_502(client, tokens, monkeypatch):
    from src.ai import groq_client

    class Resp:
        status_code = 429

    monkeypatch.setenv("GROQ_API_KEY", "clave")
    monkeypatch.setattr(groq_client.requests, "post", lambda *a, **k: Resp())
    r = client.post("/api/ai/whatsapp", headers=tokens["recepcion"], json={"items": [{"service_id": 1}]})
    assert r.status_code == 502 and "429" in r.json()["detail"]


def test_search_respects_role(client, tokens):
    admin = client.get("/api/search?q=pareto", headers=tokens["admin"]).json()
    assert any(x["id"] == "pareto" for x in admin)
    tech = client.get("/api/search?q=pareto", headers=tokens["tecnico"]).json()
    assert not any(x["type"] == "modulo" and x["id"] == "pareto" for x in tech)
    svc = client.get("/api/search?q=balatas", headers=tokens["tecnico"]).json()
    assert any(x["type"] == "servicio" for x in svc)
    orders = client.get("/api/search?q=OT-", headers=tokens["tecnico"]).json()
    assert all(x["path"] == "/mi-dia" for x in orders if x["type"] == "orden")


def test_notifications(client, tokens):
    assert isinstance(client.get("/api/notifications", headers=tokens["admin"]).json(), list)
    assert isinstance(client.get("/api/notifications", headers=tokens["tecnico"]).json(), list)


def test_reseed_admin(client, tokens):
    r = client.post("/api/admin/reseed", headers=tokens["admin"])
    assert r.status_code == 200 and r.json()["orders"] > 300


def test_openapi_documented(client):
    spec = client.get("/openapi.json").json()
    assert spec["info"]["title"] == "AutoServicio Demo API"
    assert "/api/pareto/service/{service_id}" in spec["paths"]


def test_sequencing_manual_priorities(client, tokens):
    h = tokens["admin"]
    base = client.get("/api/sequencing?mode=shop&rule=EDD", headers=h).json()
    assert base["days"] and base["days"][0]["label"][:3] in {"lun", "mar", "mié", "jue", "vie", "sáb"}
    folios = [r["orden"] for r in sorted(base["schedule"], key=lambda r: r["posicion"])]
    reversed_prio = {f: i + 1 for i, f in enumerate(reversed(folios))}
    sim = client.post("/api/sequencing/simulate", headers=h,
                      json={"rule": "MANUAL", "mode": "shop", "priorities": reversed_prio}).json()
    first = min(sim["schedule"], key=lambda r: r["posicion"])
    assert first["orden"] == folios[-1]
    assert [r["regla"] for r in sim["comparison"]][-1] == "MANUAL"

    r = client.post("/api/sequencing/apply", headers=h,
                    json={"rule": "MANUAL", "mode": "shop", "priorities": reversed_prio})
    assert r.json()["updated"] == len(folios)
    stored = client.get("/api/sequencing?mode=shop&rule=MANUAL", headers=h).json()
    assert stored["has_manual"] is True
    assert min(stored["schedule"], key=lambda r: r["posicion"])["orden"] == folios[-1]


def test_my_day_follows_stored_sequence(client, tokens):
    day = client.get("/api/me/day", headers=tokens["tecnico"]).json()["orders"]
    seqs = [o["sequence"] for o in day if o["sequence"] is not None]
    assert seqs == sorted(seqs)


def test_simulate_rejects_unknown_rule(client, tokens):
    r = client.post("/api/sequencing/simulate", headers=tokens["admin"], json={"rule": "LPT"})
    assert r.status_code == 400
    assert client.post("/api/sequencing/simulate", headers=tokens["recepcion"], json={}).status_code == 403


def test_sequencing_move_order_to_other_technician(client, tokens):
    h = tokens["admin"]
    base = client.get("/api/sequencing?mode=assigned&rule=EDD", headers=h).json()
    row = base["schedule"][0]
    techs = client.get("/api/technicians", headers=h).json()
    target = next(t for t in techs if t["name"] != row["recurso"])
    sim = client.post("/api/sequencing/simulate", headers=h, json={
        "rule": "EDD", "mode": "assigned", "technicians": {row["orden"]: target["id"]}}).json()
    moved = next(r for r in sim["schedule"] if r["orden"] == row["orden"])
    assert moved["recurso"] == target["name"] and moved["tecnico_actual"] == row["recurso"]
    # También se respeta en "Taller completo"
    shop = client.post("/api/sequencing/simulate", headers=h, json={
        "rule": "EDD", "mode": "shop", "technicians": {row["orden"]: target["id"]}}).json()
    assert next(r for r in shop["schedule"] if r["orden"] == row["orden"])["recurso"] == target["name"]
    # Guardar persiste el técnico
    r = client.post("/api/sequencing/apply", headers=h, json={
        "rule": "EDD", "mode": "assigned", "technicians": {row["orden"]: target["id"]}})
    assert r.status_code == 200
    orders = client.get(f"/api/orders?q={row['orden']}", headers=h).json()
    assert next(o for o in orders if o["folio"] == row["orden"])["technician_id"] == target["id"]


def test_sequencing_move_rejected_in_technician_mode(client, tokens):
    h = tokens["admin"]
    one = client.get("/api/sequencing?mode=technician&technician_id=1", headers=h).json()
    folio = one["schedule"][0]["orden"]
    r = client.post("/api/sequencing/simulate", headers=h, json={
        "rule": "EDD", "mode": "technician", "technician_id": 1, "technicians": {folio: 2}})
    assert r.status_code == 400
    bad = client.post("/api/sequencing/simulate", headers=h, json={"technicians": {folio: 999}})
    assert bad.status_code == 400
