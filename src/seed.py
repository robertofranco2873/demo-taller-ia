"""Genera ~6 meses de datos FICTICIOS con semilla fija.

Simula la llegada de órdenes (estacionalidad mensual y por día de la semana),
la cola de cada técnico y bahía, tiempos reales según la eficiencia de cada
técnico, esperas por refacciones (retrasos) y algunas anomalías de tiempo.

Uso:  python -m src.seed   (borra y regenera data/taller.db)
"""
import math
import random
from datetime import datetime, timedelta
from pathlib import Path

from src import config
from src.quote import Quote, QuoteLine
from src.time_study import standard_hours
from src.workcalendar import add_work_hours, add_workdays, is_workday

SEED = 42
DAYS_OF_HISTORY = 182

# (código, nombre, precio MXN)
PARTS = [
    ("R01", "Aceite sintético 5W-30 (litro)", 180), ("R02", "Filtro de aceite", 160),
    ("R03", "Filtro de aire de motor", 280), ("R04", "Bujía de iridio", 220),
    ("R05", "Filtro de gasolina", 350), ("R06", "Juego de balatas delanteras", 950),
    ("R07", "Juego de balatas traseras", 850), ("R08", "Disco de freno delantero", 1100),
    ("R09", "Líquido de frenos DOT4 (litro)", 210), ("R10", "Amortiguador delantero", 1450),
    ("R11", "Amortiguador trasero", 1150), ("R12", "Kit de clutch", 4800),
    ("R13", "Kit de distribución (banda y tensor)", 3200), ("R14", "Carga de gas refrigerante R-134a", 650),
    ("R15", "Batería 12 V 60 Ah", 2600), ("R16", "Bomba de agua", 1800),
    ("R17", "Anticongelante (litro)", 140), ("R18", "Limpiador de inyectores", 320),
    ("R19", "Radiador", 3900), ("R20", "Rótula / terminal de dirección", 620),
    ("R21", "Kit de bujes de suspensión", 1400), ("R22", "Aceite ATF (litro)", 230),
    ("R23", "Filtro de transmisión", 520), ("R24", "Kit de juntas de motor", 3500),
    ("R25", "Juego de anillos y metales", 4200), ("R26", "Alternador reconstruido", 3800),
    ("R27", "Motor de arranque reconstruido", 3300), ("R28", "Filtro de aire de cabina", 300),
    ("R29", "Fusibles y terminales eléctricas", 150), ("R30", "Plomos de balanceo", 80),
]

# (código, nombre, categoría, min observados, factor calificación, suplementos,
#  palabras clave, [(refacción, cantidad)], peso de demanda)
SERVICES = [
    ("S01", "Cambio de aceite y filtro", "Mantenimiento", 35, 1.05, 0.15,
     "aceite, servicio, kilometraje, testigo de aceite", [("R01", 4), ("R02", 1)], 18),
    ("S02", "Afinación mayor", "Mantenimiento", 150, 1.00, 0.15,
     "afinación, tironea, consume gasolina, falla en marcha, bujías",
     [("R01", 4), ("R02", 1), ("R03", 1), ("R04", 4), ("R05", 1)], 10),
    ("S03", "Cambio de balatas delanteras", "Frenos", 75, 1.05, 0.15,
     "ruido al frenar, rechina, chilla, frenos delanteros", [("R06", 1)], 11),
    ("S04", "Cambio de balatas traseras", "Frenos", 85, 1.00, 0.15,
     "ruido atrás al frenar, freno de mano, frenos traseros", [("R07", 1)], 6),
    ("S05", "Rectificado de discos", "Frenos", 60, 1.00, 0.12,
     "vibra al frenar, pedal vibra, disco rayado", [], 6),
    ("S06", "Cambio de discos delanteros", "Frenos", 90, 1.00, 0.15,
     "disco desgastado, vibración fuerte al frenar", [("R08", 2)], 3),
    ("S07", "Purga y cambio de líquido de frenos", "Frenos", 40, 1.00, 0.15,
     "pedal esponjoso, pedal se va al fondo, líquido de frenos", [("R09", 1)], 5),
    ("S08", "Alineación y balanceo", "Suspensión", 50, 1.05, 0.12,
     "se jala, volante chueco, vibra en carretera, desgaste de llantas", [("R30", 1)], 12),
    ("S09", "Cambio de amortiguadores delanteros", "Suspensión", 120, 1.00, 0.18,
     "rebota, golpe en baches, inestable, amortiguadores", [("R10", 2)], 4),
    ("S10", "Cambio de amortiguadores traseros", "Suspensión", 90, 1.00, 0.18,
     "rebota atrás, se hunde la parte trasera", [("R11", 2)], 3),
    ("S11", "Cambio de rótulas y terminales", "Suspensión", 100, 1.00, 0.18,
     "juego en el volante, golpeteo en la dirección", [("R20", 2)], 4),
    ("S12", "Cambio de bujes de suspensión", "Suspensión", 160, 0.95, 0.18,
     "rechinido de suspensión, golpe al pasar topes", [("R21", 1)], 3),
    ("S13", "Cambio de clutch", "Transmisión", 300, 1.00, 0.20,
     "patina, no entran velocidades, pedal de clutch duro, olor a quemado", [("R12", 1)], 3),
    ("S14", "Servicio de transmisión automática", "Transmisión", 90, 1.00, 0.15,
     "cambios bruscos, tarda en cambiar, transmisión", [("R22", 6), ("R23", 1)], 3),
    ("S15", "Cambio de kit de distribución", "Motor", 240, 1.00, 0.20,
     "banda de distribución, 100 mil km, ruido de banda", [("R13", 1)], 3),
    ("S16", "Ajuste de motor", "Motor", 900, 1.00, 0.20,
     "humo azul, consume aceite, pérdida de compresión, motor desvielado",
     [("R24", 1), ("R25", 1), ("R01", 4), ("R02", 1)], 1),
    ("S17", "Cambio de bomba de agua", "Enfriamiento", 180, 1.00, 0.18,
     "fuga de anticongelante, se calienta, charco verde", [("R16", 1), ("R17", 4)], 3),
    ("S18", "Cambio de radiador", "Enfriamiento", 150, 1.00, 0.15,
     "se calienta, radiador roto, fuga en radiador", [("R19", 1), ("R17", 4)], 2),
    ("S19", "Servicio de aire acondicionado", "Confort", 70, 1.00, 0.12,
     "no enfría, aire acondicionado, clima", [("R14", 1)], 5),
    ("S20", "Cambio de filtro de aire de cabina", "Confort", 15, 1.00, 0.10,
     "mal olor en cabina, sale poco aire", [("R28", 1)], 4),
    ("S21", "Diagnóstico por escáner", "Diagnóstico", 30, 1.00, 0.10,
     "check engine, testigo encendido, falla desconocida", [], 10),
    ("S22", "Revisión del sistema eléctrico", "Eléctrico", 60, 1.05, 0.15,
     "luces no prenden, fusibles, falla eléctrica", [("R29", 1)], 4),
    ("S23", "Cambio de batería", "Eléctrico", 20, 1.00, 0.10,
     "no arranca, batería descargada, se descarga", [("R15", 1)], 6),
    ("S24", "Cambio de alternador", "Eléctrico", 90, 1.00, 0.15,
     "testigo de batería, la batería no carga", [("R26", 1)], 2),
    ("S25", "Cambio de motor de arranque", "Eléctrico", 80, 1.00, 0.15,
     "no da marcha, hace clic al arrancar", [("R27", 1)], 2),
    ("S26", "Lavado de inyectores", "Motor", 90, 1.00, 0.15,
     "jaloneo, alto consumo de gasolina, ralentí inestable", [("R18", 1)], 5),
]

# (nombre ficticio, especialidad, eficiencia real, peso de asignación)
TECHNICIANS = [
    ("Técnico A · Carlos (ficticio)", "Motor y transmisión", 1.12, 0.32),
    ("Técnico B · Lucía (ficticia)", "Frenos y suspensión", 1.00, 0.27),
    ("Técnico C · Miguel (ficticio)", "Eléctrico y diagnóstico", 0.93, 0.23),
    ("Técnico D · Sofía (ficticia)", "Mantenimiento general", 0.82, 0.18),
]
BAYS = ["Bahía 1 · Elevador", "Bahía 2 · Elevador", "Bahía 3 · Alineación"]

MONTH_FACTOR = {1: 0.80, 2: 0.85, 3: 0.95, 4: 0.95, 5: 1.00, 6: 0.90,
                7: 1.20, 8: 1.05, 9: 0.85, 10: 1.00, 11: 1.00, 12: 1.25}
WEEKDAY_FACTOR = {0: 1.30, 1: 1.00, 2: 0.95, 3: 0.95, 4: 1.10, 5: 0.70}
BASE_ORDERS_PER_DAY = 2.35
RECENT_BOOST_DAYS = 8      # pico de demanda reciente para tener backlog
RECENT_BOOST = 2.2
RECENT_WAIT_PROB = 0.40    # órdenes recientes esperando autorización o refacciones
RECENT_TECH_WEIGHTS = [0.45, 0.25, 0.18, 0.12]  # el técnico A concentra la carga reciente

FIRST_NAMES = ["Ana", "Luis", "María", "José", "Laura", "Jorge", "Elena", "Raúl", "Paola", "Diego",
               "Karla", "Héctor", "Fernanda", "Iván", "Gabriela", "Óscar", "Mónica", "Rodrigo"]
LAST_NAMES = ["García", "López", "Martínez", "Hernández", "Ramírez", "Torres", "Flores", "Rivera",
              "Gómez", "Díaz", "Cruz", "Morales", "Reyes", "Ortiz", "Vargas", "Castillo"]
VEHICLES = ["Nissan Versa", "Chevrolet Aveo", "VW Jetta", "Nissan March", "Toyota Corolla",
            "Honda Civic", "Mazda 3", "Kia Rio", "VW Vento", "Nissan NP300", "Ford Ranger",
            "Toyota Hilux", "Chevrolet Spark", "Hyundai Accent", "Seat Ibiza"]


def _poisson(rng: random.Random, lam: float) -> int:
    limit, k, p = math.exp(-lam), 0, 1.0
    while True:
        p *= rng.random()
        if p <= limit:
            return k
        k += 1


def generate(now: datetime, seed: int = SEED) -> dict:
    """Genera todas las filas en memoria. Determinista para (now, seed)."""
    rng = random.Random(seed)
    part_price = {code: price for code, _, price in PARTS}
    catalog = []
    for code, name, cat, obs, rf, allow, kw, parts, weight in SERVICES:
        catalog.append({"code": code, "name": name, "category": cat, "weight": weight,
                        "std_hours": standard_hours(obs, rf, allow),
                        "parts_cost": sum(part_price[p] * q for p, q in parts)})
    weights = [s["weight"] for s in catalog]
    tech_weights = [t[3] for t in TECHNICIANS]

    start_day = (now - timedelta(days=DAYS_OF_HISTORY)).date()
    tech_free = [datetime.combine(start_day, datetime.min.time())] * len(TECHNICIANS)
    bay_free = [datetime.combine(start_day, datetime.min.time())] * len(BAYS)
    orders, items = [], []

    day = start_day
    while day <= now.date():
        if not is_workday(day):
            day += timedelta(days=1)
            continue
        lam = BASE_ORDERS_PER_DAY * MONTH_FACTOR[day.month] * WEEKDAY_FACTOR[day.weekday()]
        if (now.date() - day).days <= RECENT_BOOST_DAYS:
            lam *= RECENT_BOOST
        arrivals = sorted(rng.uniform(0, 7.5) for _ in range(_poisson(rng, lam)))
        for offset in arrivals:
            created = (datetime.combine(day, datetime.min.time()) + timedelta(
                hours=config.WORKDAY_START_HOUR + offset)).replace(microsecond=0)
            if created > now:
                continue
            # Servicios: uno principal y, a veces, uno o dos adicionales.
            n_services = 1 + (rng.random() < 0.35) + (rng.random() < 0.10)
            chosen = []
            while len(chosen) < n_services:
                s = rng.choices(catalog, weights=weights)[0]
                if s not in chosen:
                    chosen.append(s)
            recent = (now.date() - day).days <= RECENT_BOOST_DAYS
            heavy = any(s["category"] in ("Motor", "Transmisión") for s in chosen)
            t_weights = RECENT_TECH_WEIGHTS if recent else tech_weights
            t = 0 if heavy and rng.random() < 0.6 else rng.choices(range(len(TECHNICIANS)), t_weights)[0]
            eff = TECHNICIANS[t][2]

            lines = [QuoteLine(s["code"], s["name"], s["std_hours"], s["parts_cost"], 1) for s in chosen]
            quote = Quote(lines, config.DEFAULT_LABOR_RATE, config.DEFAULT_MARGIN_PCT)

            wait_prob = RECENT_WAIT_PROB if recent else 0.08
            wait_parts = rng.randint(1, 4) * config.HOURS_PER_DAY if rng.random() < wait_prob else 0.0
            ready = add_work_hours(created, rng.uniform(0.25, 1.5) + wait_parts)
            b = min(range(len(BAYS)), key=lambda i: bay_free[i])
            start = add_work_hours(max(ready, tech_free[t], bay_free[b]), 0)
            actuals = []
            for line in lines:
                factor = rng.lognormvariate(0, 0.12)
                if rng.random() < 0.03:  # retrabajo / anomalía
                    factor *= rng.uniform(1.6, 2.2)
                actuals.append(round(line.hours / eff * factor, 2))
            finish = add_work_hours(start, sum(actuals))
            delivered = add_work_hours(finish, rng.uniform(0.5, 10))
            tech_free[t], bay_free[b] = finish, finish

            # La promesa al cliente incluye la espera por refacciones; los retrasos salen de la cola.
            promise_days = math.ceil(quote.hours / 6) + int(wait_parts // config.HOURS_PER_DAY) + rng.choice([0, 1, 1, 2])
            due = add_workdays(created.date(), promise_days)

            if start > now:
                status, started, finished, deliv = "recibida", None, None, None
            elif finish > now:
                status, started, finished, deliv = "en proceso", start, None, None
            elif delivered > now:
                status, started, finished, deliv = "terminada", start, finish, None
            else:
                status, started, finished, deliv = "entregada", start, finish, delivered
            done = finished is not None

            order_id = len(orders) + 1
            orders.append({
                "id": order_id, "folio": f"OT-{order_id:05d}",
                "customer": f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)} (ficticio)",
                "phone": f"+52 55 0000 {rng.randint(0, 9999):04d}",
                "vehicle": f"{rng.choice(VEHICLES)} {rng.randint(2010, 2024)}",
                "created_at": created, "due_date": due, "scheduled_date": start.date(),
                "started_at": started, "finished_at": finished, "delivered_at": deliv,
                "status": status, "technician_id": t + 1, "bay_id": b + 1,
                "labor_rate": quote.labor_rate, "margin_pct": quote.margin_pct,
                "std_hours": quote.hours, "labor": quote.labor, "parts": quote.parts,
                "subtotal": quote.subtotal, "iva": quote.iva, "total": quote.total,
            })
            for s, line, actual in zip(chosen, lines, actuals):
                items.append({"order_id": order_id, "service_code": s["code"], "qty": 1,
                              "std_hours": line.hours, "parts_cost": line.parts(),
                              "line_subtotal": quote.line_subtotal(line),
                              "actual_hours": actual if done else None})
        day += timedelta(days=1)
    return {"orders": orders, "items": items}


def _iso(value):
    if value is None:
        return None
    return value.isoformat(timespec="seconds") if isinstance(value, datetime) else value.isoformat()


def seed_database(db_path: Path | None = None, now: datetime | None = None, seed: int = SEED) -> dict:
    """Borra la base (si existe) y la llena con catálogo y órdenes ficticias."""
    from src import db

    path = Path(db_path or config.DB_PATH)
    if path.exists():
        path.unlink()
    db.init_schema(path)
    data = generate(now or datetime.now().replace(microsecond=0), seed)
    with db.connect(path) as conn:
        conn.executemany("INSERT INTO settings(key, value) VALUES (?, ?)",
                         [("labor_rate", str(config.DEFAULT_LABOR_RATE)),
                          ("margin_pct", str(config.DEFAULT_MARGIN_PCT))])
        conn.executemany("INSERT INTO technicians(id, name, specialty) VALUES (?, ?, ?)",
                         [(i + 1, n, s) for i, (n, s, _, _) in enumerate(TECHNICIANS)])
        conn.executemany("INSERT INTO bays(id, name) VALUES (?, ?)",
                         [(i + 1, n) for i, n in enumerate(BAYS)])
        conn.executemany("INSERT INTO parts(code, name, price) VALUES (?, ?, ?)", PARTS)
        part_id = {code: pid for pid, code in conn.execute("SELECT id, code FROM parts")}
        for code, name, cat, obs, rf, allow, kw, parts, _ in SERVICES:
            cur = conn.execute(
                """INSERT INTO services(code, name, category, observed_avg_min, rating_factor,
                   allowance_pct, keywords) VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (code, name, cat, obs, rf, allow, kw))
            conn.executemany("INSERT INTO service_parts(service_id, part_id, qty) VALUES (?, ?, ?)",
                             [(cur.lastrowid, part_id[p], q) for p, q in parts])
        service_id = {code: sid for sid, code in conn.execute("SELECT id, code FROM services")}
        cols = ["id", "folio", "customer", "phone", "vehicle", "created_at", "due_date",
                "scheduled_date", "started_at", "finished_at", "delivered_at", "status",
                "technician_id", "bay_id", "labor_rate", "margin_pct", "std_hours", "labor",
                "parts", "subtotal", "iva", "total"]
        conn.executemany(
            f"INSERT INTO orders({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})",
            [tuple(_iso(o[c]) if c in ("created_at", "due_date", "scheduled_date", "started_at",
                                       "finished_at", "delivered_at") else o[c] for c in cols)
             for o in data["orders"]])
        conn.executemany(
            """INSERT INTO order_items(order_id, service_id, qty, std_hours, parts_cost,
               line_subtotal, actual_hours) VALUES (?, ?, ?, ?, ?, ?, ?)""",
            [(i["order_id"], service_id[i["service_code"]], i["qty"], i["std_hours"],
              i["parts_cost"], i["line_subtotal"], i["actual_hours"]) for i in data["items"]])
    return {"orders": len(data["orders"]), "items": len(data["items"])}


if __name__ == "__main__":
    result = seed_database()
    print(f"Base creada en {config.DB_PATH}: {result['orders']} órdenes, {result['items']} servicios.")
