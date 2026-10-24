"""Exportación de la cotización a Excel (openpyxl)."""
from datetime import datetime
from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill

from src.config import BUSINESS_NAME, DEMO_NOTICE
from src.quote import Quote

MONEY = '"$"#,##0.00'


def quote_to_excel(quote: Quote, customer: str = "", vehicle: str = "",
                   when: datetime | None = None) -> bytes:
    when = when or datetime.now()
    wb = Workbook()
    ws = wb.active
    ws.title = "Cotización"
    ws["A1"] = f"{BUSINESS_NAME} — Cotización"
    ws["A1"].font = Font(size=14, bold=True)
    ws["A2"] = DEMO_NOTICE
    ws["A2"].font = Font(italic=True, color="C00000")
    ws["A4"], ws["B4"] = "Fecha", when.strftime("%Y-%m-%d %H:%M")
    ws["A5"], ws["B5"] = "Cliente", customer or "—"
    ws["A6"], ws["B6"] = "Vehículo", vehicle or "—"
    ws["A7"], ws["B7"] = "Tarifa por hora", quote.labor_rate
    ws["B7"].number_format = MONEY
    ws["A8"], ws["B8"] = "Margen", quote.margin_pct
    ws["B8"].number_format = "0.0%"

    header = ["Código", "Servicio", "Cantidad", "Horas estándar", "Mano de obra", "Refacciones", "Importe (con margen)"]
    ws.append([])
    ws.append(header)
    head_row = ws.max_row
    for cell in ws[head_row]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="1F4E78")
        cell.alignment = Alignment(horizontal="center")
    for line in quote.lines:
        ws.append([line.code, line.name, line.qty, round(line.hours, 2),
                   round(line.labor(quote.labor_rate), 2), round(line.parts(), 2),
                   quote.line_subtotal(line)])
        for col in "EFG":
            ws[f"{col}{ws.max_row}"].number_format = MONEY

    ws.append([])
    for label, value in [("Mano de obra", quote.labor), ("Refacciones", quote.parts),
                         ("Margen", quote.margin), ("Subtotal", quote.subtotal),
                         (f"IVA {quote.iva_rate:.0%}", quote.iva), ("TOTAL", quote.total)]:
        ws.append(["", "", "", "", "", label, value])
        ws[f"G{ws.max_row}"].number_format = MONEY
        if label == "TOTAL":
            ws[f"F{ws.max_row}"].font = ws[f"G{ws.max_row}"].font = Font(bold=True)
    ws.append([])
    ws.append(["Fórmula: horas estándar × tarifa + refacciones; + margen; + IVA. Vigencia: 7 días."])

    for col, width in zip("ABCDEFG", [10, 38, 10, 15, 15, 15, 20]):
        ws.column_dimensions[col].width = width
    buffer = BytesIO()
    wb.save(buffer)
    return buffer.getvalue()
