"""Funciones de IA. La IA solo interpreta y redacta: nunca calcula precios ni métricas.

Cada función recibe `chat_fn` (por defecto el cliente de Groq) para poder probarse sin red.
"""
import json
from typing import Callable

from src.ai.groq_client import AIError, chat

ChatFn = Callable[..., str]

DIAGNOSIS_SYSTEM = (
    "Eres asesor de servicio de un taller mecánico. Con la descripción del cliente, sugiere "
    "servicios ÚNICAMENTE del catálogo proporcionado (usa sus códigos exactos). No inventes "
    "servicios ni precios. Responde solo JSON con esta forma: "
    '{"servicios": [{"codigo": "S01", "motivo": "texto breve", "confianza": 0.0-1.0}], '
    '"preguntas": ["pregunta para aclarar"], "nota": "texto breve"}. '
    "Sugiere máximo 4 servicios. Si no es claro, incluye el diagnóstico por escáner."
)


def _catalog_text(catalog: list[dict]) -> str:
    return "\n".join(f"{c['code']}: {c['name']} ({c.get('category', '')}) — señales: {c.get('keywords', '')}"
                     for c in catalog)


def parse_diagnosis(raw: str, valid_codes: set[str], max_services: int = 4) -> dict:
    """Valida el JSON de la IA. Descarta códigos fuera del catálogo y normaliza la confianza."""
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        raise AIError("La IA no respondió un JSON válido. Intenta de nuevo.")
    if not isinstance(data, dict) or not isinstance(data.get("servicios"), list):
        raise AIError("El JSON de la IA no tiene la lista 'servicios'.")
    services, seen, discarded = [], set(), []
    for entry in data["servicios"]:
        if not isinstance(entry, dict):
            continue
        code = str(entry.get("codigo", "")).strip().upper()
        if code not in valid_codes:
            discarded.append(code)
            continue
        if code in seen:
            continue
        try:
            conf = min(max(float(entry.get("confianza", 0.5)), 0.0), 1.0)
        except (TypeError, ValueError):
            conf = 0.5
        services.append({"codigo": code, "motivo": str(entry.get("motivo", ""))[:300], "confianza": conf})
        seen.add(code)
    questions = [str(q)[:200] for q in data.get("preguntas", []) if isinstance(q, (str, int, float))]
    return {"servicios": services[:max_services], "preguntas": questions[:3],
            "nota": str(data.get("nota", ""))[:500], "descartados": [c for c in discarded if c]}


def suggest_services(problem: str, catalog: list[dict], chat_fn: ChatFn = chat) -> dict:
    """Diagnóstico en texto libre → servicios del catálogo (JSON validado)."""
    if not problem.strip():
        raise AIError("Describe el problema del vehículo.")
    messages = [
        {"role": "system", "content": DIAGNOSIS_SYSTEM},
        {"role": "user", "content": f"Catálogo:\n{_catalog_text(catalog)}\n\nProblema del cliente: {problem}"},
    ]
    raw = chat_fn(messages, json_mode=True, temperature=0.2)
    return parse_diagnosis(raw, {c["code"] for c in catalog})


def executive_summary(kpis: dict, chat_fn: ChatFn = chat) -> str:
    """Resumen ejecutivo en lenguaje claro a partir de KPIs YA calculados."""
    messages = [
        {"role": "system", "content": (
            "Eres analista de operaciones (ingeniería industrial) de un taller mecánico DEMO. "
            "Redacta en español un resumen ejecutivo de máximo 180 palabras: 3 hallazgos y 3 "
            "recomendaciones accionables. Usa SOLO los números del JSON, sin recalcular ni inventar "
            "cifras. Eficiencia > 1 significa más rápido que el estándar. Formato markdown con viñetas.")},
        {"role": "user", "content": json.dumps(kpis, ensure_ascii=False)},
    ]
    return chat_fn(messages, temperature=0.4)


def whatsapp_message(customer: str, vehicle: str, quote: dict, services: list[str],
                     business: str = "AutoServicio Demo", chat_fn: ChatFn = chat) -> str:
    """Mensaje de WhatsApp para el cliente. Los importes vienen ya calculados por fórmula."""
    data = {"cliente": customer or "cliente", "vehiculo": vehicle, "servicios": services,
            "importes_mxn": quote, "negocio": business}
    messages = [
        {"role": "system", "content": (
            "Redacta un mensaje de WhatsApp breve, cordial y profesional en español de México "
            "para enviar una cotización. Usa EXACTAMENTE los importes recibidos (no los cambies ni "
            "calcules otros), con formato $1,234.56 MXN. Incluye lista de servicios, total con IVA, "
            "vigencia de 7 días y una pregunta para confirmar. Máximo 90 palabras, 1-2 emojis. "
            "Termina con: '(Mensaje de demostración, datos ficticios)'.")},
        {"role": "user", "content": json.dumps(data, ensure_ascii=False)},
    ]
    return chat_fn(messages, temperature=0.6)
