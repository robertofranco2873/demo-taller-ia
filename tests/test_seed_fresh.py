"""La semilla genera fechas relativas a "ahora": al abrir la demo siempre se ve un día normal de taller."""
from datetime import datetime, timedelta

import pytest

from src import clock
from src.seed import generate

SIMULATED_NOWS = [
    datetime(2026, 10, 21, 11, 0),   # miércoles a media mañana
    datetime(2026, 10, 24, 13, 0),   # sábado
    datetime(2026, 10, 25, 12, 0),   # domingo (taller cerrado)
    datetime(2026, 10, 26, 9, 5),    # lunes recién abierto
    datetime(2026, 12, 24, 10, 0),   # temporada alta
    datetime(2027, 3, 3, 16, 40),    # otro año, casi al cierre
    datetime(2028, 2, 29, 12, 0),    # año bisiesto
]


@pytest.mark.parametrize("now", SIMULATED_NOWS, ids=lambda d: d.strftime("%a-%Y-%m-%d-%H%M"))
def test_seed_is_realistic_for_any_date(now):
    orders = generate(now)["orders"]
    pending = [o for o in orders if o["status"] in ("recibida", "en proceso")]
    in_progress = [o for o in orders if o["status"] == "en proceso"]
    overdue = [o for o in pending if o["due_date"] < now.date()]
    ready = [o for o in orders if o["status"] == "terminada"]
    recent = [o for o in orders if now - o["created_at"] <= timedelta(days=30)]

    assert 350 <= len(orders) <= 480                       # ~6 meses de historial
    assert min(o["created_at"] for o in orders) <= now - timedelta(days=175)
    assert len(recent) >= 50                               # historial reciente
    assert 8 <= len(pending) <= 40                         # trabajo en cola
    assert len(in_progress) >= 2                           # órdenes en curso
    assert 1 <= len(overdue) <= 5                          # solo unas pocas vencidas...
    assert len(overdue) <= max(1, len(pending) * 0.3)      # ...no todo en rojo
    assert len(ready) >= 1                                 # listas para entregar
    # Nada en el futuro
    assert all(o["created_at"] <= now for o in orders)
    assert all(o["started_at"] is None or o["started_at"] <= now for o in orders)
    assert all(o["finished_at"] is None or o["finished_at"] <= now for o in orders)
    assert all(o["delivered_at"] is None or o["delivered_at"] <= now for o in orders)
    assert all(o["due_date"] >= o["created_at"].date() for o in orders)
    # Coherencia de estados
    assert all(o["started_at"] is not None for o in in_progress)
    assert all(o["finished_at"] is not None and o["delivered_at"] is None for o in ready)


def test_seed_follows_app_clock(tmp_path, monkeypatch):
    """Sin fecha explícita, la semilla usa el reloj del taller (APP_TZ), no el del servidor (UTC)."""
    from datetime import timezone

    from src import db
    from src.seed import seed_database
    monkeypatch.setattr(clock, "_utcnow", lambda: datetime(2026, 10, 24, 0, 30, tzinfo=timezone.utc))
    monkeypatch.delenv("APP_TZ", raising=False)
    p = tmp_path / "reloj.db"
    seed_database(p)
    orders = db.load_orders(p)
    local_now = datetime(2026, 10, 23, 18, 30)  # 00:30 UTC = 18:30 en CDMX
    assert orders["created_at"].max() <= local_now
    assert orders["created_at"].max().date() == local_now.date()  # nada "del 24" aunque en UTC ya lo sea


def test_generate_relative_shift():
    """El mismo patrón se desplaza con la fecha: la orden más reciente siempre es de "hoy" o el último día laborable."""
    for now in SIMULATED_NOWS:
        latest = max(o["created_at"] for o in generate(now)["orders"])
        assert now - latest <= timedelta(days=2)
