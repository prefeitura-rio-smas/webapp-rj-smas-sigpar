import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

import app.auth as authmod
import app.main as mainmod
from app.auth import get_current_user
from app.config import get_settings
from app.db import connect
from app.main import app
from test_api import _seed
from test_health_mask import _payload, _seed_context


def _as(email: str) -> None:
    app.dependency_overrides[get_current_user] = lambda: {
        "email": email,
        "email_verified": True,
    }


@pytest.fixture(autouse=True)
def _limpar_override():
    yield
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def auth_real(monkeypatch):
    monkeypatch.setenv("SIGPAR_NOAUTH", "0")
    get_settings.cache_clear()
    yield
    monkeypatch.setenv("SIGPAR_NOAUTH", "1")
    get_settings.cache_clear()


def _central_id() -> int:
    con = connect()
    try:
        return con.execute(
            "SELECT id FROM unidades WHERE nome_norm = 'nível central'"
        ).fetchone()["id"]
    finally:
        con.close()


def test_root_contract():
    with TestClient(app) as client:
        r = client.get("/")
    assert r.status_code == 200
    assert set(r.json()) == {"app", "version", "status"}
    assert r.json()["status"] == "ok"


def test_health_contract_e_headers():
    with TestClient(app) as client:
        r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert set(body) == {"ok", "app", "version", "schema_version", "db"}
    assert body["ok"] is True
    assert body["db"] == "ok"
    assert body["schema_version"] == "1"
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["x-frame-options"] == "DENY"
    assert r.headers["referrer-policy"] == "no-referrer"
    assert "default-src 'none'" in r.headers["content-security-policy"]


def test_health_db_indisponivel_retorna_503(monkeypatch):
    def falha():
        raise RuntimeError("db fora")

    monkeypatch.setattr(mainmod, "connect", falha)
    with TestClient(app) as client:
        r = client.get("/health")
    assert r.status_code == 503
    assert "db indisponivel" in r.json()["detail"]


def test_cors_allowlist():
    with TestClient(app) as client:
        preflight = client.options(
            "/health",
            headers={
                "Origin": "https://sigpar.web.app",
                "Access-Control-Request-Method": "GET",
            },
        )
        bloqueado = client.get(
            "/health", headers={"Origin": "https://evil.example"}
        )
    assert preflight.status_code == 200
    assert preflight.headers["access-control-allow-origin"] == "https://sigpar.web.app"
    assert "access-control-allow-origin" not in bloqueado.headers


def test_me_contract():
    _seed()
    _as("dev@local")
    with TestClient(app) as client:
        r = client.get("/me")
    assert r.status_code == 200
    body = r.json()
    assert set(body) == {
        "email",
        "nome",
        "perfil",
        "unidade_padrao_id",
        "meta",
        "unidades_permitidas",
    }
    assert body["email"] == "dev@local"
    assert body["perfil"] == "admin"
    assert any(u["nome"] == "CRAS TESTE" for u in body["unidades_permitidas"])


def test_me_recusa_desconhecido_e_inativo():
    _seed()
    con = connect()
    try:
        unidade = con.execute(
            "SELECT id FROM unidades WHERE nome_norm = 'cras teste'"
        ).fetchone()["id"]
        con.execute(
            "INSERT OR IGNORE INTO usuarios (email, nome, perfil, unidade_padrao_id, ativo) "
            "VALUES (?, ?, 'user', ?, 0)",
            ("inativo@local", "Inativo", unidade),
        )
        con.commit()
    finally:
        con.close()

    _as("naoexiste@local")
    with TestClient(app) as client:
        assert client.get("/me").status_code == 403

    _as("inativo@local")
    with TestClient(app) as client:
        assert client.get("/me").status_code == 403


def test_unidades_e_contexto_contract():
    _seed()
    _as("dev@local")
    with TestClient(app) as client:
        unidades = client.get("/unidades")
        central = _central_id()
        contexto = client.get(f"/unidades/{central}/contexto")
    assert unidades.status_code == 200
    assert isinstance(unidades.json(), list)
    assert contexto.status_code == 200
    body = contexto.json()
    assert set(body) == {
        "unidade",
        "item",
        "postos",
        "insumos",
        "kit",
        "veiculos",
        "avaliacoes_servico",
        "pode_central",
        "unidades_aluguel",
    }
    assert body["pode_central"] is True

    _as("user@local")
    with TestClient(app) as client:
        assert client.get(f"/unidades/{central}/contexto").status_code == 403
        assert (
            client.get("/lancamentos", params={"unidade_id": central}).status_code
            == 403
        )


def test_lancamento_contract_e_lista():
    unidade, posto, insumo = _seed_context()
    _as("dev@local")
    with TestClient(app) as client:
        criado = client.post(
            "/lancamentos",
            json=_payload(unidade, posto, insumo, "2028-01-01"),
        )
        assert criado.status_code == 200, criado.text
        launch_id = criado.json()["id"]
        lista = client.get("/lancamentos")
        detalhe = client.get(f"/lancamentos/{launch_id}")
        por_legacy = client.get(
            "/lancamentos", params={"id_lancamento": criado.json()["legacy_id"]}
        )
    assert set(criado.json()) == {"id", "legacy_id", "duplicado", "pdf_url"}
    assert lista.status_code == 200
    assert all("legacy_id" in item for item in lista.json())
    assert detalhe.status_code == 200
    assert {
        "lancamento",
        "unidade",
        "item",
        "autor_perfil",
        "postos",
        "insumos",
        "veiculos",
        "lanches",
        "kit",
        "locacao",
        "avaliacao_central",
    } <= set(detalhe.json())
    assert detalhe.json()["postos"][0]["licenca_medica"] == "Sim"
    assert por_legacy.status_code == 200
    assert [item["id"] for item in por_legacy.json()] == [launch_id]


def test_duplicidade_409_e_confirmacao():
    unidade, posto, insumo = _seed_context()
    _as("user@local")
    payload = _payload(unidade, posto, insumo, "2028-03-01")
    with TestClient(app) as client:
        assert client.post("/lancamentos", json=payload).status_code == 200
        dup = client.post("/lancamentos", json=payload)
        assert dup.status_code == 409
        assert "existentes" in dup.json()["detail"]
        payload["confirmar_duplicado"] = True
        confirmado = client.post("/lancamentos", json=payload)
    assert confirmado.status_code == 200
    assert confirmado.json()["duplicado"] is True


def test_validacao_de_payload_e_limites():
    unidade, posto, insumo = _seed_context()
    _as("user@local")
    with TestClient(app) as client:
        assert (
            client.post(
                "/lancamentos",
                json=_payload(unidade, posto, insumo, "2028-13"),
            ).status_code
            == 422
        )
        invalido = _payload(unidade, posto, insumo, "2028-06-01")
        invalido["detalhe_postos"][0]["posto_id"] = 999999
        assert client.post("/lancamentos", json=invalido).status_code == 422
        assert client.get("/lancamentos", params={"limit": 0}).status_code == 422
        assert client.get("/lancamentos", params={"limit": 201}).status_code == 422
        assert client.get("/lancamentos", params={"mes": "2028-13"}).status_code == 422


def test_lancamento_nivel_central_completo():
    _seed()
    central = _central_id()
    con = connect()
    try:
        con.execute(
            "INSERT OR IGNORE INTO veiculos (unidade_id, nome, quantidade) VALUES (?, ?, ?)",
            (central, "Veiculo Teste", 1),
        )
        veiculo = con.execute(
            "SELECT id FROM veiculos WHERE unidade_id = ? AND nome = 'Veiculo Teste'",
            (central,),
        ).fetchone()["id"]
        con.execute(
            "INSERT OR IGNORE INTO kit_operacional "
            "(legacy_id, tipo_unidade, subitem, descricao, previsao, ordem, ativo) "
            "VALUES ('TEST-KIT-1', 'APOIO À GESTÃO', 'Kit', 'Kit teste', 1, 1, 1)"
        )
        con.commit()
    finally:
        con.close()

    payload = {
        "unidade_id": central,
        "referencia_mes": "2028-04-01",
        "tem_lanches": True,
        "lanches_previsto": 10,
        "lanches_executado": 9,
        "parecer_opcao": "ATESTAR a regularidade da prestação dos serviços.",
        "classificacao": "Plenamente",
        "detalhe_postos": [],
        "detalhe_insumos": [],
        "detalhe_veiculos": [
            {"veiculo_id": veiculo, "previsto": 10, "executado": 8}
        ],
        "composicao_kit": [
            {
                "item": "Kit teste",
                "quantitativo": 1,
                "conformidade": "OK",
                "percentual": 1,
                "obs": "teste",
            }
        ],
        "locacao": [
            {
                "unidade_locacao": "Unidade X",
                "dias_corridos": 30,
                "controle_regularizacao": "OK",
                "nota": "1",
                "data_autorizo": "2028-04-01",
            }
        ],
        "avaliacao_central": {
            "perfil_meta": 100,
            "nota1": 10,
            "nota2": 10,
            "nota3": 10,
            "nota4": 10,
            "nota5": 10,
            "nota6": 10,
            "nota7": 10,
            "nota8": 10,
            "nota9": 10,
            "nota10": 10,
            "nota11": 10,
            "obs_nutricionista": "ok",
        },
        "confirmar_duplicado": False,
    }
    _as("dev@local")
    with TestClient(app) as client:
        criado = client.post("/lancamentos", json=payload)
        assert criado.status_code == 200, criado.text
        detalhe = client.get(f"/lancamentos/{criado.json()['id']}")
    assert detalhe.status_code == 200
    body = detalhe.json()
    assert body["lancamento"]["unidade_nome"] == "NÍVEL CENTRAL"
    assert len(body["veiculos"]) == 1
    assert len(body["kit"]) == 1
    assert len(body["locacao"]) == 1
    assert body["avaliacao_central"]["nota11"] == 10
    assert body["lanches"][0]["executado"] == 9


def test_lancamento_central_nao_acessivel_por_user():
    _seed()
    central = _central_id()
    payload = {
        "unidade_id": central,
        "referencia_mes": "2028-07-01",
        "parecer_opcao": "ATESTAR a regularidade da prestação dos serviços.",
        "classificacao": "Plenamente",
    }
    _as("dev@local")
    with TestClient(app) as client:
        criado = client.post("/lancamentos", json=payload)
        assert criado.status_code == 200
        launch_id = criado.json()["id"]
    _as("user@local")
    with TestClient(app) as client:
        assert client.get(f"/lancamentos/{launch_id}").status_code == 403
        assert client.get(f"/lancamentos/{launch_id}/pdf").status_code == 403


def test_edicao_admin_e_exclusao_restrita():
    unidade, posto, insumo = _seed_context()
    payload = _payload(unidade, posto, insumo, "2028-05-01")
    _as("dev@local")
    with TestClient(app) as client:
        criado = client.post("/lancamentos", json=payload)
        assert criado.status_code == 200
        launch_id = criado.json()["id"]
        payload["classificacao"] = "Parcialmente"
        editado = client.put(f"/lancamentos/{launch_id}", json=payload)
    assert editado.status_code == 200

    _as("user@local")
    with TestClient(app) as client:
        assert client.delete(f"/lancamentos/{launch_id}").status_code == 403

    _as("dev@local")
    with TestClient(app) as client:
        assert client.delete(f"/lancamentos/{launch_id}").status_code == 200
        assert client.get(f"/lancamentos/{launch_id}").status_code == 404


def test_busca_nao_e_vulneravel_a_sql_injection():
    _seed()
    _as("user@local")
    with TestClient(app) as client:
        r = client.get(
            "/lancamentos", params={"id_lancamento": "1' OR '1'='1"}
        )
    assert r.status_code == 200
    assert r.json() == [] or all(
        item["legacy_id"] == "1' OR '1'='1" for item in r.json()
    )


def test_auth_exige_bearer(auth_real):
    with pytest.raises(HTTPException) as sem_token:
        get_current_user("")
    assert sem_token.value.status_code == 401
    with pytest.raises(HTTPException) as vazio:
        get_current_user("Bearer ")
    assert vazio.value.status_code == 401


def test_auth_recusa_token_invalido(auth_real, monkeypatch):
    def falha(*args, **kwargs):
        raise ValueError("token ruim")

    monkeypatch.setattr(authmod.id_token, "verify_firebase_token", falha)
    with pytest.raises(HTTPException) as exc:
        get_current_user("Bearer token-invalido")
    assert exc.value.status_code == 401


def test_auth_recusa_email_nao_verificado(auth_real, monkeypatch):
    monkeypatch.setattr(
        authmod.id_token,
        "verify_firebase_token",
        lambda *args, **kwargs: {"email": "user@local", "email_verified": False},
    )
    with pytest.raises(HTTPException) as exc:
        get_current_user("Bearer token")
    assert exc.value.status_code == 403


def test_auth_normaliza_email(auth_real, monkeypatch):
    monkeypatch.setattr(
        authmod.id_token,
        "verify_firebase_token",
        lambda *args, **kwargs: {"email": "USER@LOCAL", "email_verified": True},
    )
    user = get_current_user("Bearer token")
    assert user["email"] == "user@local"
