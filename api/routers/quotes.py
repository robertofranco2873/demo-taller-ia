from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field

from api.core import STAFF, bad_request, require_roles
from src import db
from src.export import quote_to_excel, quote_to_pdf
from src.quote import Quote

router = APIRouter(prefix="/api/quotes", tags=["Cotizador"])


class QuoteItem(BaseModel):
    service_id: int
    qty: int = Field(1, ge=1, le=20)


class QuoteIn(BaseModel):
    items: list[QuoteItem] = Field(min_length=1)
    labor_rate: float | None = Field(None, ge=0)
    margin_pct: float | None = Field(None, ge=0, le=3)
    customer: str = ""
    vehicle: str = ""


def build(body: QuoteIn) -> Quote:
    settings = db.get_settings()
    qty: dict[int, int] = {}
    for item in body.items:
        qty[item.service_id] = qty.get(item.service_id, 0) + item.qty
    try:
        quote, _ = db.build_quote(qty, body.labor_rate if body.labor_rate is not None else settings["labor_rate"],
                                  body.margin_pct if body.margin_pct is not None else settings["margin_pct"])
    except KeyError:
        raise HTTPException(404, "Uno de los servicios no existe.")
    except ValueError as e:
        raise bad_request(e)
    return quote


def quote_json(quote: Quote) -> dict:
    return {
        **quote.as_dict(), "labor_rate": quote.labor_rate, "margin_pct": quote.margin_pct,
        "iva_rate": quote.iva_rate,
        "lines": [{"code": l.code, "name": l.name, "qty": l.qty, "std_hours": l.hours,
                   "labor": round(l.labor(quote.labor_rate), 2), "parts": round(l.parts(), 2),
                   "subtotal": quote.line_subtotal(l)} for l in quote.lines],
        "formula": "Total = [(horas estándar × tarifa) + refacciones] × (1 + margen) × (1 + IVA)",
    }


@router.post("", summary="Cotizar por fórmula")
def quote(body: QuoteIn, _: dict = Depends(require_roles(*STAFF))):
    return quote_json(build(body))


@router.post("/excel", summary="Cotización en Excel", response_class=Response)
def quote_excel(body: QuoteIn, _: dict = Depends(require_roles(*STAFF))):
    data = quote_to_excel(build(body), body.customer, body.vehicle)
    return Response(data, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": f'attachment; filename="cotizacion_{date.today():%Y%m%d}.xlsx"'})


@router.post("/pdf", summary="Cotización en PDF", response_class=Response)
def quote_pdf(body: QuoteIn, _: dict = Depends(require_roles(*STAFF))):
    data = quote_to_pdf(build(body), body.customer, body.vehicle)
    return Response(data, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="cotizacion_{date.today():%Y%m%d}.pdf"'})
