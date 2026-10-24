"""Hash de contraseñas con bcrypt."""
import os

import bcrypt

ROLES = ("admin", "recepcion", "tecnico")
ROLE_LABELS = {"admin": "Administrador / gerente", "recepcion": "Recepción / asesor", "tecnico": "Técnico"}


def _rounds() -> int:
    return int(os.getenv("BCRYPT_ROUNDS", "12"))


def hash_password(password: str) -> str:
    if len(password) < 6:
        raise ValueError("La contraseña debe tener al menos 6 caracteres.")
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(_rounds())).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False
