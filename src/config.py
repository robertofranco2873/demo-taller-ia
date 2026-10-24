"""Constantes de configuración del demo."""
import os
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
DB_PATH = Path(os.getenv("TALLER_DB_PATH", ROOT_DIR / "data" / "taller.db"))

BUSINESS_NAME = "AutoServicio Demo"
DEMO_NOTICE = (
    "⚠️ DEMO con datos ficticios. \"AutoServicio Demo\" no es un negocio real; "
    "clientes, precios y órdenes fueron generados al azar."
)

# Calendario laboral: lunes a sábado, 9:00 a 17:00 (8 h).
HOURS_PER_DAY = 8.0
WORKDAYS = (0, 1, 2, 3, 4, 5)  # 0 = lunes ... 5 = sábado
WORKDAY_START_HOUR = 9

IVA_RATE = 0.16
DEFAULT_LABOR_RATE = 450.0  # MXN por hora estándar
DEFAULT_MARGIN_PCT = 0.15   # margen sobre mano de obra + refacciones

STATUSES = ["recibida", "en proceso", "terminada", "entregada"]
PENDING_STATUSES = ["recibida", "en proceso"]
CLOSED_STATUSES = ["terminada", "entregada"]

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_DEFAULT_MODEL = "llama-3.3-70b-versatile"
GROQ_TIMEOUT_S = 30
