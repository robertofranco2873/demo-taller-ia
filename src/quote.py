"""Cotizador por fórmula.

mano de obra = Σ horas estándar × cantidad × tarifa
refacciones  = Σ precio refacción × cantidad
base         = mano de obra + refacciones
margen       = base × % margen
subtotal     = base + margen
IVA          = subtotal × 16 %
total        = subtotal + IVA
"""
from dataclasses import dataclass, field

from src.config import IVA_RATE


@dataclass
class QuoteLine:
    code: str
    name: str
    std_hours: float
    parts_cost: float  # costo de refacciones por unidad de servicio
    qty: int = 1

    @property
    def hours(self) -> float:
        return self.std_hours * self.qty

    def labor(self, rate: float) -> float:
        return self.hours * rate

    def parts(self) -> float:
        return self.parts_cost * self.qty


@dataclass
class Quote:
    lines: list[QuoteLine]
    labor_rate: float
    margin_pct: float
    iva_rate: float = IVA_RATE
    labor: float = field(init=False)
    parts: float = field(init=False)
    base: float = field(init=False)
    margin: float = field(init=False)
    subtotal: float = field(init=False)
    iva: float = field(init=False)
    total: float = field(init=False)
    hours: float = field(init=False)

    def __post_init__(self):
        if self.labor_rate < 0:
            raise ValueError("La tarifa no puede ser negativa.")
        if self.margin_pct < 0:
            raise ValueError("El margen no puede ser negativo.")
        if any(line.qty <= 0 for line in self.lines):
            raise ValueError("Las cantidades deben ser mayores a cero.")
        self.hours = sum(line.hours for line in self.lines)
        self.labor = round(sum(line.labor(self.labor_rate) for line in self.lines), 2)
        self.parts = round(sum(line.parts() for line in self.lines), 2)
        self.base = round(self.labor + self.parts, 2)
        self.margin = round(self.base * self.margin_pct, 2)
        self.subtotal = round(self.base + self.margin, 2)
        self.iva = round(self.subtotal * self.iva_rate, 2)
        self.total = round(self.subtotal + self.iva, 2)

    def line_subtotal(self, line: QuoteLine) -> float:
        """Importe antes de IVA de una línea (incluye su parte proporcional del margen)."""
        return round((line.labor(self.labor_rate) + line.parts()) * (1 + self.margin_pct), 2)

    def as_dict(self) -> dict:
        return {
            "horas_estandar": round(self.hours, 2),
            "mano_de_obra": self.labor,
            "refacciones": self.parts,
            "margen": self.margin,
            "subtotal": self.subtotal,
            "iva": self.iva,
            "total": self.total,
        }
