#!/usr/bin/env python3
"""Cria/atualiza o banco de staging com dados sintéticos.

Nunca usar dados de produção aqui. Uso:
    PYTHONPATH=api python3 etl/seed_staging.py --db /var/lib/sigpar/staging/staging.sqlite
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api"))

from app.migrate import apply_migrations  # noqa: E402


def seed(db_path: str) -> None:
    apply_migrations(db_path)
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    try:
        con.execute(
            "INSERT INTO itens_contrato (codigo,instituicao,cnpj,instrumento,objeto,"
            "vigencia_inicio,vigencia_fim,processo_instrutivo) VALUES (?,?,?,?,?,?,?,?) "
            "ON CONFLICT(codigo) DO UPDATE SET instituicao=excluded.instituicao",
            (
                "ITEM TESTE SIGPAR",
                "Instituição de Teste",
                "00.000.000/0001-00",
                "Nº TESTE/2026",
                "Objeto sintético para staging",
                "2026-01-01",
                "2028-12-31",
                "000000.000000/2026-00",
            ),
        )
        item = con.execute(
            "SELECT id FROM itens_contrato WHERE codigo='ITEM TESTE SIGPAR'"
        ).fetchone()["id"]

        unidades = [
            ("NÍVEL CENTRAL", "APOIO À GESTÃO", "APOIO À GESTÃO", 0, 0, 0),
            ("CRAS TESTE", "CRAS", "01ªCAS", 4, 100, 0),
            ("CREAS TESTE", "CREAS", "01ªCAS", 4, 100, 0),
            ("CAD TESTE", "CAD", "01ªCAS", 2, 0, 0),
            ("CAS TESTE", "CAS", "01ªCAS", 2, 0, 0),
        ]
        for nome, tipo, terr, postos, lanches, aluguel in unidades:
            con.execute(
                "INSERT INTO unidades (nome,nome_norm,tipo,territorio,item_id,"
                "postos_previstos,lanches_previstos,aluguel,ativo) VALUES (?,?,?,?,?,?,?,?,1) "
                "ON CONFLICT(nome_norm) DO UPDATE SET tipo=excluded.tipo,"
                "territorio=excluded.territorio,item_id=excluded.item_id,ativo=1",
                (nome, nome.lower(), tipo, terr, item, postos, lanches, aluguel),
            )
        unid_ids = {
            r["nome_norm"]: r["id"]
            for r in con.execute("SELECT id,nome_norm FROM unidades")
        }

        for email, nome, perfil in [
            ("leone.smtr@gmail.com", "Leone (staging)", "admin"),
            ("leone.abreu@prefeitura.rio", "Leone Abreu (staging)", "admin"),
        ]:
            con.execute(
                "INSERT INTO usuarios (email,nome,perfil,unidade_padrao_id,meta,ativo) "
                "VALUES (?,?,?,?,?,1) ON CONFLICT(email) DO UPDATE SET nome=excluded.nome,"
                "perfil=excluded.perfil,unidade_padrao_id=excluded.unidade_padrao_id,ativo=1",
                (email, nome, perfil, unid_ids["nível central"], 0),
            )

        postos = {
            "crãs teste": ["Assistente Social", "Psicólogo", "Orientador Social", "Auxiliar Administrativo"],
            "creas teste": ["Assistente Social", "Psicólogo", "Advogado", "Auxiliar Administrativo"],
            "cad teste": ["Atendente", "Supervisor"],
            "cas teste": ["Atendente", "Supervisor"],
        }
        for uname, nomes in postos.items():
            uname_key = uname.replace("crãs", "cras")
            uid = unid_ids.get(uname_key) or unid_ids.get(uname)
            if not uid:
                continue
            for ordem, nome in enumerate(nomes, 1):
                con.execute(
                    "INSERT INTO postos (legacy_id,unidade_id,nome,ordem,ativo) "
                    "VALUES (?,?,?,?,1) ON CONFLICT(legacy_id) DO UPDATE SET "
                    "unidade_id=excluded.unidade_id,nome=excluded.nome,ordem=excluded.ordem,ativo=1",
                    (f"STG-{uname_key.replace(' ', '-').upper()}-{ordem}", uid, nome, ordem),
                )

        insumos = {
            "CRAS": ["Água sanitária", "Desinfetante", "Sabão em pó"],
            "CREAS": ["Água sanitária", "Desinfetante", "Sabão em pó"],
            "CAD": ["Álcool 70%", "Papel toalha"],
            "CAS": ["Álcool 70%", "Papel toalha"],
        }
        for tipo, descs in insumos.items():
            for ordem, desc in enumerate(descs, 1):
                con.execute(
                    "INSERT INTO insumos (legacy_id,tipo_unidade,subitem,descricao,previsao,ordem,ativo) "
                    "VALUES (?,?,?,?,?,?,1) ON CONFLICT(legacy_id) DO UPDATE SET "
                    "tipo_unidade=excluded.tipo_unidade,subitem=excluded.subitem,"
                    "descricao=excluded.descricao,previsao=excluded.previsao,ordem=excluded.ordem",
                    (f"STG-INS-{tipo}-{ordem}", tipo, "Material de Limpeza", desc, 10, ordem),
                )
        for tipo in ("CRAS", "CREAS"):
            for ordem, desc in enumerate(["Água mineral sem gás", "Suco integral de fruta"], 1):
                con.execute(
                    "INSERT INTO kit_operacional (legacy_id,tipo_unidade,subitem,descricao,previsao,ordem,ativo) "
                    "VALUES (?,?,?,?,?,?,1) ON CONFLICT(legacy_id) DO UPDATE SET "
                    "tipo_unidade=excluded.tipo_unidade,descricao=excluded.descricao,previsao=excluded.previsao",
                    (f"STG-KIT-{tipo}-{ordem}", tipo, "Lanche", desc, 100, ordem),
                )
        for nome, qtd in [("Veículo Sedan", 2), ("Van 16 lugares", 1)]:
            con.execute(
                "INSERT INTO veiculos (unidade_id,nome,quantidade) VALUES (?,?,?) "
                "ON CONFLICT(unidade_id,nome) DO UPDATE SET quantidade=excluded.quantidade",
                (unid_ids["nível central"], nome, qtd),
            )
        for criterio, media in [
            ("Pontualidade do Motorista", 4.8),
            ("Cordialidade do Motorista", 4.9),
        ]:
            con.execute(
                "INSERT INTO avaliacoes_servico (unidade_id,criterio,media,satisfacao,referencia_mes) "
                "VALUES (?,?,?,?,?) ON CONFLICT(unidade_id,criterio,referencia_mes) DO UPDATE SET "
                "media=excluded.media,satisfacao=excluded.satisfacao",
                (unid_ids["nível central"], criterio, media, media / 5, "2026-01-01"),
            )
        con.commit()
        print("staging seed ok:", db_path)
    finally:
        con.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--db", default="/var/lib/sigpar/staging/staging.sqlite"
    )
    args = parser.parse_args()
    seed(args.db)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
