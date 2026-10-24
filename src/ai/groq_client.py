"""Cliente mínimo para Groq (API compatible con OpenAI) usando requests."""
import os

import requests
from dotenv import load_dotenv

from src import config

load_dotenv(config.ROOT_DIR / ".env")


class AIError(Exception):
    """Error de IA con mensaje listo para mostrarse al usuario."""


def get_api_key() -> str | None:
    key = os.getenv("GROQ_API_KEY", "").strip()
    return key or None


def get_model() -> str:
    return os.getenv("GROQ_MODEL", config.GROQ_DEFAULT_MODEL)


def chat(messages: list[dict], json_mode: bool = False, temperature: float = 0.3,
         api_key: str | None = None, model: str | None = None,
         timeout: float = config.GROQ_TIMEOUT_S) -> str:
    """Envía la conversación y regresa el texto de la respuesta."""
    key = api_key or get_api_key()
    if not key:
        raise AIError("No hay GROQ_API_KEY configurada. Las funciones de IA están desactivadas.")
    payload = {"model": model or get_model(), "messages": messages, "temperature": temperature}
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
    try:
        resp = requests.post(config.GROQ_URL, json=payload, timeout=timeout,
                             headers={"Authorization": f"Bearer {key}"})
    except requests.Timeout:
        raise AIError(f"Groq no respondió en {timeout:.0f} s (timeout). Intenta de nuevo en un momento.")
    except requests.ConnectionError:
        raise AIError("No se pudo conectar con Groq. Revisa tu conexión a internet.")
    if resp.status_code == 401:
        raise AIError("Groq rechazó la API key (401). Verifica GROQ_API_KEY en tu archivo .env.")
    if resp.status_code == 429:
        raise AIError("Se alcanzó el límite de uso gratuito de Groq (429). Espera un minuto y reintenta.")
    if resp.status_code == 404:
        raise AIError(f"El modelo «{payload['model']}» no existe en Groq o fue retirado (404). "
                      "Cambia GROQ_MODEL en .env (lista en console.groq.com/docs/models).")
    if resp.status_code >= 400:
        raise AIError(f"Groq devolvió un error {resp.status_code}. Intenta más tarde.")
    try:
        return resp.json()["choices"][0]["message"]["content"]
    except (ValueError, KeyError, IndexError):
        raise AIError("Respuesta inesperada de Groq.")
