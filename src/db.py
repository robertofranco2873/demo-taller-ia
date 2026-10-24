"""Acceso a SQLite. La base se crea y se llena con datos ficticios si no existe."""
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime
from pathlib import Path

import pandas as pd

from src import config
from src.orders import STATUS_TIMESTAMP, validate_transition
from src.quote import Quote, QuoteLine
from src.time_study import normal_time, standard_time

SCHEMA = """
CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS technicians (
    id INTEGER PRIMARY KEY, name TEXT NOT NULL, specialty TEXT);
CREATE TABLE IF NOT EXISTS bays (id INTEGER PRIMARY KEY, name TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS parts (
    id INTEGER PRIMARY KEY, code TEXT UNIQUE NOT NULL, name TEXT NOT NULL, price REAL NOT NULL,
    stock REAL NOT NULL DEFAULT 0, lead_time_days REAL NOT NULL DEFAULT 3);
CREATE TABLE IF NOT EXISTS services (
    id INTEGER PRIMARY KEY, code TEXT UNIQUE NOT NULL, name TEXT NOT NULL, category TEXT,
    observed_avg_min REAL NOT NULL, rating_factor REAL NOT NULL, allowance_pct REAL NOT NULL,
    keywords TEXT DEFAULT '', steps TEXT DEFAULT '');
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY, username TEXT UNIQUE NOT NULL, name TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('admin', 'recepcion', 'tecnico')),
    password_hash TEXT NOT NULL, technician_id INTEGER REFERENCES technicians(id),
    active INTEGER NOT NULL DEFAULT 1);
CREATE TABLE IF NOT EXISTS time_logs (
    id INTEGER PRIMARY KEY, order_id INTEGER NOT NULL REFERENCES orders(id),
    started_at TEXT NOT NULL, ended_at TEXT);
CREATE TABLE IF NOT EXISTS inventory_movements (
    id INTEGER PRIMARY KEY, part_id INTEGER NOT NULL REFERENCES parts(id), created_at TEXT NOT NULL,
    qty REAL NOT NULL, kind TEXT NOT NULL, order_id INTEGER REFERENCES orders(id), note TEXT DEFAULT '');
CREATE TABLE IF NOT EXISTS service_parts (
    service_id INTEGER NOT NULL REFERENCES services(id),
    part_id INTEGER NOT NULL REFERENCES parts(id),
    qty REAL NOT NULL, PRIMARY KEY (service_id, part_id));
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY, folio TEXT UNIQUE NOT NULL, customer TEXT NOT NULL, phone TEXT,
    vehicle TEXT, created_at TEXT NOT NULL, due_date TEXT NOT NULL, scheduled_date TEXT NOT NULL,
    started_at TEXT, finished_at TEXT, delivered_at TEXT, status TEXT NOT NULL,
    technician_id INTEGER REFERENCES technicians(id), bay_id INTEGER REFERENCES bays(id),
    labor_rate REAL NOT NULL, margin_pct REAL NOT NULL, std_hours REAL NOT NULL,
    labor REAL NOT NULL, parts REAL NOT NULL, subtotal REAL NOT NULL, iva REAL NOT NULL,
    total REAL NOT NULL, notes TEXT DEFAULT '');
CREATE TABLE IF NOT EXISTS order_items (
    id INTEGER PRIMARY KEY, order_id INTEGER NOT NULL REFERENCES orders(id),
    service_id INTEGER NOT NULL REFERENCES services(id), qty INTEGER NOT NULL,
    std_hours REAL NOT NULL, parts_cost REAL NOT NULL, line_subtotal REAL NOT NULL,
    actual_hours REAL);
CREATE INDEX IF NOT EXISTS idx_items_order ON order_items(order_id);
CREATE INDEX IF NOT EXISTS idx_logs_order ON time_logs(order_id);
CREATE INDEX IF NOT EXISTS idx_mov_part ON inventory_movements(part_id);
"""
SCHEMA_VERSION = "2"


def _path(db_path: Path | None) -> Path:
    return Path(db_path or config.DB_PATH)


@contextmanager
def connect(db_path: Path | None = None):
    path = _path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_schema(db_path: Path | None = None) -> None:
    with connect(db_path) as conn:
        conn.executescript(SCHEMA)


def is_empty(db_path: Path | None = None) -> bool:
    """True si no hay base, está vacía o es de una versión de esquema anterior."""
    if not _path(db_path).exists():
        return True
    with connect(db_path) as conn:
        try:
            version = conn.execute("SELECT value FROM settings WHERE key='schema_version'").fetchone()
            if version is None or version[0] != SCHEMA_VERSION:
                return True
            return conn.execute("SELECT COUNT(*) FROM services").fetchone()[0] == 0
        except sqlite3.OperationalError:
            return True


def ensure_database(db_path: Path | None = None) -> bool:
    """Crea y siembra la base si no existe (o es de la V1). Regresa True si la creó."""
    if not is_empty(db_path):
        return False
    from src.seed import seed_database
    seed_database(db_path)
    return True


# ---------- configuración ----------

def get_settings(db_path: Path | None = None) -> dict:
    with connect(db_path) as conn:
        rows = dict(conn.execute("SELECT key, value FROM settings").fetchall())
    return {
        "labor_rate": float(rows.get("labor_rate", config.DEFAULT_LABOR_RATE)),
        "margin_pct": float(rows.get("margin_pct", config.DEFAULT_MARGIN_PCT)),
        "efficiency_goal": float(rows.get("efficiency_goal", config.DEFAULT_EFFICIENCY_GOAL)),
        "service_level": float(rows.get("service_level", config.DEFAULT_SERVICE_LEVEL)),
    }


def save_settings(labor_rate: float, margin_pct: float, efficiency_goal: float | None = None,
                  service_level: float | None = None, db_path: Path | None = None) -> None:
    if labor_rate < 0 or margin_pct < 0:
        raise ValueError("Tarifa y margen no pueden ser negativos.")
    values = [("labor_rate", labor_rate), ("margin_pct", margin_pct)]
    if efficiency_goal is not None:
        if not 0.5 <= efficiency_goal <= 1.5:
            raise ValueError("La meta de eficiencia debe estar entre 50 % y 150 %.")
        values.append(("efficiency_goal", efficiency_goal))
    if service_level is not None:
        if not 0.5 <= service_level < 1:
            raise ValueError("El nivel de servicio debe estar entre 50 % y 99.9 %.")
        values.append(("service_level", service_level))
    with connect(db_path) as conn:
        conn.executemany("INSERT OR REPLACE INTO settings(key, value) VALUES (?, ?)",
                         [(k, str(v)) for k, v in values])


# ---------- catálogo ----------

def load_services(db_path: Path | None = None) -> pd.DataFrame:
    """Catálogo con tiempo normal, estándar y costo de refacciones calculados."""
    with connect(db_path) as conn:
        df = pd.read_sql_query(
            """SELECT s.*, COALESCE(SUM(sp.qty * p.price), 0) AS parts_cost
               FROM services s
               LEFT JOIN service_parts sp ON sp.service_id = s.id
               LEFT JOIN parts p ON p.id = sp.part_id
               GROUP BY s.id ORDER BY s.code""", conn)
    df["normal_min"] = [normal_time(o, r) for o, r in zip(df.observed_avg_min, df.rating_factor)]
    df["standard_min"] = [standard_time(n, a) for n, a in zip(df.normal_min, df.allowance_pct)]
    df["std_hours"] = df["standard_min"] / 60
    return df


def load_parts(db_path: Path | None = None) -> pd.DataFrame:
    with connect(db_path) as conn:
        return pd.read_sql_query("SELECT * FROM parts ORDER BY code", conn)


def load_service_parts(service_id: int, db_path: Path | None = None) -> pd.DataFrame:
    with connect(db_path) as conn:
        return pd.read_sql_query(
            """SELECT p.code, p.name, sp.qty, p.price, sp.qty * p.price AS importe
               FROM service_parts sp JOIN parts p ON p.id = sp.part_id
               WHERE sp.service_id = ? ORDER BY p.code""", conn, params=(service_id,))


def update_service(service_id: int, name: str, category: str, observed_avg_min: float,
                   rating_factor: float, allowance_pct: float, db_path: Path | None = None) -> None:
    standard_time(normal_time(observed_avg_min, rating_factor), allowance_pct)  # valida
    with connect(db_path) as conn:
        conn.execute(
            """UPDATE services SET name=?, category=?, observed_avg_min=?, rating_factor=?,
               allowance_pct=? WHERE id=?""",
            (name, category, observed_avg_min, rating_factor, allowance_pct, service_id))


def add_service(code: str, name: str, category: str, observed_avg_min: float,
                rating_factor: float, allowance_pct: float, keywords: str = "",
                db_path: Path | None = None) -> int:
    standard_time(normal_time(observed_avg_min, rating_factor), allowance_pct)
    with connect(db_path) as conn:
        cur = conn.execute(
            """INSERT INTO services(code, name, category, observed_avg_min, rating_factor,
               allowance_pct, keywords) VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (code, name, category, observed_avg_min, rating_factor, allowance_pct, keywords))
        return int(cur.lastrowid)


def update_part_price(part_id: int, price: float, db_path: Path | None = None) -> None:
    if price < 0:
        raise ValueError("El precio no puede ser negativo.")
    with connect(db_path) as conn:
        conn.execute("UPDATE parts SET price=? WHERE id=?", (price, part_id))


def load_technicians(db_path: Path | None = None) -> pd.DataFrame:
    with connect(db_path) as conn:
        return pd.read_sql_query("SELECT * FROM technicians ORDER BY id", conn)


def load_bays(db_path: Path | None = None) -> pd.DataFrame:
    with connect(db_path) as conn:
        return pd.read_sql_query("SELECT * FROM bays ORDER BY id", conn)


# ---------- órdenes ----------

def build_quote(service_qty: dict[int, int], labor_rate: float, margin_pct: float,
                db_path: Path | None = None) -> tuple[Quote, list[int]]:
    """Cotización por fórmula a partir de {service_id: cantidad}."""
    services = load_services(db_path).set_index("id")
    lines, ids = [], []
    for sid, qty in service_qty.items():
        s = services.loc[int(sid)]
        lines.append(QuoteLine(code=s.code, name=s["name"], std_hours=float(s.std_hours),
                               parts_cost=float(s.parts_cost), qty=int(qty)))
        ids.append(int(sid))
    return Quote(lines, labor_rate, margin_pct), ids


def _next_folio(conn) -> str:
    n = conn.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM orders").fetchone()[0]
    return f"OT-{n:05d}"


def create_order(customer: str, phone: str, vehicle: str, service_qty: dict[int, int],
                 technician_id: int, bay_id: int, due_date: date, scheduled_date: date,
                 notes: str = "", created_at: datetime | None = None,
                 db_path: Path | None = None) -> str:
    if not customer.strip():
        raise ValueError("El nombre del cliente es obligatorio.")
    if not service_qty:
        raise ValueError("Agrega al menos un servicio.")
    settings = get_settings(db_path)
    quote, service_ids = build_quote(service_qty, settings["labor_rate"], settings["margin_pct"], db_path)
    created = created_at or datetime.now()
    with connect(db_path) as conn:
        folio = _next_folio(conn)
        cur = conn.execute(
            """INSERT INTO orders(folio, customer, phone, vehicle, created_at, due_date, scheduled_date,
               status, technician_id, bay_id, labor_rate, margin_pct, std_hours, labor, parts,
               subtotal, iva, total, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, 'recibida', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (folio, customer.strip(), phone, vehicle, created.isoformat(timespec="seconds"),
             due_date.isoformat(), scheduled_date.isoformat(), technician_id, bay_id,
             quote.labor_rate, quote.margin_pct, quote.hours, quote.labor, quote.parts,
             quote.subtotal, quote.iva, quote.total, notes))
        order_id = cur.lastrowid
        conn.executemany(
            """INSERT INTO order_items(order_id, service_id, qty, std_hours, parts_cost, line_subtotal)
               VALUES (?, ?, ?, ?, ?, ?)""",
            [(order_id, sid, line.qty, line.hours, line.parts(), quote.line_subtotal(line))
             for sid, line in zip(service_ids, quote.lines)])
    return folio


def update_assignment(order_id: int, technician_id: int, bay_id: int, scheduled_date: date,
                      db_path: Path | None = None) -> None:
    with connect(db_path) as conn:
        conn.execute("UPDATE orders SET technician_id=?, bay_id=?, scheduled_date=? WHERE id=?",
                     (technician_id, bay_id, scheduled_date.isoformat(), order_id))


def advance_order(order_id: int, new_status: str, actual_hours: dict[int, float] | None = None,
                  when: datetime | None = None, db_path: Path | None = None) -> None:
    """Avanza el estado. actual_hours = {item_id: horas reales} (obligatorio al terminar)."""
    when = when or datetime.now()
    with connect(db_path) as conn:
        row = conn.execute("SELECT status FROM orders WHERE id=?", (order_id,)).fetchone()
        if row is None:
            raise ValueError("Orden no encontrada.")
        item_ids = [r[0] for r in conn.execute("SELECT id FROM order_items WHERE order_id=?", (order_id,))]
        hours = [(actual_hours or {}).get(i) for i in item_ids] if new_status == "terminada" else None
        validate_transition(row["status"], new_status, hours)
        col = STATUS_TIMESTAMP[new_status]
        stamp = when.isoformat(timespec="seconds")
        conn.execute(f"UPDATE orders SET status=?, {col}=? WHERE id=?", (new_status, stamp, order_id))
        if new_status == "terminada":
            conn.executemany("UPDATE order_items SET actual_hours=? WHERE id=?",
                             [(actual_hours[i], i) for i in item_ids])
            conn.execute("UPDATE time_logs SET ended_at=? WHERE order_id=? AND ended_at IS NULL",
                         (stamp, order_id))
            _consume_parts(conn, order_id, stamp)


def _consume_parts(conn, order_id: int, stamp: str) -> None:
    """Descuenta del inventario las refacciones de los servicios de la orden."""
    rows = conn.execute(
        """SELECT sp.part_id, SUM(sp.qty * i.qty) FROM order_items i
           JOIN service_parts sp ON sp.service_id = i.service_id
           WHERE i.order_id = ? GROUP BY sp.part_id""", (order_id,)).fetchall()
    for part_id, qty in rows:
        conn.execute("UPDATE parts SET stock = stock - ? WHERE id = ?", (qty, part_id))
        conn.execute("""INSERT INTO inventory_movements(part_id, created_at, qty, kind, order_id)
                        VALUES (?, ?, ?, 'consumo', ?)""", (part_id, stamp, -qty, order_id))


ORDERS_SQL = """
SELECT o.*, t.name AS technician, b.name AS bay,
       (SELECT SUM(actual_hours) FROM order_items i WHERE i.order_id = o.id) AS actual_hours
FROM orders o
LEFT JOIN technicians t ON t.id = o.technician_id
LEFT JOIN bays b ON b.id = o.bay_id
ORDER BY o.created_at
"""

ITEMS_SQL = """
SELECT i.*, s.code AS service_code, s.name AS service_name, s.category,
       o.folio, o.created_at, o.status, o.technician_id, t.name AS technician
FROM order_items i
JOIN orders o ON o.id = i.order_id
JOIN services s ON s.id = i.service_id
LEFT JOIN technicians t ON t.id = o.technician_id
ORDER BY o.created_at, i.id
"""


def load_orders(db_path: Path | None = None) -> pd.DataFrame:
    with connect(db_path) as conn:
        df = pd.read_sql_query(ORDERS_SQL, conn)
    for col in ["created_at", "started_at", "finished_at", "delivered_at"]:
        df[col] = pd.to_datetime(df[col])
    for col in ["due_date", "scheduled_date"]:
        df[col] = pd.to_datetime(df[col]).dt.date
    return df


def load_items(db_path: Path | None = None) -> pd.DataFrame:
    with connect(db_path) as conn:
        df = pd.read_sql_query(ITEMS_SQL, conn)
    df["created_at"] = pd.to_datetime(df["created_at"])
    return df


def get_order(order_id: int, db_path: Path | None = None) -> dict:
    orders = load_orders(db_path)
    match = orders[orders["id"] == order_id]
    if match.empty:
        raise ValueError("Orden no encontrada.")
    items = load_items(db_path)
    return {"order": match.iloc[0].to_dict(), "items": items[items["order_id"] == order_id].to_dict("records")}


# ---------- usuarios ----------

USER_COLS = "u.id, u.username, u.name, u.role, u.technician_id, u.active, t.name AS technician"


def list_users(db_path: Path | None = None) -> list[dict]:
    with connect(db_path) as conn:
        rows = conn.execute(f"""SELECT {USER_COLS} FROM users u
                                LEFT JOIN technicians t ON t.id = u.technician_id ORDER BY u.id""")
        return [dict(r) for r in rows]


def get_user_auth(username: str, db_path: Path | None = None) -> dict | None:
    with connect(db_path) as conn:
        row = conn.execute(f"""SELECT {USER_COLS}, u.password_hash FROM users u
                               LEFT JOIN technicians t ON t.id = u.technician_id
                               WHERE u.username = ?""", (username.strip().lower(),)).fetchone()
        return dict(row) if row else None


def get_user(user_id: int, db_path: Path | None = None) -> dict | None:
    with connect(db_path) as conn:
        row = conn.execute(f"""SELECT {USER_COLS} FROM users u
                               LEFT JOIN technicians t ON t.id = u.technician_id WHERE u.id = ?""",
                           (user_id,)).fetchone()
        return dict(row) if row else None


def _validate_user(role: str, technician_id: int | None) -> None:
    from src.security import ROLES
    if role not in ROLES:
        raise ValueError(f"Rol inválido: {role}")
    if role == "tecnico" and not technician_id:
        raise ValueError("Un usuario técnico debe estar ligado a un técnico.")


def create_user(username: str, name: str, role: str, password_hash: str,
                technician_id: int | None = None, db_path: Path | None = None) -> int:
    _validate_user(role, technician_id)
    if not username.strip():
        raise ValueError("El usuario es obligatorio.")
    with connect(db_path) as conn:
        try:
            cur = conn.execute(
                "INSERT INTO users(username, name, role, password_hash, technician_id) VALUES (?, ?, ?, ?, ?)",
                (username.strip().lower(), name.strip(), role, password_hash,
                 technician_id if role == "tecnico" else None))
        except sqlite3.IntegrityError:
            raise ValueError("Ese nombre de usuario ya existe.")
        return int(cur.lastrowid)


def update_user(user_id: int, name: str, role: str, technician_id: int | None, active: bool,
                password_hash: str | None = None, db_path: Path | None = None) -> None:
    _validate_user(role, technician_id)
    with connect(db_path) as conn:
        conn.execute("UPDATE users SET name=?, role=?, technician_id=?, active=? WHERE id=?",
                     (name.strip(), role, technician_id if role == "tecnico" else None, int(active), user_id))
        if password_hash:
            conn.execute("UPDATE users SET password_hash=? WHERE id=?", (password_hash, user_id))


def delete_user(user_id: int, db_path: Path | None = None) -> None:
    with connect(db_path) as conn:
        conn.execute("DELETE FROM users WHERE id=?", (user_id,))


# ---------- cronómetro del técnico ----------

def timer_state(order_id: int, now: datetime | None = None, db_path: Path | None = None) -> dict:
    """Horas acumuladas en la bitácora y si el cronómetro está corriendo."""
    now = now or datetime.now()
    with connect(db_path) as conn:
        logs = conn.execute("SELECT started_at, ended_at FROM time_logs WHERE order_id=? ORDER BY id",
                            (order_id,)).fetchall()
    total, running_since = 0.0, None
    for start, end in logs:
        s = datetime.fromisoformat(start)
        if end is None:
            running_since = s
            total += (now - s).total_seconds() / 3600
        else:
            total += (datetime.fromisoformat(end) - s).total_seconds() / 3600
    return {"hours": round(total, 4), "running": running_since is not None,
            "running_since": running_since.isoformat(timespec="seconds") if running_since else None}


def start_timer(order_id: int, now: datetime | None = None, db_path: Path | None = None) -> None:
    now = now or datetime.now()
    with connect(db_path) as conn:
        row = conn.execute("SELECT status FROM orders WHERE id=?", (order_id,)).fetchone()
        if row is None:
            raise ValueError("Orden no encontrada.")
        if row["status"] not in config.PENDING_STATUSES:
            raise ValueError("Solo se pueden iniciar órdenes recibidas o en proceso.")
        if conn.execute("SELECT 1 FROM time_logs WHERE order_id=? AND ended_at IS NULL", (order_id,)).fetchone():
            raise ValueError("El cronómetro ya está corriendo.")
        if row["status"] == "recibida":
            conn.execute("UPDATE orders SET status='en proceso', started_at=? WHERE id=?",
                         (now.isoformat(timespec="seconds"), order_id))
        conn.execute("INSERT INTO time_logs(order_id, started_at) VALUES (?, ?)",
                     (order_id, now.isoformat(timespec="seconds")))


def pause_timer(order_id: int, now: datetime | None = None, db_path: Path | None = None) -> None:
    now = now or datetime.now()
    with connect(db_path) as conn:
        cur = conn.execute("UPDATE time_logs SET ended_at=? WHERE order_id=? AND ended_at IS NULL",
                           (now.isoformat(timespec="seconds"), order_id))
        if cur.rowcount == 0:
            raise ValueError("El cronómetro no está corriendo.")


def finish_with_timer(order_id: int, now: datetime | None = None, db_path: Path | None = None) -> dict:
    """Termina la orden con el tiempo del cronómetro, repartido entre servicios según su tiempo estándar."""
    from src.orders import split_actual_hours

    now = now or datetime.now()
    hours = timer_state(order_id, now, db_path)["hours"]
    if hours <= 0:
        raise ValueError("Inicia el cronómetro antes de terminar la orden.")
    items = load_items(db_path)
    items = items[items["order_id"] == order_id]
    split = split_actual_hours(dict(zip(items["id"].astype(int), items["std_hours"])), hours)
    advance_order(order_id, "terminada", split, now, db_path)
    std = float(items["std_hours"].sum())
    return {"actual_hours": hours, "std_hours": std, "efficiency": std / hours}


# ---------- inventario ----------

def load_consumption(db_path: Path | None = None) -> pd.DataFrame:
    with connect(db_path) as conn:
        df = pd.read_sql_query(
            "SELECT part_id, created_at, -qty AS qty FROM inventory_movements WHERE kind='consumo'", conn)
    df["date"] = pd.to_datetime(df["created_at"]).dt.date
    return df


def load_movements(part_id: int, limit: int = 50, db_path: Path | None = None) -> list[dict]:
    with connect(db_path) as conn:
        rows = conn.execute(
            """SELECT m.created_at, m.qty, m.kind, m.note, o.folio FROM inventory_movements m
               LEFT JOIN orders o ON o.id = m.order_id WHERE m.part_id=? ORDER BY m.id DESC LIMIT ?""",
            (part_id, limit))
        return [dict(r) for r in rows]


def add_movement(part_id: int, qty: float, kind: str, note: str = "",
                 now: datetime | None = None, db_path: Path | None = None) -> float:
    """Entrada (+), salida (-) o ajuste (+/-). Regresa el nuevo stock."""
    if kind not in ("entrada", "ajuste", "salida"):
        raise ValueError("Tipo de movimiento inválido.")
    if qty == 0:
        raise ValueError("La cantidad no puede ser cero.")
    if kind == "entrada" and qty < 0:
        raise ValueError("Una entrada debe ser positiva.")
    signed = -abs(qty) if kind == "salida" else qty
    now = now or datetime.now()
    with connect(db_path) as conn:
        row = conn.execute("SELECT stock FROM parts WHERE id=?", (part_id,)).fetchone()
        if row is None:
            raise ValueError("Refacción no encontrada.")
        if row["stock"] + signed < 0:
            raise ValueError("El stock no puede quedar negativo.")
        conn.execute("UPDATE parts SET stock = stock + ? WHERE id=?", (signed, part_id))
        conn.execute("INSERT INTO inventory_movements(part_id, created_at, qty, kind, note) VALUES (?, ?, ?, ?, ?)",
                     (part_id, now.isoformat(timespec="seconds"), signed, kind, note))
        return float(row["stock"] + signed)


def update_part(part_id: int, price: float, lead_time_days: float, db_path: Path | None = None) -> None:
    if price < 0 or lead_time_days < 0:
        raise ValueError("Precio y tiempo de entrega no pueden ser negativos.")
    with connect(db_path) as conn:
        conn.execute("UPDATE parts SET price=?, lead_time_days=? WHERE id=?", (price, lead_time_days, part_id))


def update_service_steps(service_id: int, steps: list[str], db_path: Path | None = None) -> None:
    with connect(db_path) as conn:
        conn.execute("UPDATE services SET steps=? WHERE id=?",
                     ("\n".join(s.strip() for s in steps if s.strip()), service_id))


# ---------- clientes y reasignación ----------

def load_customers(db_path: Path | None = None) -> pd.DataFrame:
    """Clientes derivados de las órdenes (nombre + teléfono)."""
    orders = load_orders(db_path)
    if orders.empty:
        return pd.DataFrame(columns=["customer", "phone", "ordenes", "total", "ultima_visita", "vehiculos"])
    g = orders.groupby(["customer", "phone"], dropna=False)
    out = g.agg(ordenes=("id", "size"), total=("total", "sum"), ultima_visita=("created_at", "max"),
                vehiculos=("vehicle", lambda v: ", ".join(sorted(set(v))))).reset_index()
    return out.sort_values("ultima_visita", ascending=False).reset_index(drop=True)


def apply_assignments(assignments: list[dict], db_path: Path | None = None) -> int:
    """assignments: [{order_id, technician_id, bay_id, scheduled_date}]; solo afecta órdenes pendientes."""
    placeholders = ",".join("?" * len(config.PENDING_STATUSES))
    with connect(db_path) as conn:
        n = 0
        for a in assignments:
            cur = conn.execute(
                f"UPDATE orders SET technician_id=?, bay_id=?, scheduled_date=? "
                f"WHERE id=? AND status IN ({placeholders})",
                (a["technician_id"], a["bay_id"], a["scheduled_date"].isoformat(), a["order_id"],
                 *config.PENDING_STATUSES))
            n += cur.rowcount
        return n
