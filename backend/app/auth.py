import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta

import httpx
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .config import settings
from .models import Credentials
from .store import LocalStore

bearer = HTTPBearer(auto_error=False)


def secret():
    root = settings().data_dir
    root.mkdir(parents=True, exist_ok=True)
    path = root / "session.key"
    try:
        with path.open("x") as file:
            file.write(secrets.token_hex(32))
    except FileExistsError:
        pass
    return path.read_text().strip()


def password_hash(password, salt):
    return hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 600000).hex()


async def authenticate(credentials: Credentials, register=False):
    email = credentials.email.lower().strip()
    if settings().app_mode == "cloud":
        operation = "signUp" if register else "signInWithPassword"
        async with httpx.AsyncClient(timeout=20) as client:
            try:
                response = await client.post(
                    f"https://identitytoolkit.googleapis.com/v1/accounts:{operation}",
                    params={"key": settings().firebase_web_api_key},
                    json={
                        "email": email,
                        "password": credentials.password,
                        "returnSecureToken": True,
                    },
                )
            except httpx.HTTPError:
                raise HTTPException(
                    503, "Firebase no está disponible. Intenta nuevamente."
                ) from None
        if response.status_code != 200:
            raise HTTPException(
                400 if register else 401,
                "No se pudo crear la cuenta. Revisa el correo y la contraseña."
                if register
                else "Correo o contraseña incorrectos.",
            )
        data = response.json()
        return {"token": data["idToken"], "email": data["email"], "expires_in": 3600}
    store = LocalStore()
    key = hashlib.sha256(email.encode()).hexdigest()
    if register:
        salt = secrets.token_hex(16)

        def create(existing):
            if existing:
                raise HTTPException(400, "No se pudo crear la cuenta. Prueba iniciar sesión.")
            return {
                "id": key,
                "email": email,
                "salt": salt,
                "hash": password_hash(credentials.password, salt),
            }

        user = store.mutate("users", key, create)
    else:
        user = store.get("users", key)
        salt = user["salt"] if user else "00" * 16
        calculated = password_hash(credentials.password, salt)
        if not user or not hmac.compare_digest(calculated, user["hash"]):
            raise HTTPException(401, "Correo o contraseña incorrectos.")
    token = jwt.encode(
        {
            "sub": key,
            "email": email,
            "aud": "pqr-local",
            "exp": datetime.now(UTC) + timedelta(hours=1),
        },
        secret(),
        algorithm="HS256",
    )
    return {"token": token, "email": email, "expires_in": 3600}


def current_user(authorization: HTTPAuthorizationCredentials | None = Depends(bearer)):
    if not authorization:
        raise HTTPException(401, "Inicia sesión para continuar.")
    try:
        if settings().app_mode == "cloud":
            import firebase_admin
            from firebase_admin import auth

            try:
                app = firebase_admin.get_app()
            except ValueError:
                app = firebase_admin.initialize_app(
                    options={
                        "projectId": settings().firebase_project_id
                        or settings().google_cloud_project
                    }
                )
            claims = auth.verify_id_token(authorization.credentials, app=app)
            return {"id": claims["uid"], "email": claims.get("email", "")}
        claims = jwt.decode(
            authorization.credentials, secret(), algorithms=["HS256"], audience="pqr-local"
        )
        return {"id": claims["sub"], "email": claims["email"]}
    except Exception:
        raise HTTPException(401, "Tu sesión venció. Inicia sesión nuevamente.") from None
