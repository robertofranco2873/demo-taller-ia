"""Autenticación (JWT), permisos por rol y utilidades de serialización."""
import json
import os
import secrets
from datetime import date, datetime, timedelta, timezone

import jwt
import pandas as pd
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src import clock
from src import db

JWT_ALGORITHM = "HS256"
TOKEN_HOURS = 12
# En producción JWT_SECRET viene del entorno (Render lo genera). Sin él, se usa uno aleatorio
# por proceso: las sesiones se invalidan al reiniciar, aceptable para desarrollo.
_SECRET = os.getenv("JWT_SECRET") or secrets.token_urlsafe(32)

bearer = HTTPBearer(auto_error=False)

ADMIN, RECEPCION, TECNICO = "admin", "recepcion", "tecnico"
STAFF = (ADMIN, RECEPCION)
ALL_ROLES = (ADMIN, RECEPCION, TECNICO)


def create_token(user: dict) -> str:
    now = datetime.now(timezone.utc)
    payload = {"sub": str(user["id"]), "role": user["role"], "iat": now,
               "exp": now + timedelta(hours=TOKEN_HOURS)}
    return jwt.encode(payload, _SECRET, algorithm=JWT_ALGORITHM)


def current_user(creds: HTTPAuthorizationCredentials | None = Depends(bearer)) -> dict:
    if creds is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Inicia sesión para continuar.",
                            headers={"WWW-Authenticate": "Bearer"})
    try:
        payload = jwt.decode(creds.credentials, _SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "La sesión expiró. Vuelve a iniciar sesión.")
    except jwt.InvalidTokenError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sesión inválida.")
    # Se consulta la base en cada petición: un cambio de rol o una baja aplican de inmediato.
    user = db.get_user(int(payload["sub"]))
    if user is None or not user["active"]:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Usuario inactivo o inexistente.")
    return user


def require_roles(*roles: str):
    def checker(user: dict = Depends(current_user)) -> dict:
        if user["role"] not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Tu rol no tiene permiso para esta acción.")
        return user
    return checker


DEMO_BLOCKED = "Desactivado en la demo pública: {accion}. Los datos se restablecen cada 24 h."


def deny_in_demo(accion: str) -> None:
    """En modo demo (DEMO_MODE=true) bloquea acciones destructivas con un 403 amable."""
    from src.config import demo_mode
    if demo_mode():
        raise HTTPException(status.HTTP_403_FORBIDDEN, DEMO_BLOCKED.format(accion=accion))


def bad_request(e: Exception) -> HTTPException:
    return HTTPException(status.HTTP_400_BAD_REQUEST, str(e))


def records(df: pd.DataFrame) -> list[dict]:
    """DataFrame → lista de dicts JSON-seguros (NaN → null, fechas → ISO)."""
    if df is None or len(df) == 0:
        return []
    out = df.copy()
    for col in out.columns:
        if out[col].dtype == object and out[col].map(lambda v: isinstance(v, (date, datetime))).any():
            out[col] = out[col].map(lambda v: v.isoformat() if isinstance(v, (date, datetime)) else v)
    return json.loads(out.to_json(orient="records", date_format="iso", date_unit="s"))


def clean(obj):
    """Convierte valores de pandas/numpy y fechas sueltas a tipos JSON."""
    if isinstance(obj, dict):
        return {k: clean(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [clean(v) for v in obj]
    if isinstance(obj, (pd.Timestamp, datetime, date)):
        return None if pd.isna(obj) else obj.isoformat()
    if hasattr(obj, "item"):  # numpy escalar
        obj = obj.item()
    if isinstance(obj, float) and obj != obj:  # NaN
        return None
    return obj


def parse_range(start: date | None, end: date | None, orders: pd.DataFrame) -> tuple[date, date]:
    min_d = orders["created_at"].min().date() if len(orders) else clock.today()
    max_d = orders["created_at"].max().date() if len(orders) else clock.today()
    start, end = start or min_d, end or max_d
    if end < start:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "La fecha final es anterior a la inicial.")
    return start, end
