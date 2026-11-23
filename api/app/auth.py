from fastapi import Header, HTTPException

from google.auth.transport import requests as grequests
from google.oauth2 import id_token

from .config import get_settings


def get_current_user(authorization: str = Header(default="")) -> dict:
    """Valida o Firebase ID token e devolve o payload do usuário.

    Em desenvolvimento (SIGPAR_NOAUTH=1) devolve um usuário fake; nunca usar
    esse modo em produção.
    """
    cfg = get_settings()
    if cfg.noauth:
        return {"email": cfg.dev_email, "email_verified": True, "name": "Dev"}

    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="sem token")

    token = authorization[7:].strip()
    if not token:
        raise HTTPException(status_code=401, detail="token vazio")

    try:
        info = id_token.verify_firebase_token(
            token,
            grequests.Request(),
            cfg.firebase_project,
            clock_skew_in_seconds=60,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"AUTH FAIL {type(exc).__name__}: {exc}", flush=True)
        raise HTTPException(status_code=401, detail="token invalido") from exc

    if not info.get("email_verified"):
        raise HTTPException(status_code=403, detail="email nao verificado")

    email = (info.get("email") or "").strip().lower()
    if not email:
        raise HTTPException(status_code=401, detail="token sem email")

    info["email"] = email
    return info
