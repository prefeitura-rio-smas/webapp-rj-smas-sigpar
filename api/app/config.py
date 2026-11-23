import os
from dataclasses import dataclass
from functools import lru_cache


def _cors_origins() -> tuple[str, ...]:
    raw = os.getenv(
        "SIGPAR_CORS_ORIGINS",
        "https://sigpar.web.app,"
        "https://sigpar.firebaseapp.com,"
        "https://sigpar-smas.web.app,"
        "https://sigpar-smas.firebaseapp.com",
    )
    return tuple(x.strip() for x in raw.split(",") if x.strip())


@dataclass(frozen=True)
class Settings:
    db_path: str
    firebase_project: str
    cors_origins: tuple[str, ...]
    noauth: bool
    dev_email: str
    app_name: str = "SIGPAR API"
    version: str = "0.1.0"


@lru_cache
def get_settings() -> Settings:
    return Settings(
        db_path=os.getenv("SIGPAR_DB", "/root/sigpar/db/sigpar.sqlite"),
        firebase_project=os.getenv("SIGPAR_FIREBASE_PROJECT", "sigpar-smas"),
        cors_origins=_cors_origins(),
        noauth=os.getenv("SIGPAR_NOAUTH", "0") == "1",
        dev_email=os.getenv("SIGPAR_DEV_EMAIL", "dev@local"),
    )
