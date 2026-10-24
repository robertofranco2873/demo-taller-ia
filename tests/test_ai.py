import json
from unittest.mock import patch

import pytest
import requests

from src.ai import groq_client
from src.ai.features import executive_summary, parse_diagnosis, suggest_services, whatsapp_message
from src.ai.groq_client import AIError

CATALOG = [{"code": "S03", "name": "Balatas delanteras", "category": "Frenos", "keywords": "ruido al frenar"},
           {"code": "S21", "name": "Diagnóstico", "category": "Diagnóstico", "keywords": "falla"}]


def test_parse_diagnosis_filters_unknown_codes():
    raw = json.dumps({"servicios": [
        {"codigo": "s03", "motivo": "ruido", "confianza": 1.7},
        {"codigo": "X99", "motivo": "inventado"},
        {"codigo": "S03", "motivo": "duplicado"},
    ], "preguntas": ["¿Desde cuándo?"]})
    out = parse_diagnosis(raw, {"S03", "S21"})
    assert [s["codigo"] for s in out["servicios"]] == ["S03"]
    assert out["servicios"][0]["confianza"] == 1.0
    assert out["descartados"] == ["X99"]


@pytest.mark.parametrize("raw", ["no es json", "[]", '{"otra": 1}'])
def test_parse_diagnosis_invalid(raw):
    with pytest.raises(AIError):
        parse_diagnosis(raw, {"S03"})


def test_suggest_services_uses_chat_fn():
    def fake_chat(messages, **kwargs):
        assert kwargs["json_mode"] is True
        assert "S03" in messages[1]["content"]
        return '{"servicios": [{"codigo": "S03", "motivo": "ruido", "confianza": 0.9}]}'
    out = suggest_services("hace ruido al frenar", CATALOG, chat_fn=fake_chat)
    assert out["servicios"][0]["codigo"] == "S03"


def test_summary_and_whatsapp_pass_numbers():
    captured = {}

    def fake_chat(messages, **kwargs):
        captured["content"] = messages[-1]["content"]
        return "ok"
    assert executive_summary({"ticket_promedio": 1234.5}, chat_fn=fake_chat) == "ok"
    assert "$1,234.50 MXN" in captured["content"]  # ya formateado: la IA solo copia
    whatsapp_message("Ana", "Versa", {"total": 999.99}, ["Balatas"], chat_fn=fake_chat)
    assert "999.99" in captured["content"]


class FakeResp:
    def __init__(self, status, body=None):
        self.status_code = status
        self._body = body or {}

    def json(self):
        return self._body


@pytest.mark.parametrize("status, text", [(401, "401"), (404, "GROQ_MODEL"), (429, "429"), (500, "500")])
def test_chat_http_errors(status, text):
    with patch.object(groq_client.requests, "post", return_value=FakeResp(status)):
        with pytest.raises(AIError, match=text):
            groq_client.chat([{"role": "user", "content": "hola"}], api_key="k")


def test_chat_timeout():
    with patch.object(groq_client.requests, "post", side_effect=requests.Timeout):
        with pytest.raises(AIError, match="timeout"):
            groq_client.chat([], api_key="k")


def test_chat_ok():
    body = {"choices": [{"message": {"content": "respuesta"}}]}
    with patch.object(groq_client.requests, "post", return_value=FakeResp(200, body)):
        assert groq_client.chat([], api_key="k") == "respuesta"


def test_chat_without_key(monkeypatch):
    monkeypatch.setattr(groq_client, "get_api_key", lambda: None)
    with pytest.raises(AIError, match="GROQ_API_KEY"):
        groq_client.chat([])


def test_kpis_formatted_for_ai_without_calculating():
    from src.ai.features import format_kpis_for_text
    out = format_kpis_for_text({"tasa_cierre": 0.939, "ticket_promedio": 4375.27, "backlog_ordenes": 26,
                                "eficiencia_por_tecnico": {"Carlos": 1.108}, "ingresos_por_mes": {"2026-08": 440276.07},
                                "utilizacion_bahias": {"B1": 0.254}, "periodo": "2026-04-24 a 2026-10-23"})
    assert out["tasa_cierre"] == "93.9 %" and out["ticket_promedio"] == "$4,375.27 MXN"
    assert out["eficiencia_por_tecnico"]["Carlos"] == "110.8 %" and out["utilizacion_bahias"]["B1"] == "25.4 %"
    assert out["ingresos_por_mes"]["2026-08"] == "$440,276.07 MXN"
    assert out["backlog_ordenes"] == 26 and out["periodo"] == "2026-04-24 a 2026-10-23"


def test_summary_prompt_forbids_calculations():
    captured = {}

    def fake_chat(messages, **kwargs):
        captured["system"] = messages[0]["content"]
        captured["user"] = messages[1]["content"]
        return "ok"
    executive_summary({"tasa_cierre": 0.5}, chat_fn=fake_chat)
    assert "NO calcules" in captured["system"] and "50.0 %" in captured["user"]
