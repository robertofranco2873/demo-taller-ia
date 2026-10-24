from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from api.core import create_token, current_user
from src import db
from src.security import ROLE_LABELS, verify_password
from src.seed import DEMO_PASSWORD, DEMO_USERS

router = APIRouter(prefix="/api/auth", tags=["Autenticación"])


class LoginIn(BaseModel):
    username: str
    password: str


@router.post("/login", summary="Iniciar sesión (devuelve un JWT)")
def login(body: LoginIn):
    user = db.get_user_auth(body.username)
    if user is None or not user["active"] or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Usuario o contraseña incorrectos.")
    user.pop("password_hash")
    return {"access_token": create_token(user), "token_type": "bearer", "user": user}


@router.get("/me", summary="Usuario de la sesión actual")
def me(user: dict = Depends(current_user)):
    return user


@router.get("/demo-users", summary="Usuarios demo visibles en el login (públicos a propósito)")
def demo_users():
    shown = {"gerente", "recepcion", "tecnico"}
    return [{"username": u, "name": n, "role": r, "role_label": ROLE_LABELS[r], "password": DEMO_PASSWORD}
            for u, n, r, _ in DEMO_USERS if u in shown]
