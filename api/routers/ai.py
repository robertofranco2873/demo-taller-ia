"""IA opcional (Groq). Solo interpreta y redacta; los importes y KPIs vienen de las fórmulas."""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from api.core import ADMIN, ALL_ROLES, STAFF, clean, parse_range, require_roles
from api.routers.quotes import QuoteIn, build, quote_json
from src import config, db, kpis
from src.ai.features import executive_summary, suggest_services, whatsapp_message
from src.ai.groq_client import AIError, get_api_key, get_model

router = APIRouter(prefix="/api/ai", tags=["IA opcional (Groq)"])


def _require_ai():
    if not get_api_key():
        raise HTTPException(503, "Las funciones de IA están desactivadas: falta GROQ_API_KEY.")


def _ai_error(e: AIError) -> HTTPException:
    return HTTPException(502, str(e))


@router.get("/status", summary="¿Hay IA configurada?")
def status(_: dict = Depends(require_roles(*ALL_ROLES))):
    enabled = get_api_key() is not None
    return {"enabled": enabled, "model": get_model() if enabled else None}


class DiagnosisIn(BaseModel):
    problem: str = Field(min_length=5, max_length=1000)


@router.post("/diagnosis", summary="Texto libre → servicios del catálogo (JSON validado) + cotización por fórmula")
def diagnosis(body: DiagnosisIn, _: dict = Depends(require_roles(*STAFF))):
    _require_ai()
    services = db.load_services()
    catalog = services[["code", "name", "category", "keywords"]].to_dict("records")
    try:
        result = suggest_services(body.problem, catalog)
    except AIError as e:
        raise _ai_error(e)
    ids = dict(zip(services["code"], services["id"]))
    for s in result["servicios"]:
        s["service_id"] = int(ids[s["codigo"]])
        s["nombre"] = services.set_index("code").loc[s["codigo"], "name"]
    quote = None
    if result["servicios"]:
        quote = quote_json(build(QuoteIn(items=[{"service_id": s["service_id"], "qty": 1}
                                                for s in result["servicios"]])))
    return {**result, "quote": quote}


class SummaryIn(BaseModel):
    start: date | None = None
    end: date | None = None


@router.post("/summary", summary="Resumen ejecutivo a partir de los KPIs ya calculados")
def summary(body: SummaryIn, _: dict = Depends(require_roles(ADMIN))):
    _require_ai()
    all_orders = db.load_orders()
    s, e = parse_range(body.start, body.end, all_orders)
    data = kpis.summary(kpis.filter_by_date(all_orders, s, e), kpis.filter_by_date(db.load_items(), s, e),
                        db.load_bays()["name"].tolist(), s, e)
    try:
        return {"text": executive_summary(data), "kpis": clean(data)}
    except AIError as err:
        raise _ai_error(err)


@router.post("/whatsapp", summary="Mensaje de WhatsApp con la cotización")
def whatsapp(body: QuoteIn, _: dict = Depends(require_roles(*STAFF))):
    _require_ai()
    quote = build(body)
    try:
        text = whatsapp_message(body.customer, body.vehicle, quote.as_dict(), [l.name for l in quote.lines],
                                config.BUSINESS_NAME)
    except AIError as e:
        raise _ai_error(e)
    return {"text": text}
