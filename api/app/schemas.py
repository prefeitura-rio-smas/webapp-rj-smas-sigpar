from pydantic import BaseModel


class UnidadePermitida(BaseModel):
    unidade_id: int
    nome: str
    tipo: str | None = None
    territorio: str | None = None


class UsuarioOut(BaseModel):
    email: str
    nome: str | None = None
    perfil: str
    unidade_padrao_id: int | None = None
    territorio: str | None = None
    meta: float = 0
    ativo: int = 1


class MeResponse(BaseModel):
    email: str
    nome: str | None = None
    perfil: str
    unidade_padrao_id: int | None = None
    meta: float = 0
    unidades_permitidas: list[UnidadePermitida]


class HealthResponse(BaseModel):
    ok: bool
    app: str
    version: str
    schema_version: str | None = None
    db: str
