#!/usr/bin/env python3
"""ETL Sheet -> SQLite do SIGPAR.

Uso:
    python3 etl/migrate_from_sheet.py --xlsx /caminho/SIGPAR.xlsx
    python3 etl/migrate_from_sheet.py --xlsx /caminho/SIGPAR.xlsx --write
    python3 etl/migrate_from_sheet.py --token "$TOKEN" --write --db /tmp/teste.sqlite

Sem `--write` é dry-run: lê a planilha, mostra o mapeamento e a reconciliação
sem alterar o banco.
"""
from __future__ import annotations

import argparse
import io
import json
import os
import sqlite3
import sys
import urllib.request
from collections import Counter, defaultdict
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "db" / "schema.sql"
DEFAULT_DB = ROOT / "db" / "sigpar.sqlite"
DRIVE_ID = os.getenv("SIGPAR_SOURCE_SHEET_ID", "")

EXPECTED_ROWS = {
    "Unidades": 86,
    "Item": 7,
    "Operacional": 20,
    "Insumos": 196,
    "Veiculos": 2,
    "Postos": 1260,
    "Responsaveis": 95,
    "Avaliacao": 6,
    "Registro_Locacao": 3,
    "Avaliacao_Central": 1,
    "Composicao_Kit_Nutricionista": 407,
    "Registro_Insumos": 4787,
    "Registro_Lanches": 60,
    "Ocupacao_Postos": 1237,
    "Historico_Lancamentos": 83,
}


# ---------------------------------------------------------------------------
# Normalização
# ---------------------------------------------------------------------------

def now_brt() -> str:
    return datetime.now(ZoneInfo("America/Sao_Paulo")).strftime("%Y-%m-%d %H:%M:%S")


def norm_nome(value) -> str:
    return str(value or "").strip().lower()


def parse_text(value) -> str:
    if value is None:
        return ""
    return str(value).strip()


def parse_dt(value) -> str | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(value, date):
        return value.strftime("%Y-%m-%d 00:00:00")
    text = str(value).strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%d/%m/%Y %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(text, fmt).strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue
    return text


def parse_mes(value) -> str | None:
    dt = parse_dt(value)
    if not dt or len(dt) < 7:
        return None
    return dt[:7] + "-01"


def parse_float(value) -> float | None:
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace(" ", "")
    if text.upper() in ("N/A", "NA", "-", "NÃO", "NAO"):
        return None
    if "," in text:
        text = text.replace(".", "").replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return None


def parse_bool(value) -> int:
    return 1 if str(value or "").strip().upper() in ("TRUE", "1", "SIM", "S") else 0


def normalizar_classificacao(value) -> str:
    text = str(value or "").strip()
    return {
        "pleno": "Plenamente",
        "plenamente": "Plenamente",
        "parcial": "Parcialmente",
        "parcialmente": "Parcialmente",
        "não": "Não",
        "nao": "Não",
    }.get(text.lower(), text)


def parecer_codigo(value) -> str:
    text = str(value or "").upper()
    if "COM RESSALVA" in text:
        return "atestar_ressalva"
    if "NÃO ATESTAR" in text or "NAO ATESTAR" in text:
        return "nao_atestar"
    if "ATESTAR" in text:
        return "atestar"
    return ""


# ---------------------------------------------------------------------------
# Leitura da planilha
# ---------------------------------------------------------------------------

def load_workbook_from_drive(file_id: str, token: str):
    req = urllib.request.Request(
        f"https://www.googleapis.com/drive/v3/files/{file_id}/export"
        "?mimeType=application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Authorization": f"Bearer {token}"},
    )
    return load_workbook(io.BytesIO(urllib.request.urlopen(req, timeout=180).read()), read_only=True, data_only=True)


def sheet_dicts(wb, name: str):
    ws = wb[name]
    rows = ws.iter_rows(values_only=True)
    try:
        header = next(rows)
    except StopIteration:
        return
    keys = [str(h or "").strip().lower() for h in header]
    for row in rows:
        if not any(v not in (None, "") for v in row):
            continue
        yield {keys[i]: row[i] for i in range(min(len(keys), len(row)))}


def get(d: dict, key: str):
    return d.get(key.strip().lower())


# ---------------------------------------------------------------------------
# Importação
# ---------------------------------------------------------------------------

class Migration:
    def __init__(self, con: sqlite3.Connection):
        self.con = con
        self.warnings: list[str] = []
        self.unit_ids: dict[str, int] = {}
        self.item_ids: dict[str, int] = {}
        self.launch_ids: dict[str, int] = {}
        self.launch_info: dict[str, dict] = {}
        self.post_ids: dict[str, int] = {}
        self.insumo_ids: dict[tuple, int] = {}
        self.insumo_generic: dict[tuple, list[int]] = defaultdict(list)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)

    # -- cadastros ---------------------------------------------------------
    def import_items(self, wb) -> None:
        for d in sheet_dicts(wb, "Item"):
            code = parse_text(get(d, "item"))
            if not code:
                self.warn("Item: linha sem codigo ignorada")
                continue
            self.con.execute(
                "INSERT INTO itens_contrato (codigo,instituicao,cnpj,instrumento,objeto,"
                "vigencia_inicio,vigencia_fim,processo_instrutivo) VALUES (?,?,?,?,?,?,?,?) "
                "ON CONFLICT(codigo) DO UPDATE SET instituicao=excluded.instituicao,"
                "cnpj=excluded.cnpj,instrumento=excluded.instrumento,objeto=excluded.objeto,"
                "vigencia_inicio=excluded.vigencia_inicio,vigencia_fim=excluded.vigencia_fim,"
                "processo_instrutivo=excluded.processo_instrutivo",
                (
                    code,
                    parse_text(get(d, "instituição")),
                    parse_text(get(d, "cnpj")),
                    parse_text(get(d, "número do instrumento")),
                    parse_text(get(d, "objeto")),
                    parse_dt(get(d, "vigência (início)")),
                    parse_dt(get(d, "vigência (término)")),
                    parse_text(get(d, "número do processo instrutivo")),
                ),
            )
            row = self.con.execute("SELECT id FROM itens_contrato WHERE codigo=?", (code,)).fetchone()
            self.item_ids[code] = row["id"]
            self.item_ids[norm_nome(code)] = row["id"]

    def import_units(self, wb) -> None:
        for d in sheet_dicts(wb, "Unidades"):
            nome = parse_text(get(d, "unidade"))
            if not nome:
                self.warn("Unidades: linha sem nome ignorada")
                continue
            nome_norm = norm_nome(nome)
            item_code = parse_text(get(d, "item"))
            item_id = self.item_ids.get(item_code) or self.item_ids.get(norm_nome(item_code))
            self.con.execute(
                "INSERT INTO unidades (legacy_id,nome,nome_norm,tipo,territorio,item_id,"
                "postos_previstos,lanches_previstos,aluguel,ativo) VALUES (?,?,?,?,?,?,?,?,?,1) "
                "ON CONFLICT(nome_norm) DO UPDATE SET legacy_id=excluded.legacy_id,"
                "nome=excluded.nome,tipo=excluded.tipo,territorio=excluded.territorio,"
                "item_id=excluded.item_id,postos_previstos=excluded.postos_previstos,"
                "lanches_previstos=excluded.lanches_previstos,aluguel=excluded.aluguel,ativo=1",
                (
                    parse_text(get(d, "id_unidade")) or None,
                    nome,
                    nome_norm,
                    parse_text(get(d, "tipo")),
                    parse_text(get(d, "territorio")),
                    item_id,
                    parse_float(get(d, "postos")) or 0,
                    parse_float(get(d, "lanches")) or 0,
                    parse_bool(get(d, "aluguel")),
                ),
            )
            row = self.con.execute("SELECT id FROM unidades WHERE nome_norm=?", (nome_norm,)).fetchone()
            self.unit_ids[nome_norm] = row["id"]

    def import_users(self, wb) -> None:
        seen: set[str] = set()
        for d in sheet_dicts(wb, "Responsaveis"):
            email = parse_text(get(d, "email")).lower()
            if not email:
                continue
            if email in seen:
                self.warn(f"Responsaveis: email duplicado {email}")
            seen.add(email)
            perfil_raw = parse_text(get(d, "perfil")).lower()
            perfil = {"admin": "admin", "cord": "cord", "user": "user"}.get(perfil_raw, "user")
            unidade = norm_nome(get(d, "unidade"))
            unidade_id = self.unit_ids.get(unidade)
            if not unidade_id:
                self.warn(f"Responsaveis: unidade nao encontrada para {email}: {get(d,'unidade')!r}")
            self.con.execute(
                "INSERT INTO usuarios (email,nome,perfil,unidade_padrao_id,territorio,meta,ativo) "
                "VALUES (?,?,?,?,?,?,1) ON CONFLICT(email) DO UPDATE SET nome=excluded.nome,"
                "perfil=excluded.perfil,unidade_padrao_id=excluded.unidade_padrao_id,"
                "territorio=excluded.territorio,meta=excluded.meta,ativo=1",
                (
                    email,
                    parse_text(get(d, "email")),
                    perfil,
                    unidade_id,
                    parse_text(get(d, "territorio")),
                    parse_float(get(d, "meta")) or 0,
                ),
            )

    def import_postos(self, wb) -> None:
        ordem: Counter = Counter()
        for d in sheet_dicts(wb, "Postos"):
            legacy = parse_text(get(d, "id_posto"))
            nome = parse_text(get(d, "posto"))
            unidade_norm = norm_nome(get(d, "unidade"))
            unidade_id = self.unit_ids.get(unidade_norm)
            if not legacy or not nome:
                self.warn(f"Postos: linha ignorada (id={legacy!r}, posto={nome!r})")
                continue
            if not unidade_id:
                self.warn(f"Postos: unidade nao encontrada {get(d,'unidade')!r} (posto {legacy})")
                continue
            ordem[unidade_norm] += 1
            self.con.execute(
                "INSERT INTO postos (legacy_id,unidade_id,nome,ordem,ativo) VALUES (?,?,?,?,1) "
                "ON CONFLICT(legacy_id) DO UPDATE SET unidade_id=excluded.unidade_id,"
                "nome=excluded.nome,ordem=excluded.ordem,ativo=1",
                (legacy, unidade_id, nome, ordem[unidade_norm]),
            )
        for row in self.con.execute("SELECT id,legacy_id FROM postos WHERE legacy_id IS NOT NULL"):
            self.post_ids[row["legacy_id"]] = row["id"]

    def import_insumos(self, wb) -> None:
        ordem: Counter = Counter()
        for d in sheet_dicts(wb, "Insumos"):
            legacy = parse_text(get(d, "id_insumos"))
            tipo = parse_text(get(d, "tipo"))
            desc = parse_text(get(d, "descricao_is"))
            if not legacy or not desc:
                self.warn(f"Insumos: linha ignorada (id={legacy!r}, descricao={desc!r})")
                continue
            ordem[tipo] += 1
            self.con.execute(
                "INSERT INTO insumos (legacy_id,tipo_unidade,subitem,descricao,previsao,ordem,ativo) "
                "VALUES (?,?,?,?,?,?,1) ON CONFLICT(legacy_id) DO UPDATE SET "
                "tipo_unidade=excluded.tipo_unidade,subitem=excluded.subitem,"
                "descricao=excluded.descricao,previsao=excluded.previsao,ordem=excluded.ordem,ativo=1",
                (
                    legacy,
                    tipo,
                    parse_text(get(d, "subitem_is")),
                    desc,
                    parse_float(get(d, "previsao_is")),
                    ordem[tipo],
                ),
            )
        for row in self.con.execute("SELECT id,tipo_unidade,subitem,descricao FROM insumos"):
            key = (norm_nome(row["tipo_unidade"]), norm_nome(row["subitem"]), norm_nome(row["descricao"]))
            self.insumo_ids[key] = row["id"]
            self.insumo_generic[(norm_nome(row["subitem"]), norm_nome(row["descricao"]))].append(row["id"])

    def import_kit(self, wb) -> None:
        ordem: Counter = Counter()
        for d in sheet_dicts(wb, "Operacional"):
            legacy = parse_text(get(d, "id_operacional"))
            tipo = parse_text(get(d, "tipo"))
            desc = parse_text(get(d, "descricao_op"))
            if not legacy or not desc:
                self.warn(f"Operacional: linha ignorada (id={legacy!r}, descricao={desc!r})")
                continue
            ordem[tipo] += 1
            self.con.execute(
                "INSERT INTO kit_operacional (legacy_id,tipo_unidade,subitem,descricao,previsao,ordem,ativo) "
                "VALUES (?,?,?,?,?,?,1) ON CONFLICT(legacy_id) DO UPDATE SET "
                "tipo_unidade=excluded.tipo_unidade,subitem=excluded.subitem,"
                "descricao=excluded.descricao,previsao=excluded.previsao,ordem=excluded.ordem,ativo=1",
                (
                    legacy,
                    tipo,
                    parse_text(get(d, "subitem_op")),
                    desc,
                    parse_float(get(d, "previsao_op")),
                    ordem[tipo],
                ),
            )

    def import_veiculos(self, wb) -> None:
        for d in sheet_dicts(wb, "Veiculos"):
            unidade_id = self.unit_ids.get(norm_nome(get(d, "unidade")))
            nome = parse_text(get(d, "veiculo"))
            if not unidade_id or not nome:
                self.warn(f"Veiculos: ignorado {get(d,'unidade')!r}/{nome!r}")
                continue
            self.con.execute(
                "INSERT INTO veiculos (unidade_id,nome,quantidade) VALUES (?,?,?) "
                "ON CONFLICT(unidade_id,nome) DO UPDATE SET quantidade=excluded.quantidade",
                (unidade_id, nome, parse_float(get(d, "quant_veiculos"))),
            )

    def import_avaliacoes(self, wb) -> None:
        for d in sheet_dicts(wb, "Avaliacao"):
            unidade_id = self.unit_ids.get(norm_nome(get(d, "unidade")))
            criterio = parse_text(get(d, "criterio_avaliacao"))
            mes = parse_mes(get(d, "referencia"))
            if not unidade_id or not criterio or not mes:
                self.warn(f"Avaliacao: ignorado {get(d,'unidade')!r}/{criterio!r}/{get(d,'referencia')!r}")
                continue
            self.con.execute(
                "INSERT INTO avaliacoes_servico (unidade_id,criterio,media,satisfacao,referencia_mes) "
                "VALUES (?,?,?,?,?) ON CONFLICT(unidade_id,criterio,referencia_mes) DO UPDATE SET "
                "media=excluded.media,satisfacao=excluded.satisfacao",
                (
                    unidade_id,
                    criterio,
                    parse_float(get(d, "media")),
                    parse_float(get(d, "satisfacao")),
                    mes,
                ),
            )

    # -- lançamentos -------------------------------------------------------
    def import_lancamentos(self, wb) -> None:
        parecer_by_launch: dict[str, str] = {}
        for d in sheet_dicts(wb, "Parecer_Comissao"):
            lid = parse_text(get(d, "id_lancamento"))
            op = parse_text(get(d, "opcao_parecer"))
            if lid and op:
                parecer_by_launch[lid] = op

        rows = list(sheet_dicts(wb, "Historico_Lancamentos"))
        combos = Counter(
            (norm_nome(get(d, "unidade")), parse_mes(get(d, "referencia_mes")))
            for d in rows
            if parse_text(get(d, "id_lancamento"))
        )

        for d in rows:
            legacy = parse_text(get(d, "id_lancamento"))
            if not legacy:
                continue
            unidade_nome = parse_text(get(d, "unidade"))
            unidade_id = self.unit_ids.get(norm_nome(unidade_nome))
            if not unidade_id:
                self.warn(f"Historico: unidade nao encontrada {unidade_nome!r} (lanc {legacy})")
                continue
            mes = parse_mes(get(d, "referencia_mes"))
            criado = parse_dt(get(d, "data_hora"))
            if not mes and criado:
                mes = criado[:7] + "-01"
            if not mes:
                self.warn(f"Historico: mes invalido para {legacy}")
                continue
            if not criado:
                criado = now_brt()
            tipo = parse_text(get(d, "tipo_unidade"))
            item = parse_text(get(d, "item_contrato"))
            parecer = parecer_by_launch.get(legacy) or parse_text(get(d, "parecer_comissao"))
            flag_dup = 1 if combos[(norm_nome(unidade_nome), mes)] > 1 else 0
            atualizado = parse_dt(get(d, "data_hora_atualizacao"))
            if atualizado and (atualizado.startswith("1970") or atualizado.strip() in ("-", "N/A", "NA", "")):
                atualizado = None
            self.con.execute(
                "INSERT INTO lancamentos (legacy_id,unidade_id,unidade_nome,tipo_unidade,item_contrato,"
                "referencia_mes,autor_email,criado_em,atualizado_em,atualizado_por,parecer_opcao,"
                "parecer_codigo,observacoes,descricao_atividades,analise_atividades,classificacao,"
                "lanches_previsto,lanches_executado,postos_total,postos_ocupados,insumos_percentual,"
                "veiculos_detalhe,duplicado,status,created_at,updated_at) VALUES "
                "(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,'ativo',"
                "datetime('now','localtime'),datetime('now','localtime')) "
                "ON CONFLICT(legacy_id) DO UPDATE SET unidade_id=excluded.unidade_id,"
                "unidade_nome=excluded.unidade_nome,tipo_unidade=excluded.tipo_unidade,"
                "item_contrato=excluded.item_contrato,referencia_mes=excluded.referencia_mes,"
                "autor_email=excluded.autor_email,criado_em=excluded.criado_em,"
                "atualizado_em=excluded.atualizado_em,atualizado_por=excluded.atualizado_por,"
                "parecer_opcao=excluded.parecer_opcao,parecer_codigo=excluded.parecer_codigo,"
                "observacoes=excluded.observacoes,descricao_atividades=excluded.descricao_atividades,"
                "analise_atividades=excluded.analise_atividades,classificacao=excluded.classificacao,"
                "lanches_previsto=excluded.lanches_previsto,lanches_executado=excluded.lanches_executado,"
                "postos_total=excluded.postos_total,postos_ocupados=excluded.postos_ocupados,"
                "insumos_percentual=excluded.insumos_percentual,veiculos_detalhe=excluded.veiculos_detalhe,"
                "duplicado=excluded.duplicado,updated_at=datetime('now','localtime')",
                (
                    legacy,
                    unidade_id,
                    unidade_nome,
                    tipo,
                    item,
                    mes,
                    parse_text(get(d, "email_usuario")).lower(),
                    criado,
                    atualizado,
                    parse_text(get(d, "atualizado_por")) or None,
                    parecer,
                    parecer_codigo(parecer),
                    parse_text(get(d, "observacoes")),
                    parse_text(get(d, "descricao_atividades_metas")),
                    parse_text(get(d, "analise_atividades_realizadas")),
                    normalizar_classificacao(get(d, "classificacao_analise")),
                    parse_float(get(d, "lanches_previsto_mensal")) or 0,
                    parse_float(get(d, "lanches_executado_mensal")),
                    parse_float(get(d, "postos_totais")) or 0,
                    parse_float(get(d, "postos_ocupados")) or 0,
                    parse_float(get(d, "insumos_atingimento_%")),
                    parse_text(get(d, "veiculos_detalhe")),
                    flag_dup,
                ),
            )
            row = self.con.execute("SELECT id FROM lancamentos WHERE legacy_id=?", (legacy,)).fetchone()
            self.launch_ids[legacy] = row["id"]
            self.launch_info[legacy] = {"id": row["id"], "tipo": tipo, "unidade": unidade_nome}

    def _delete_details(self, launch_id: int) -> None:
        for table in (
            "lancamento_postos",
            "lancamento_insumos",
            "lancamento_veiculos",
            "lancamento_lanches",
            "lancamento_kit",
            "lancamento_locacao",
            "avaliacao_central",
        ):
            self.con.execute(f"DELETE FROM {table} WHERE lancamento_id=?", (launch_id,))

    def import_details(self, wb) -> None:
        # garante que os detalhes antigos de cada lançamento sejam substituídos
        for launch_id in self.launch_ids.values():
            self._delete_details(launch_id)

        for d in sheet_dicts(wb, "Ocupacao_Postos"):
            legacy = parse_text(get(d, "id_lancamento"))
            launch = self.launch_ids.get(legacy)
            if not launch:
                self.warn(f"Ocupacao_Postos: lancamento inexistente {legacy}")
                continue
            posto_legacy = parse_text(get(d, "id_posto"))
            posto_id = self.post_ids.get(posto_legacy)
            if posto_legacy and not posto_id:
                self.warn(f"Ocupacao_Postos: posto nao encontrado {posto_legacy} (lanc {legacy})")
            self.con.execute(
                "INSERT INTO lancamento_postos (lancamento_id,posto_id,posto_nome,ocupado,desempenho,licenca_medica) "
                "VALUES (?,?,?,?,?,?)",
                (
                    launch,
                    posto_id,
                    parse_text(get(d, "posto")),
                    parse_bool(get(d, "ocupado")),
                    parse_text(get(d, "desempenho")),
                    parse_text(get(d, "licenca_medica")),
                ),
            )

        for d in sheet_dicts(wb, "Registro_Insumos"):
            legacy = parse_text(get(d, "id_lancamento"))
            info = self.launch_info.get(legacy)
            if not info:
                self.warn(f"Registro_Insumos: lancamento inexistente {legacy}")
                continue
            subitem = parse_text(get(d, "subitem"))
            desc = parse_text(get(d, "descricao"))
            tipo = info.get("tipo") or ""
            insumo_id = self.insumo_ids.get((norm_nome(tipo), norm_nome(subitem), norm_nome(desc)))
            if not insumo_id:
                generic = self.insumo_generic.get((norm_nome(subitem), norm_nome(desc))) or []
                if len(generic) == 1:
                    insumo_id = generic[0]
                else:
                    self.warn(f"Registro_Insumos: insumo nao casado tipo={tipo!r} {subitem!r}/{desc!r}")
            prev = parse_float(get(d, "previsto"))
            exec_ = parse_float(get(d, "executado"))
            ating = parse_float(get(d, "atingimento_%"))
            if ating is None:
                if prev and exec_ is not None:
                    ating = exec_ / prev
                elif exec_:
                    ating = 1.0
                else:
                    ating = 0.0
            self.con.execute(
                "INSERT INTO lancamento_insumos (lancamento_id,insumo_id,subitem,descricao,previsto,executado,atingimento) "
                "VALUES (?,?,?,?,?,?,?)",
                (info["id"], insumo_id, subitem, desc, prev, exec_, ating),
            )

        for d in sheet_dicts(wb, "Registro_Lanches"):
            legacy = parse_text(get(d, "id_lancamento"))
            launch = self.launch_ids.get(legacy)
            if not launch:
                self.warn(f"Registro_Lanches: lancamento inexistente {legacy}")
                continue
            prev = parse_float(get(d, "lanches_previsto_mensal"))
            exec_ = parse_float(get(d, "lanches_executado_mensal"))
            ating = parse_float(get(d, "atingimento_%"))
            if ating is None and prev:
                ating = (exec_ or 0) / prev
            self.con.execute(
                "INSERT INTO lancamento_lanches (lancamento_id,periodo,previsto,executado,atingimento) "
                "VALUES (?,?,?,?,?)",
                (launch, parse_text(get(d, "periodo")) or "Mensal Integral", prev, exec_, ating),
            )

        for d in sheet_dicts(wb, "Composicao_Kit_Nutricionista"):
            legacy = parse_text(get(d, "id_lancamento"))
            launch = self.launch_ids.get(legacy)
            if not launch:
                self.warn(f"Composicao_Kit: lancamento inexistente {legacy}")
                continue
            item = parse_text(get(d, "item_kit"))
            if not item:
                continue
            self.con.execute(
                "INSERT INTO lancamento_kit (lancamento_id,item,quantitativo,conformidade,percentual,obs) "
                "VALUES (?,?,?,?,?,?)",
                (
                    launch,
                    item,
                    parse_float(get(d, "quantitativo_individual")),
                    parse_text(get(d, "conformidade_nutricional")),
                    parse_float(get(d, "percentual_conformidade")),
                    parse_text(get(d, "obs_nutricionista")),
                ),
            )

        for d in sheet_dicts(wb, "Registro_Locacao"):
            legacy = parse_text(get(d, "id_lancamento"))
            launch = self.launch_ids.get(legacy)
            if not launch:
                self.warn(f"Registro_Locacao: lancamento inexistente {legacy}")
                continue
            data_aut = parse_dt(get(d, "data_autorizo"))
            self.con.execute(
                "INSERT INTO lancamento_locacao (lancamento_id,unidade_locacao,dias_corridos,"
                "controle_regularizacao,nota,data_autorizo) VALUES (?,?,?,?,?,?)",
                (
                    launch,
                    parse_text(get(d, "unidade_locacao")),
                    parse_float(get(d, "dias_corridos")),
                    parse_text(get(d, "controle_regularizacao")),
                    parse_text(get(d, "nota")),
                    data_aut[:10] if data_aut else None,
                ),
            )

        for d in sheet_dicts(wb, "Avaliacao_Central"):
            legacy = parse_text(get(d, "id_lancamento"))
            launch = self.launch_ids.get(legacy)
            if not launch:
                self.warn(f"Avaliacao_Central: lancamento inexistente {legacy}")
                continue
            notas = [
                parse_float(get(d, "nota_csimas_cap_contratacao")),
                parse_float(get(d, "nota_csimas_adimplencia")),
                parse_float(get(d, "nota_cop_insumos")),
                parse_float(get(d, "nota_cop_veiculos")),
                parse_float(get(d, "nota_cin_alugueis")),
                parse_float(get(d, "nota_ccpar_prestacao")),
                parse_float(get(d, "nota_ccpar_diligencia")),
                parse_float(get(d, "nota_csimas_ergon")),
                parse_float(get(d, "nota_cop_motoristas")),
                parse_float(get(d, "nota_ccpar_siafic")),
                parse_float(get(d, "nota_ccpar_osinfo")),
            ]
            self.con.execute(
                "INSERT INTO avaliacao_central (lancamento_id,perfil_meta,nota1,nota2,nota3,nota4,"
                "nota5,nota6,nota7,nota8,nota9,nota10,nota11,obs_nutricionista) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                [launch, parse_float(get(d, "perfil_meta"))] + notas +
                [parse_text(get(d, "obs_nutricionista"))],
            )

    # -- reconciliação -----------------------------------------------------
    def counts(self) -> dict[str, int]:
        return {
            "itens_contrato": self.con.execute("SELECT COUNT(*) FROM itens_contrato").fetchone()[0],
            "unidades": self.con.execute("SELECT COUNT(*) FROM unidades").fetchone()[0],
            "usuarios": self.con.execute("SELECT COUNT(*) FROM usuarios").fetchone()[0],
            "postos": self.con.execute("SELECT COUNT(*) FROM postos").fetchone()[0],
            "insumos": self.con.execute("SELECT COUNT(*) FROM insumos").fetchone()[0],
            "kit_operacional": self.con.execute("SELECT COUNT(*) FROM kit_operacional").fetchone()[0],
            "veiculos": self.con.execute("SELECT COUNT(*) FROM veiculos").fetchone()[0],
            "avaliacoes_servico": self.con.execute("SELECT COUNT(*) FROM avaliacoes_servico").fetchone()[0],
            "lancamentos": self.con.execute("SELECT COUNT(*) FROM lancamentos").fetchone()[0],
            "lancamento_postos": self.con.execute("SELECT COUNT(*) FROM lancamento_postos").fetchone()[0],
            "lancamento_insumos": self.con.execute("SELECT COUNT(*) FROM lancamento_insumos").fetchone()[0],
            "lancamento_lanches": self.con.execute("SELECT COUNT(*) FROM lancamento_lanches").fetchone()[0],
            "lancamento_kit": self.con.execute("SELECT COUNT(*) FROM lancamento_kit").fetchone()[0],
            "lancamento_locacao": self.con.execute("SELECT COUNT(*) FROM lancamento_locacao").fetchone()[0],
            "avaliacao_central": self.con.execute("SELECT COUNT(*) FROM avaliacao_central").fetchone()[0],
        }

    def sums(self) -> dict[str, float]:
        row = self.con.execute(
            "SELECT COALESCE(SUM(postos_total),0), COALESCE(SUM(postos_ocupados),0), "
            "COALESCE(SUM(lanches_previsto),0), COALESCE(SUM(lanches_executado),0) "
            "FROM lancamentos WHERE status='ativo'"
        ).fetchone()
        return {
            "postos_total": float(row[0] or 0),
            "postos_ocupados": float(row[1] or 0),
            "lanches_previsto": float(row[2] or 0),
            "lanches_executado": float(row[3] or 0),
        }


def source_count(wb, name: str) -> int:
    ws = wb[name]
    n = 0
    for i, row in enumerate(ws.iter_rows(values_only=True)):
        if i == 0:
            continue
        if any(v not in (None, "") for v in row):
            n += 1
    return n


def source_sums(wb) -> dict[str, float]:
    totals = defaultdict(float)
    for d in sheet_dicts(wb, "Historico_Lancamentos"):
        if not parse_text(get(d, "id_lancamento")):
            continue
        for key, col in (
            ("postos_total", "postos_totais"),
            ("postos_ocupados", "postos_ocupados"),
            ("lanches_previsto", "lanches_previsto_mensal"),
            ("lanches_executado", "lanches_executado_mensal"),
        ):
            totals[key] += parse_float(get(d, col)) or 0
    return dict(totals)


def reconcile(wb, mig: Migration) -> str:
    lines = ["# Relatório de migração — SIGPAR", "", f"Gerado em: {now_brt()} (America/Sao_Paulo)", ""]
    lines.append("## Contagens")
    lines.append("")
    lines.append("| Origem | Planilha | SQLite |")
    lines.append("|---|---:|---:|")
    target = mig.counts()
    pairs = [
        ("Item", "itens_contrato"),
        ("Unidades", "unidades"),
        ("Responsaveis", "usuarios"),
        ("Postos", "postos"),
        ("Insumos", "insumos"),
        ("Operacional", "kit_operacional"),
        ("Veiculos", "veiculos"),
        ("Avaliacao", "avaliacoes_servico"),
        ("Historico_Lancamentos", "lancamentos"),
        ("Ocupacao_Postos", "lancamento_postos"),
        ("Registro_Insumos", "lancamento_insumos"),
        ("Registro_Lanches", "lancamento_lanches"),
        ("Composicao_Kit_Nutricionista", "lancamento_kit"),
        ("Registro_Locacao", "lancamento_locacao"),
        ("Avaliacao_Central", "avaliacao_central"),
    ]
    for src, dst in pairs:
        s = source_count(wb, src)
        t = target.get(dst, 0)
        mark = "" if s == t else " ⚠"
        lines.append(f"| {src} | {s} | {t}{mark} |")
    lines.append("")
    lines.append("## Somas do histórico")
    lines.append("")
    lines.append("| Campo | Planilha | SQLite |")
    lines.append("|---|---:|---:|")
    ss = source_sums(wb)
    ts = mig.sums()
    for key in ("postos_total", "postos_ocupados", "lanches_previsto", "lanches_executado"):
        lines.append(f"| {key} | {ss.get(key,0):.2f} | {ts.get(key,0):.2f} |")
    lines.append("")
    lines.append("## Notas")
    lines.append("")
    lines.append("- `usuarios` inclui 2 admins técnicos além dos 94 e-mails únicos da planilha.")
    lines.append("- `lancamento_veiculos` fica vazio por design: o histórico usa o texto `veiculos_detalhe` (a planilha não tem detalhe por veículo).")
    lines.append("- A linha 21 de `Operacional` (ID repetido, descrição vazia) é ignorada; ver avisos.")
    lines.append("")
    lines.append("## Avisos")
    lines.append("")
    if mig.warnings:
        for w in mig.warnings[:200]:
            lines.append(f"- {w}")
        if len(mig.warnings) > 200:
            lines.append(f"- ... e mais {len(mig.warnings)-200} avisos")
    else:
        lines.append("- nenhum")
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--xlsx")
    ap.add_argument("--drive-id", default=DRIVE_ID)
    ap.add_argument("--token")
    ap.add_argument("--db", default=str(DEFAULT_DB))
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--report", default=str(ROOT / "docs" / "migracao-relatorio.md"))
    args = ap.parse_args()

    if args.xlsx:
        wb = load_workbook(Path(args.xlsx), read_only=True, data_only=True)
    elif args.token:
        if not args.drive_id:
            print("informe --drive-id ou SIGPAR_SOURCE_SHEET_ID", file=sys.stderr)
            return 2
        wb = load_workbook_from_drive(args.drive_id, args.token)
    else:
        print("informe --xlsx ou --token", file=sys.stderr)
        return 2

    if not args.write:
        print("DRY-RUN (nada será gravado)")
        print("contagens na planilha:")
        for name in EXPECTED_ROWS:
            print(f"  {name:35s} {source_count(wb, name):6d}")
        print("somas:", source_sums(wb))
        return 0

    db_path = Path(args.db)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    con.executescript(SCHEMA.read_text(encoding="utf-8"))
    con.commit()

    mig = Migration(con)
    try:
        con.execute("BEGIN")
        mig.import_items(wb)
        mig.import_units(wb)
        mig.import_users(wb)
        mig.import_postos(wb)
        mig.import_insumos(wb)
        mig.import_kit(wb)
        mig.import_veiculos(wb)
        mig.import_avaliacoes(wb)
        mig.import_lancamentos(wb)
        mig.import_details(wb)
        con.execute(
            "INSERT INTO audit_log (ator_email,acao,entidade,entidade_id,depois_json) "
            "VALUES (?,?,?,?,?)",
            (
                "migracao",
                "migracao_inicial",
                "sistema",
                "sheet",
                json.dumps(mig.counts(), ensure_ascii=False),
            ),
        )
        con.commit()
    except Exception as exc:  # noqa: BLE001
        con.rollback()
        print(f"ERRO na migração: {type(exc).__name__}: {exc}", file=sys.stderr)
        con.close()
        return 1

    report = reconcile(wb, mig)
    Path(args.report).write_text(report, encoding="utf-8")
    print(report)
    print(f"relatório: {args.report}")
    con.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
