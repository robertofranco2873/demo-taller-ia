"""Humo de la UI: cada página se ejecuta sin excepciones, con y sin API key."""
from datetime import datetime
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from src import config
from src.seed import seed_database

ROOT = Path(__file__).resolve().parent.parent
PAGES = ["app.py"] + sorted(f"pages/{p.name}" for p in (ROOT / "pages").glob("*.py"))


@pytest.fixture(scope="module")
def demo_db(tmp_path_factory):
    path = tmp_path_factory.mktemp("ui") / "ui.db"
    seed_database(path, now=datetime.now().replace(microsecond=0))
    return path


@pytest.mark.parametrize("page", PAGES)
@pytest.mark.parametrize("with_key", [False, True])
def test_page_runs(page, with_key, demo_db, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", demo_db)
    monkeypatch.setenv("GROQ_API_KEY", "clave-de-prueba" if with_key else "")
    at = AppTest.from_file(str(ROOT / page), default_timeout=60).run()
    assert not at.exception, f"{page}: {[e.value for e in at.exception]}"


def test_ai_diagnosis_flow_with_mocked_groq(demo_db, monkeypatch):
    from src.ai import groq_client

    class Resp:
        status_code = 200

        def json(self):
            content = '{"servicios": [{"codigo": "S07", "motivo": "pedal esponjoso", "confianza": 0.8}]}'
            return {"choices": [{"message": {"content": content}}]}

    monkeypatch.setattr(config, "DB_PATH", demo_db)
    monkeypatch.setenv("GROQ_API_KEY", "clave-de-prueba")
    monkeypatch.setattr(groq_client.requests, "post", lambda *a, **k: Resp())
    at = AppTest.from_file(str(ROOT / "pages/2_Cotizador.py"), default_timeout=60).run()
    at.text_area[0].input("El pedal de freno se siente esponjoso").run()
    next(b for b in at.button if b.label == "Sugerir servicios del catálogo").click().run()
    assert not at.exception
    assert any(v.startswith("S07") for v in at.session_state["quote_sel"])
    assert "TOTAL" in [m.label for m in at.metric]


def test_cotizador_calculates_quote(demo_db, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", demo_db)
    monkeypatch.setenv("GROQ_API_KEY", "")
    at = AppTest.from_file(str(ROOT / "pages/2_Cotizador.py"), default_timeout=60).run()
    at.multiselect(key="quote_sel").select(at.multiselect(key="quote_sel").options[0]).run()
    assert not at.exception
    labels = [m.label for m in at.metric]
    assert "TOTAL" in labels
