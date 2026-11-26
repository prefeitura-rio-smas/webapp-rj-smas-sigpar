from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .auth import get_current_user
from .config import get_settings
from .db import connect, init_db
from .launches import router as launches_router
from .migrate import apply_migrations
from .permissions import get_usuario, unidades_permitidas
from .schemas import HealthResponse, MeResponse


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ARG001
    init_db()
    apply_migrations()
    yield


settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    docs_url=None,
    redoc_url=None,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
    max_age=3600,
)

app.include_router(launches_router)


@app.middleware("http")
async def security_headers(request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault(
        "Permissions-Policy", "camera=(), microphone=(), geolocation=()"
    )
    response.headers.setdefault(
        "Content-Security-Policy", "default-src 'none'; frame-ancestors 'none'"
    )
    return response


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    try:
        con = connect()
        try:
            row = con.execute(
                "SELECT value FROM schema_meta WHERE key = 'version'"
            ).fetchone()
            schema_version = row["value"] if row else None
            con.execute("SELECT 1").fetchone()
        finally:
            con.close()
        return HealthResponse(
            ok=True,
            app=settings.app_name,
            version=settings.version,
            schema_version=schema_version,
            db="ok",
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=503, detail=f"db indisponivel: {exc}") from exc


@app.get("/me", response_model=MeResponse)
def me(user: dict = Depends(get_current_user)) -> MeResponse:
    usuario = get_usuario(user["email"])
    if not usuario:
        raise HTTPException(status_code=403, detail="nao autorizado")
    if not usuario["ativo"]:
        raise HTTPException(status_code=403, detail="usuario inativo")

    unidades = unidades_permitidas(user["email"])
    return MeResponse(
        email=usuario["email"],
        nome=usuario["nome"],
        perfil=usuario["perfil"],
        unidade_padrao_id=usuario["unidade_padrao_id"],
        meta=usuario["meta"] or 0,
        unidades_permitidas=unidades,
    )


@app.get("/", include_in_schema=False)
def root() -> dict:
    return {"app": settings.app_name, "version": settings.version, "status": "ok"}
