from fastapi.testclient import TestClient

import app.launches as launchesmod
from app.auth import get_current_user
from app.db import connect
from app.main import app
from test_api import _seed


def _seed_context():
    unidade = _seed()
    con = connect()
    try:
        con.execute(
            "INSERT OR IGNORE INTO postos (legacy_id,unidade_id,nome,ordem,ativo) "
            "VALUES ('TEST-POSTO-1',?,?,1,1)",
            (unidade, "Assistente Social"),
        )
        posto = con.execute(
            "SELECT id FROM postos WHERE legacy_id='TEST-POSTO-1'"
        ).fetchone()["id"]
        con.execute(
            "INSERT OR IGNORE INTO insumos (legacy_id,tipo_unidade,subitem,descricao,previsao,ordem,ativo) "
            "VALUES ('TEST-INS-1','CRAS','Material de Limpeza','Água sanitária',10,1,1)"
        )
        insumo = con.execute(
            "SELECT id FROM insumos WHERE legacy_id='TEST-INS-1'"
        ).fetchone()["id"]
        con.commit()
        return unidade, posto, insumo
    finally:
        con.close()


def _as(email: str) -> None:
    app.dependency_overrides[get_current_user] = lambda: {
        "email": email,
        "email_verified": True,
    }


def _payload(unidade: int, posto: int, insumo: int, mes: str) -> dict:
    return {
        "unidade_id": unidade,
        "referencia_mes": mes,
        "tem_lanches": False,
        "lanches_previsto": 0,
        "parecer_opcao": "ATESTAR a regularidade da prestação dos serviços.",
        "classificacao": "Plenamente",
        "detalhe_postos": [
            {
                "posto_id": posto,
                "ocupado": True,
                "desempenho": "Satisfatório",
                "licenca_medica": "Sim",
            }
        ],
        "detalhe_insumos": [
            {"insumo_id": insumo, "previsto": 10, "executado": 9}
        ],
        "detalhe_veiculos": [],
        "composicao_kit": [],
        "locacao": [],
        "avaliacao_central": None,
        "confirmar_duplicado": False,
    }


def _health(launch_id: int):
    con = connect()
    try:
        row = con.execute(
            "SELECT licenca_medica FROM lancamento_postos WHERE lancamento_id = ?",
            (launch_id,),
        ).fetchone()
        return row["licenca_medica"] if row else None
    finally:
        con.close()


def test_health_data_mascarado_e_preservado(monkeypatch):
    unidade, posto, insumo = _seed_context()
    capturado = []

    def fake_pdf(data):
        capturado.append(data)
        return b"%PDF-1.4\n%%EOF\n"

    monkeypatch.setattr(launchesmod, "render_pdf", fake_pdf)
    try:
        with TestClient(app) as client:
            _as("user@local")
            r = client.post(
                "/lancamentos",
                json=_payload(unidade, posto, insumo, "2026-12-01"),
            )
            assert r.status_code == 200, r.text
            user_launch = r.json()["id"]
            assert _health(user_launch) is None

            _as("dev@local")
            r = client.post(
                "/lancamentos",
                json=_payload(unidade, posto, insumo, "2027-01-01"),
            )
            assert r.status_code == 200, r.text
            admin_launch = r.json()["id"]
            assert _health(admin_launch) == "Sim"

            _as("dev@local")
            admin_detail = client.get(f"/lancamentos/{admin_launch}").json()
            assert admin_detail["postos"][0]["licenca_medica"] == "Sim"

            _as("user@local")
            user_detail = client.get(f"/lancamentos/{admin_launch}").json()
            assert user_detail["postos"][0]["licenca_medica"] == "Restrito"

            pdf = client.get(f"/lancamentos/{admin_launch}/pdf")
            assert pdf.status_code == 200
            assert pdf.headers["content-type"].startswith("application/pdf")
            assert capturado[-1]["postos"][0]["licenca_medica"] == "Restrito"

            _as("dev@local")
            admin_pdf = client.get(f"/lancamentos/{admin_launch}/pdf")
            assert admin_pdf.status_code == 200
            assert capturado[-1]["postos"][0]["licenca_medica"] == "Sim"

            _as("user@local")
            # edição por não-admin não pode apagar o dado de saúde existente
            payload = _payload(unidade, posto, insumo, "2027-01-01")
            payload["detalhe_postos"][0]["licenca_medica"] = None
            r = client.put(f"/lancamentos/{admin_launch}", json=payload)
            assert r.status_code == 200, r.text
            assert _health(admin_launch) == "Sim"
    finally:
        app.dependency_overrides.pop(get_current_user, None)
