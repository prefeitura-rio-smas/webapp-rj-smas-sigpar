from fastapi.testclient import TestClient

from app.db import connect
from app.main import app


def _seed():
    con = connect()
    try:
        con.execute(
            "INSERT OR IGNORE INTO unidades (nome, nome_norm, tipo, territorio) "
            "VALUES ('NÍVEL CENTRAL', 'nível central', 'APOIO À GESTÃO', 'APOIO À GESTÃO')"
        )
        con.execute(
            "INSERT OR IGNORE INTO unidades (nome, nome_norm, tipo, territorio) "
            "VALUES ('CRAS TESTE', 'cras teste', 'CRAS', '01ªCAS')"
        )
        unidade = con.execute(
            "SELECT id FROM unidades WHERE nome_norm = 'cras teste'"
        ).fetchone()["id"]
        con.execute(
            "INSERT OR IGNORE INTO usuarios (email, nome, perfil, unidade_padrao_id) "
            "VALUES (?, ?, ?, ?)",
            ("dev@local", "Dev", "admin", unidade),
        )
        con.execute(
            "INSERT OR IGNORE INTO usuarios (email, nome, perfil, unidade_padrao_id) "
            "VALUES (?, ?, ?, ?)",
            ("user@local", "User", "user", unidade),
        )
        con.commit()
    finally:
        con.close()
    return unidade


def test_health():
    with TestClient(app) as client:
        r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["schema_version"] == "1"


def test_me_admin_ve_todas_as_unidades():
    _seed()
    with TestClient(app) as client:
        r = client.get("/me")
    assert r.status_code == 200
    body = r.json()
    assert body["email"] == "dev@local"
    assert body["perfil"] == "admin"
    nomes = {u["nome"] for u in body["unidades_permitidas"]}
    assert "CRAS TESTE" in nomes
    assert "NÍVEL CENTRAL" in nomes


def test_view_permissoes_user():
    unidade = _seed()
    con = connect()
    try:
        rows = con.execute(
            "SELECT nome FROM vw_unidades_permitidas WHERE email = 'user@local'"
        ).fetchall()
    finally:
        con.close()
    assert [r["nome"] for r in rows] == ["CRAS TESTE"]
    assert unidade > 0
