"""Secuenciación de órdenes pendientes con reglas de prioridad FIFO, SPT y EDD.

Todas las órdenes están disponibles en t = 0 (ya están en el taller).
Con m recursos en paralelo, cada orden de la secuencia se asigna al recurso
que se libera primero (programación por lista).

Tiempo de flujo F_j = C_j (fin de la orden).  Retraso T_j = max(0, C_j − d_j).
"""
from dataclasses import dataclass

import pandas as pd

RULES = {
    "FIFO": "Primero en llegar, primero en atenderse",
    "SPT": "Menor tiempo de proceso primero",
    "EDD": "Fecha de entrega más próxima primero",
}
MANUAL = "MANUAL"
MANUAL_LABEL = "Prioridad asignada por el usuario"


@dataclass
class Job:
    id: str
    processing: float  # horas
    due: float         # horas laborables desde ahora hasta la fecha compromiso
    arrival: float = 0.0  # para FIFO (p. ej. timestamp de recepción)
    technician: str | None = None  # técnico asignado actualmente (opcional)
    priority: float | None = None  # prioridad manual (1 = primero); None = al final
    pinned: bool = False  # técnico fijado por el usuario: se respeta aunque la asignación sea libre


def sequence(jobs: list[Job], rule: str) -> list[Job]:
    """Ordena las órdenes según la regla (desempate estable por llegada).

    MANUAL: por la prioridad asignada; las órdenes sin prioridad van al final, por llegada.
    """
    if rule == "FIFO":
        key = lambda j: (j.arrival, j.id)
    elif rule == "SPT":
        key = lambda j: (j.processing, j.arrival, j.id)
    elif rule == "EDD":
        key = lambda j: (j.due, j.arrival, j.id)
    elif rule == MANUAL:
        key = lambda j: (j.priority is None, j.priority if j.priority is not None else 0, j.arrival, j.id)
    else:
        raise ValueError(f"Regla desconocida: {rule}")
    return sorted(jobs, key=key)


def schedule(jobs: list[Job], rule: str, machines: int = 1,
             machine_names: list[str] | None = None) -> pd.DataFrame:
    """Programa la secuencia y calcula inicio, fin, flujo y retraso de cada orden."""
    if machines < 1:
        raise ValueError("Se requiere al menos un recurso.")
    names = machine_names or [f"Recurso {i + 1}" for i in range(machines)]
    free = [0.0] * machines
    rows = []
    for pos, job in enumerate(sequence(jobs, rule), start=1):
        m = min(range(machines), key=lambda i: (free[i], i))
        start = free[m]
        end = start + job.processing
        free[m] = end
        tardiness = max(0.0, end - job.due)
        rows.append({"posicion": pos, "orden": job.id, "recurso": names[m],
                     "proceso_h": job.processing, "entrega_h": job.due,
                     "inicio_h": start, "fin_h": end, "flujo_h": end,
                     "retraso_h": tardiness, "tarde": tardiness > 1e-9})
    return pd.DataFrame(rows)


def metrics(schedule_df: pd.DataFrame) -> dict:
    if schedule_df.empty:
        return {"flujo_promedio_h": 0.0, "retraso_promedio_h": 0.0, "ordenes_tarde": 0, "makespan_h": 0.0}
    return {
        "flujo_promedio_h": float(schedule_df["flujo_h"].mean()),
        "retraso_promedio_h": float(schedule_df["retraso_h"].mean()),
        "ordenes_tarde": int(schedule_df["tarde"].sum()),
        "makespan_h": float(schedule_df["fin_h"].max()),
    }


def compare_rules(jobs: list[Job], machines: int = 1,
                  machine_names: list[str] | None = None) -> pd.DataFrame:
    """Tabla comparativa de las tres reglas."""
    rows = []
    for rule in RULES:
        m = metrics(schedule(jobs, rule, machines, machine_names))
        rows.append({"regla": rule, **m})
    return pd.DataFrame(rows)


def schedule_resources(jobs: list[Job], rule: str, technicians: list[str], bays: list[str],
                       respect_assignment: bool = True) -> pd.DataFrame:
    """Programa con dos recursos por orden: un técnico y una bahía.

    Si respect_assignment es True, cada orden va con su técnico asignado (si existe en la lista);
    si no, con el técnico que se libera primero. La bahía es siempre la que se libera primero.
    Inicio = máx(técnico libre, bahía libre).
    """
    if not technicians or not bays:
        raise ValueError("Se requiere al menos un técnico y una bahía.")
    tech_free = {t: 0.0 for t in technicians}
    bay_free = {b: 0.0 for b in bays}
    rows = []
    for pos, job in enumerate(sequence(jobs, rule), start=1):
        if (respect_assignment or job.pinned) and job.technician in tech_free:
            tech = job.technician
        else:
            tech = min(technicians, key=lambda t: (tech_free[t], technicians.index(t)))
        bay = min(bays, key=lambda b: (bay_free[b], bays.index(b)))
        start = max(tech_free[tech], bay_free[bay])
        end = start + job.processing
        tech_free[tech] = bay_free[bay] = end
        tardiness = max(0.0, end - job.due)
        rows.append({"posicion": pos, "orden": job.id, "recurso": tech, "bahia": bay,
                     "proceso_h": job.processing, "entrega_h": job.due, "inicio_h": start,
                     "fin_h": end, "flujo_h": end, "retraso_h": tardiness, "tarde": tardiness > 1e-9})
    return pd.DataFrame(rows)


def compare_rules_resources(jobs: list[Job], technicians: list[str], bays: list[str],
                            respect_assignment: bool = True, include_manual: bool = False) -> pd.DataFrame:
    rows = []
    for rule in [*RULES, *([MANUAL] if include_manual else [])]:
        m = metrics(schedule_resources(jobs, rule, technicians, bays, respect_assignment))
        rows.append({"regla": rule, **m})
    return pd.DataFrame(rows)
