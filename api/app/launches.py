from __future__ import annotations

import json
import re
import secrets
import sqlite3
import time
from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, Field

from .auth import get_current_user
from .db import connect
from .pdf import render_pdf
from .permissions import exigir_unidade, get_usuario_ativo, unidades_ids

router = APIRouter()


def now_brt() -> str:
    return datetime.now(ZoneInfo("America/Sao_Paulo")).strftime("%Y-%m-%d %H:%M:%S")


def normalizar_mes(value: str) -> str:
    text = str(value or "").strip()
    if re.fullmatch(r"\d{4}-\d{2}", text):
        text += "-01"
    if not re.fullmatch(r"\d{4}-\d{2}-01", text):
        raise HTTPException(status_code=422, detail="referencia_mes deve ser YYYY-MM ou YYYY-MM-01")
    return text


def parecer_codigo(value: str) -> str:
    text = (value or "").upper()
    if "COM RESSALVA" in text:
        return "atestar_ressalva"
    if "NÃO ATESTAR" in text or "NAO ATESTAR" in text:
        return "nao_atestar"
    if "ATESTAR" in text:
        return "atestar"
    return ""


def usuario_atual(user: dict = Depends(get_current_user)) -> dict:
    return get_usuario_ativo(user["email"])


# ---------------------------------------------------------------------------
# Modelos
# ---------------------------------------------------------------------------

class PostoIn(BaseModel):
    posto_id: int
    ocupado: bool = False
    desempenho: str | None = None
    licenca_medica: str | None = None


class InsumoIn(BaseModel):
    insumo_id: int
    previsto: float | None = None
    executado: float | None = None


class VeiculoIn(BaseModel):
    veiculo_id: int
    previsto: float | None = None
    executado: float | None = None


class KitIn(BaseModel):
    item: str
    quantitativo: float | None = None
    conformidade: str | None = None
    percentual: float | None = None
    obs: str | None = None


class LocacaoIn(BaseModel):
    unidade_locacao: str | None = None
    dias_corridos: float | None = None
    controle_regularizacao: str | None = None
    nota: str | None = None
    data_autorizo: str | None = None


class AvaliacaoCentralIn(BaseModel):
    perfil_meta: float | None = None
    nota1: float | None = None
    nota2: float | None = None
    nota3: float | None = None
    nota4: float | None = None
    nota5: float | None = None
    nota6: float | None = None
    nota7: float | None = None
    nota8: float | None = None
    nota9: float | None = None
    nota10: float | None = None
    nota11: float | None = None
    obs_nutricionista: str | None = None


class LancamentoIn(BaseModel):
    unidade_id: int
    referencia_mes: str
    tem_lanches: bool = False
    lanches_previsto: float = 0
    lanches_executado: float | None = None
    parecer_opcao: str = ""
    observacoes: str = ""
    descricao_atividades: str = ""
    analise_atividades: str = ""
    classificacao: str = ""
    detalhe_postos: list[PostoIn] = Field(default_factory=list)
    detalhe_insumos: list[InsumoIn] = Field(default_factory=list)
    detalhe_veiculos: list[VeiculoIn] = Field(default_factory=list)
    composicao_kit: list[KitIn] = Field(default_factory=list)
    locacao: list[LocacaoIn] = Field(default_factory=list)
    avaliacao_central: AvaliacaoCentralIn | None = None
    confirmar_duplicado: bool = False


# ---------------------------------------------------------------------------
# Helpers de banco
# ---------------------------------------------------------------------------

def _unidade(con: sqlite3.Connection, unidade_id: int) -> dict:
    row = con.execute(
        "SELECT u.*, i.id AS item_ref_id, i.codigo AS item_codigo, i.instituicao, i.cnpj, "
        "i.instrumento, i.objeto, i.vigencia_inicio, i.vigencia_fim, i.processo_instrutivo "
        "FROM unidades u LEFT JOIN itens_contrato i ON i.id = u.item_id "
        "WHERE u.id = ? AND u.ativo = 1",
        (unidade_id,),
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="unidade nao encontrada")
    return dict(row)


def _duplicados(
    con: sqlite3.Connection, unidade_id: int, mes: str, excluir_id: int | None = None
) -> list[dict]:
    sql = (
        "SELECT id, legacy_id, criado_em, autor_email FROM lancamentos "
        "WHERE unidade_id = ? AND referencia_mes = ? AND status = 'ativo'"
    )
    params: list = [unidade_id, mes]
    if excluir_id is not None:
        sql += " AND id <> ?"
        params.append(excluir_id)
    sql += " ORDER BY id"
    return [dict(r) for r in con.execute(sql, params).fetchall()]


def _contexto_ids(
    con: sqlite3.Connection, unidade: dict
) -> tuple[dict[int, dict], dict[int, dict], dict[int, dict]]:
    postos = {
        r["id"]: dict(r)
        for r in con.execute(
            "SELECT id, nome FROM postos WHERE unidade_id = ? AND ativo = 1", (unidade["id"],)
        ).fetchall()
    }
    insumos = {
        r["id"]: dict(r)
        for r in con.execute(
            "SELECT id, subitem, descricao FROM insumos WHERE tipo_unidade = ? AND ativo = 1",
            (unidade["tipo"],),
        ).fetchall()
    }
    veiculos = {
        r["id"]: dict(r)
        for r in con.execute(
            "SELECT id, nome FROM veiculos WHERE unidade_id = ?", (unidade["id"],)
        ).fetchall()
    }
    return postos, insumos, veiculos


def _validar_payload(
    con: sqlite3.Connection, unidade: dict, payload: LancamentoIn
) -> dict:
    postos, insumos, veiculos = _contexto_ids(con, unidade)

    for p in payload.detalhe_postos:
        if p.posto_id not in postos:
            raise HTTPException(
                status_code=422,
                detail=f"posto {p.posto_id} nao pertence a unidade {unidade['nome']}",
            )
    for i in payload.detalhe_insumos:
        if i.insumo_id not in insumos:
            raise HTTPException(
                status_code=422,
                detail=f"insumo {i.insumo_id} nao pertence ao tipo {unidade['tipo']}",
            )
    for v in payload.detalhe_veiculos:
        if v.veiculo_id not in veiculos:
            raise HTTPException(
                status_code=422,
                detail=f"veiculo {v.veiculo_id} nao pertence a unidade {unidade['nome']}",
            )

    central = unidade["nome_norm"] == "nível central"
    if (payload.locacao or payload.avaliacao_central) and not central:
        raise HTTPException(
            status_code=422,
            detail="locacao/avaliacao central so se aplicam a NÍVEL CENTRAL",
        )

    return {"postos": postos, "insumos": insumos, "veiculos": veiculos}


def _calcular(payload: LancamentoIn, unidade: dict, mapas: dict) -> dict:
    postos_total = len(payload.detalhe_postos)
    postos_ocupados = sum(1 for p in payload.detalhe_postos if p.ocupado)

    pcts: list[float] = []
    for i in payload.detalhe_insumos:
        prev = i.previsto or 0
        exec_ = i.executado or 0
        if prev > 0:
            pcts.append(exec_ / prev)
        elif exec_ > 0:
            pcts.append(1.0)
        else:
            pcts.append(0.0)
    insumos_pct = (sum(pcts) / len(pcts)) if pcts else None

    detalhes_veic = []
    for v in payload.detalhe_veiculos:
        nome = (mapas["veiculos"].get(v.veiculo_id) or {}).get("nome", f"Veículo {v.veiculo_id}")
        detalhes_veic.append(f"{nome}: Exec {v.executado or 0}/{v.previsto or 0}")
    veiculos_detalhe = " | ".join(detalhes_veic) if detalhes_veic else "N/A"

    lanches_prev = payload.lanches_previsto if payload.tem_lanches else 0
    lanches_exec = payload.lanches_executado if payload.tem_lanches else None

    return {
        "postos_total": postos_total,
        "postos_ocupados": postos_ocupados,
        "insumos_percentual": insumos_pct,
        "veiculos_detalhe": veiculos_detalhe,
        "lanches_previsto": lanches_prev or 0,
        "lanches_executado": lanches_exec,
        "parecer_codigo": parecer_codigo(payload.parecer_opcao),
    }


def _inserir_detalhes(
    con: sqlite3.Connection,
    launch_id: int,
    payload: LancamentoIn,
    mapas: dict,
    unidade: dict,
    pode_saude: bool = False,
    existing_health: dict[int, str] | None = None,
) -> None:
    for p in payload.detalhe_postos:
        posto = mapas["postos"].get(p.posto_id) or {}
        if pode_saude:
            licenca = p.licenca_medica if p.ocupado else None
        else:
            licenca = (existing_health or {}).get(p.posto_id) if p.ocupado else None
        con.execute(
            "INSERT INTO lancamento_postos (lancamento_id,posto_id,posto_nome,ocupado,desempenho,licenca_medica) "
            "VALUES (?,?,?,?,?,?)",
            (
                launch_id,
                p.posto_id,
                posto.get("nome"),
                1 if p.ocupado else 0,
                p.desempenho if p.ocupado else None,
                licenca,
            ),
        )

    for i in payload.detalhe_insumos:
        ins = mapas["insumos"].get(i.insumo_id) or {}
        prev = i.previsto or 0
        exec_ = i.executado or 0
        if prev > 0:
            ating = exec_ / prev
        elif exec_ > 0:
            ating = 1.0
        else:
            ating = 0.0
        con.execute(
            "INSERT INTO lancamento_insumos (lancamento_id,insumo_id,subitem,descricao,previsto,executado,atingimento) "
            "VALUES (?,?,?,?,?,?,?)",
            (launch_id, i.insumo_id, ins.get("subitem"), ins.get("descricao"), prev, exec_, ating),
        )

    for v in payload.detalhe_veiculos:
        veic = mapas["veiculos"].get(v.veiculo_id) or {}
        con.execute(
            "INSERT INTO lancamento_veiculos (lancamento_id,veiculo_id,nome,previsto,executado) "
            "VALUES (?,?,?,?,?)",
            (launch_id, v.veiculo_id, veic.get("nome"), v.previsto, v.executado),
        )

    if payload.tem_lanches:
        prev = payload.lanches_previsto or 0
        exec_ = payload.lanches_executado or 0
        ating = (exec_ / prev) if prev > 0 else (1.0 if exec_ > 0 else 0.0)
        con.execute(
            "INSERT INTO lancamento_lanches (lancamento_id,periodo,previsto,executado,atingimento) "
            "VALUES (?,?,?,?,?)",
            (launch_id, "Mensal Integral", prev, exec_, ating),
        )
        for k in payload.composicao_kit:
            con.execute(
                "INSERT INTO lancamento_kit (lancamento_id,item,quantitativo,conformidade,percentual,obs) "
                "VALUES (?,?,?,?,?,?)",
                (launch_id, k.item, k.quantitativo, k.conformidade, k.percentual, k.obs),
            )

    if unidade["nome_norm"] == "nível central":
        for loc in payload.locacao:
            con.execute(
                "INSERT INTO lancamento_locacao (lancamento_id,unidade_locacao,dias_corridos,"
                "controle_regularizacao,nota,data_autorizo) VALUES (?,?,?,?,?,?)",
                (
                    launch_id,
                    loc.unidade_locacao,
                    loc.dias_corridos,
                    loc.controle_regularizacao,
                    loc.nota,
                    loc.data_autorizo,
                ),
            )
        av = payload.avaliacao_central
        if av is not None:
            con.execute(
                "INSERT INTO avaliacao_central (lancamento_id,perfil_meta,nota1,nota2,nota3,nota4,"
                "nota5,nota6,nota7,nota8,nota9,nota10,nota11,obs_nutricionista) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    launch_id,
                    av.perfil_meta,
                    av.nota1,
                    av.nota2,
                    av.nota3,
                    av.nota4,
                    av.nota5,
                    av.nota6,
                    av.nota7,
                    av.nota8,
                    av.nota9,
                    av.nota10,
                    av.nota11,
                    av.obs_nutricionista,
                ),
            )


def _deletar_detalhes(con: sqlite3.Connection, launch_id: int) -> None:
    for table in (
        "lancamento_postos",
        "lancamento_insumos",
        "lancamento_veiculos",
        "lancamento_lanches",
        "lancamento_kit",
        "lancamento_locacao",
        "avaliacao_central",
    ):
        con.execute(f"DELETE FROM {table} WHERE lancamento_id = ?", (launch_id,))


def _audit(
    con: sqlite3.Connection,
    ator: str,
    acao: str,
    entidade_id: str,
    antes: dict | None,
    depois: dict | None,
) -> None:
    con.execute(
        "INSERT INTO audit_log (ator_email,acao,entidade,entidade_id,antes_json,depois_json) "
        "VALUES (?,?,?,?,?,?)",
        (
            ator,
            acao,
            "lancamento",
            entidade_id,
            json.dumps(antes, ensure_ascii=False, default=str) if antes else None,
            json.dumps(depois, ensure_ascii=False, default=str) if depois else None,
        ),
    )


def _novo_legacy_id(con: sqlite3.Connection) -> str:
    for _ in range(5):
        candidate = f"LANC-{int(time.time() * 1000)}"
        if not con.execute("SELECT 1 FROM lancamentos WHERE legacy_id = ?", (candidate,)).fetchone():
            return candidate
        time.sleep(0.002)
    return f"LANC-{int(time.time() * 1000)}-{secrets.randbelow(900) + 100}"


def _carregar_completo(
    con: sqlite3.Connection, launch_id: int, mask_health: bool = False
) -> dict:
    row = con.execute(
        "SELECT * FROM lancamentos WHERE id = ? AND status = 'ativo'", (launch_id,)
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="lancamento nao encontrado")
    lanc = dict(row)
    unidade = _unidade(con, lanc["unidade_id"])
    item = None
    if unidade.get("item_ref_id"):
        item = {
            "id": unidade["item_ref_id"],
            "codigo": unidade.get("item_codigo"),
            "instituicao": unidade.get("instituicao"),
            "cnpj": unidade.get("cnpj"),
            "instrumento": unidade.get("instrumento"),
            "objeto": unidade.get("objeto"),
            "vigencia_inicio": unidade.get("vigencia_inicio"),
            "vigencia_fim": unidade.get("vigencia_fim"),
            "processo_instrutivo": unidade.get("processo_instrutivo"),
        }
    autor = con.execute(
        "SELECT perfil, nome FROM usuarios WHERE email = ?", (lanc["autor_email"].lower(),)
    ).fetchone()
    postos = [
        dict(r)
        for r in con.execute(
            "SELECT posto_id, posto_nome, ocupado, desempenho, licenca_medica "
            "FROM lancamento_postos WHERE lancamento_id = ? ORDER BY id",
            (launch_id,),
        ).fetchall()
    ]
    if mask_health:
        for posto in postos:
            posto["licenca_medica"] = "Restrito" if posto.get("licenca_medica") else None
    insumos = [
        dict(r)
        for r in con.execute(
            "SELECT insumo_id, subitem, descricao, previsto, executado, atingimento "
            "FROM lancamento_insumos WHERE lancamento_id = ? ORDER BY id",
            (launch_id,),
        ).fetchall()
    ]
    veiculos = [
        dict(r)
        for r in con.execute(
            "SELECT veiculo_id, nome, previsto, executado FROM lancamento_veiculos "
            "WHERE lancamento_id = ? ORDER BY id",
            (launch_id,),
        ).fetchall()
    ]
    lanches = [
        dict(r)
        for r in con.execute(
            "SELECT periodo, previsto, executado, atingimento FROM lancamento_lanches "
            "WHERE lancamento_id = ? ORDER BY id",
            (launch_id,),
        ).fetchall()
    ]
    kit = [
        dict(r)
        for r in con.execute(
            "SELECT item, quantitativo, conformidade, percentual, obs FROM lancamento_kit "
            "WHERE lancamento_id = ? ORDER BY id",
            (launch_id,),
        ).fetchall()
    ]
    locacao = [
        dict(r)
        for r in con.execute(
            "SELECT unidade_locacao, dias_corridos, controle_regularizacao, nota, data_autorizo "
            "FROM lancamento_locacao WHERE lancamento_id = ? ORDER BY id",
            (launch_id,),
        ).fetchall()
    ]
    av = con.execute(
        "SELECT * FROM avaliacao_central WHERE lancamento_id = ?", (launch_id,)
    ).fetchone()
    avaliacao = dict(av) if av else None
    if avaliacao:
        avaliacao.pop("lancamento_id", None)

    return {
        "lancamento": lanc,
        "unidade": unidade,
        "item": item,
        "autor_perfil": (autor["perfil"] if autor else "Usuário"),
        "postos": postos,
        "insumos": insumos,
        "veiculos": veiculos,
        "lanches": lanches,
        "kit": kit,
        "locacao": locacao,
        "avaliacao_central": avaliacao,
    }


# ---------------------------------------------------------------------------
# Rotas
# ---------------------------------------------------------------------------

@router.get("/unidades")
def listar_unidades(usuario: dict = Depends(usuario_atual)) -> list[dict]:
    con = connect()
    try:
        ids = unidades_ids(usuario["email"])
        if not ids:
            return []
        marks = ",".join("?" for _ in ids)
        rows = con.execute(
            f"SELECT id, nome, tipo, territorio, postos_previstos, lanches_previstos, aluguel "
            f"FROM unidades WHERE id IN ({marks}) AND ativo = 1 ORDER BY nome",
            ids,
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        con.close()


@router.get("/unidades/{unidade_id}/contexto")
def contexto(unidade_id: int, usuario: dict = Depends(usuario_atual)) -> dict:
    exigir_unidade(usuario["email"], unidade_id)
    con = connect()
    try:
        unidade = _unidade(con, unidade_id)
        item = None
        if unidade.get("item_ref_id"):
            item = {
                "codigo": unidade.get("item_codigo"),
                "instituicao": unidade.get("instituicao"),
                "cnpj": unidade.get("cnpj"),
                "instrumento": unidade.get("instrumento"),
                "objeto": unidade.get("objeto"),
                "vigencia_inicio": unidade.get("vigencia_inicio"),
                "vigencia_fim": unidade.get("vigencia_fim"),
                "processo_instrutivo": unidade.get("processo_instrutivo"),
            }
        postos = [
            dict(r)
            for r in con.execute(
                "SELECT id, nome, ordem FROM postos WHERE unidade_id = ? AND ativo = 1 "
                "ORDER BY ordem, id",
                (unidade_id,),
            ).fetchall()
        ]
        insumos = [
            dict(r)
            for r in con.execute(
                "SELECT id, subitem, descricao, previsao FROM insumos "
                "WHERE tipo_unidade = ? AND ativo = 1 ORDER BY ordem, id",
                (unidade["tipo"],),
            ).fetchall()
        ]
        kit = [
            dict(r)
            for r in con.execute(
                "SELECT id, subitem, descricao, previsao FROM kit_operacional "
                "WHERE tipo_unidade = ? AND ativo = 1 ORDER BY ordem, id",
                (unidade["tipo"],),
            ).fetchall()
        ]
        veiculos = [
            dict(r)
            for r in con.execute(
                "SELECT id, nome, quantidade FROM veiculos WHERE unidade_id = ? ORDER BY nome",
                (unidade_id,),
            ).fetchall()
        ]
        avaliacoes = [
            dict(r)
            for r in con.execute(
                "SELECT criterio, media, satisfacao, referencia_mes FROM avaliacoes_servico "
                "WHERE unidade_id = ? ORDER BY referencia_mes DESC, criterio",
                (unidade_id,),
            ).fetchall()
        ]
        central = unidade["nome_norm"] == "nível central" and usuario["perfil"] == "admin"
        aluguel = []
        if central:
            aluguel = [
                dict(r)
                for r in con.execute(
                    "SELECT id, nome FROM unidades WHERE aluguel = 1 AND ativo = 1 ORDER BY nome"
                ).fetchall()
            ]
        return {
            "unidade": {
                "id": unidade["id"],
                "nome": unidade["nome"],
                "tipo": unidade["tipo"],
                "territorio": unidade["territorio"],
                "postos_previstos": unidade["postos_previstos"],
                "lanches_previstos": unidade["lanches_previstos"],
                "aluguel": unidade["aluguel"],
            },
            "item": item,
            "postos": postos,
            "insumos": insumos,
            "kit": kit,
            "veiculos": veiculos,
            "avaliacoes_servico": avaliacoes,
            "pode_central": central,
            "unidades_aluguel": aluguel,
        }
    finally:
        con.close()


@router.get("/lancamentos")
def listar_lancamentos(
    id_lancamento: str | None = Query(default=None),
    unidade_id: int | None = Query(default=None),
    mes: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    usuario: dict = Depends(usuario_atual),
) -> list[dict]:
    permitidas = set(unidades_ids(usuario["email"]))
    if unidade_id is not None and unidade_id not in permitidas:
        raise HTTPException(status_code=403, detail="sem permissao para a unidade")
    con = connect()
    try:
        sql = (
            "SELECT id, legacy_id, unidade_id, unidade_nome, referencia_mes, autor_email, "
            "criado_em, atualizado_em, duplicado, parecer_codigo, parecer_opcao, "
            "postos_total, postos_ocupados, lanches_previsto, lanches_executado, "
            "insumos_percentual, classificacao "
            "FROM lancamentos WHERE status = 'ativo'"
        )
        params: list = []
        if id_lancamento:
            sql += " AND (legacy_id = ? OR CAST(id AS TEXT) = ?)"
            params.extend([id_lancamento.strip(), id_lancamento.strip()])
        if unidade_id is not None:
            sql += " AND unidade_id = ?"
            params.append(unidade_id)
        if mes:
            sql += " AND referencia_mes = ?"
            params.append(normalizar_mes(mes))
        if not usuario["perfil"] == "admin":
            if not permitidas:
                return []
            marks = ",".join("?" for _ in permitidas)
            sql += f" AND unidade_id IN ({marks})"
            params.extend(sorted(permitidas))
        sql += " ORDER BY criado_em DESC, id DESC LIMIT ?"
        params.append(limit)
        return [dict(r) for r in con.execute(sql, params).fetchall()]
    finally:
        con.close()


@router.get("/lancamentos/{lancamento_id}")
def detalhar_lancamento(
    lancamento_id: int, usuario: dict = Depends(usuario_atual)
) -> dict:
    con = connect()
    try:
        row = con.execute(
            "SELECT unidade_id FROM lancamentos WHERE id = ? AND status = 'ativo'",
            (lancamento_id,),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="lancamento nao encontrado")
        exigir_unidade(usuario["email"], row["unidade_id"])
        return _carregar_completo(
            con, lancamento_id, mask_health=usuario["perfil"] != "admin"
        )
    finally:
        con.close()


@router.post("/lancamentos")
def criar_lancamento(
    payload: LancamentoIn, usuario: dict = Depends(usuario_atual)
) -> dict:
    exigir_unidade(usuario["email"], payload.unidade_id)
    mes = normalizar_mes(payload.referencia_mes)
    con = connect()
    try:
        unidade = _unidade(con, payload.unidade_id)
        if unidade["nome_norm"] == "nível central" and usuario["perfil"] != "admin":
            raise HTTPException(status_code=403, detail="NÍVEL CENTRAL exige perfil admin")
        mapas = _validar_payload(con, unidade, payload)
        duplicados = _duplicados(con, payload.unidade_id, mes)
        if duplicados and not payload.confirmar_duplicado:
            raise HTTPException(
                status_code=409,
                detail={
                    "mensagem": "Ja existe lancamento para esta unidade e mes.",
                    "existentes": duplicados,
                },
            )
        calc = _calcular(payload, unidade, mapas)
        legacy = _novo_legacy_id(con)
        now = now_brt()
        cur = con.execute(
            "INSERT INTO lancamentos (legacy_id,unidade_id,unidade_nome,tipo_unidade,item_contrato,"
            "referencia_mes,autor_email,criado_em,atualizado_em,atualizado_por,parecer_opcao,"
            "parecer_codigo,observacoes,descricao_atividades,analise_atividades,classificacao,"
            "lanches_previsto,lanches_executado,postos_total,postos_ocupados,insumos_percentual,"
            "veiculos_detalhe,duplicado,status,created_at,updated_at) VALUES "
            "(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,'ativo',?,?)",
            (
                legacy,
                payload.unidade_id,
                unidade["nome"],
                unidade["tipo"],
                unidade.get("item_codigo"),
                mes,
                usuario["email"],
                now,
                None,
                None,
                payload.parecer_opcao,
                calc["parecer_codigo"],
                payload.observacoes,
                payload.descricao_atividades,
                payload.analise_atividades,
                payload.classificacao,
                calc["lanches_previsto"],
                calc["lanches_executado"],
                calc["postos_total"],
                calc["postos_ocupados"],
                calc["insumos_percentual"],
                calc["veiculos_detalhe"],
                1 if duplicados else 0,
                now,
                now,
            ),
        )
        launch_id = cur.lastrowid
        _inserir_detalhes(
            con,
            launch_id,
            payload,
            mapas,
            unidade,
            pode_saude=usuario["perfil"] == "admin",
        )
        _audit(
            con,
            usuario["email"],
            "criar",
            str(launch_id),
            None,
            {"legacy_id": legacy, "unidade_id": payload.unidade_id, "referencia_mes": mes},
        )
        con.commit()
        return {
            "id": launch_id,
            "legacy_id": legacy,
            "duplicado": bool(duplicados),
            "pdf_url": f"/lancamentos/{launch_id}/pdf",
        }
    except HTTPException:
        con.rollback()
        raise
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


@router.put("/lancamentos/{lancamento_id}")
def editar_lancamento(
    lancamento_id: int, payload: LancamentoIn, usuario: dict = Depends(usuario_atual)
) -> dict:
    con = connect()
    try:
        existente = con.execute(
            "SELECT * FROM lancamentos WHERE id = ? AND status = 'ativo'", (lancamento_id,)
        ).fetchone()
        if not existente:
            raise HTTPException(status_code=404, detail="lancamento nao encontrado")
        exigir_unidade(usuario["email"], existente["unidade_id"])
        exigir_unidade(usuario["email"], payload.unidade_id)
        mes = normalizar_mes(payload.referencia_mes)
        unidade = _unidade(con, payload.unidade_id)
        if unidade["nome_norm"] == "nível central" and usuario["perfil"] != "admin":
            raise HTTPException(status_code=403, detail="NÍVEL CENTRAL exige perfil admin")
        mapas = _validar_payload(con, unidade, payload)
        duplicados = _duplicados(con, payload.unidade_id, mes, excluir_id=lancamento_id)
        if duplicados and not payload.confirmar_duplicado:
            raise HTTPException(
                status_code=409,
                detail={
                    "mensagem": "Ja existe outro lancamento para esta unidade e mes.",
                    "existentes": duplicados,
                },
            )
        calc = _calcular(payload, unidade, mapas)
        now = now_brt()
        con.execute(
            "UPDATE lancamentos SET unidade_id=?, unidade_nome=?, tipo_unidade=?, item_contrato=?, "
            "referencia_mes=?, atualizado_em=?, atualizado_por=?, parecer_opcao=?, parecer_codigo=?, "
            "observacoes=?, descricao_atividades=?, analise_atividades=?, classificacao=?, "
            "lanches_previsto=?, lanches_executado=?, postos_total=?, postos_ocupados=?, "
            "insumos_percentual=?, veiculos_detalhe=?, duplicado=?, updated_at=? WHERE id=?",
            (
                payload.unidade_id,
                unidade["nome"],
                unidade["tipo"],
                unidade.get("item_codigo"),
                mes,
                now,
                usuario["email"],
                payload.parecer_opcao,
                calc["parecer_codigo"],
                payload.observacoes,
                payload.descricao_atividades,
                payload.analise_atividades,
                payload.classificacao,
                calc["lanches_previsto"],
                calc["lanches_executado"],
                calc["postos_total"],
                calc["postos_ocupados"],
                calc["insumos_percentual"],
                calc["veiculos_detalhe"],
                1 if duplicados else 0,
                now,
                lancamento_id,
            ),
        )
        existing_health = {
            r["posto_id"]: r["licenca_medica"]
            for r in con.execute(
                "SELECT posto_id, licenca_medica FROM lancamento_postos WHERE lancamento_id = ?",
                (lancamento_id,),
            ).fetchall()
            if r["posto_id"] is not None
        }
        _deletar_detalhes(con, lancamento_id)
        _inserir_detalhes(
            con,
            lancamento_id,
            payload,
            mapas,
            unidade,
            pode_saude=usuario["perfil"] == "admin",
            existing_health=existing_health,
        )
        _audit(
            con,
            usuario["email"],
            "editar",
            str(lancamento_id),
            {"unidade_id": existente["unidade_id"], "referencia_mes": existente["referencia_mes"]},
            {"unidade_id": payload.unidade_id, "referencia_mes": mes},
        )
        con.commit()
        return {
            "id": lancamento_id,
            "legacy_id": existente["legacy_id"],
            "duplicado": bool(duplicados),
            "pdf_url": f"/lancamentos/{lancamento_id}/pdf",
        }
    except HTTPException:
        con.rollback()
        raise
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


@router.delete("/lancamentos/{lancamento_id}")
def excluir_lancamento(
    lancamento_id: int, usuario: dict = Depends(usuario_atual)
) -> dict:
    if usuario["perfil"] != "admin":
        raise HTTPException(status_code=403, detail="apenas admin pode excluir")
    con = connect()
    try:
        row = con.execute(
            "SELECT unidade_id, legacy_id FROM lancamentos WHERE id = ? AND status = 'ativo'",
            (lancamento_id,),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="lancamento nao encontrado")
        now = now_brt()
        con.execute(
            "UPDATE lancamentos SET status='excluido', atualizado_em=?, atualizado_por=?, "
            "updated_at=? WHERE id=?",
            (now, usuario["email"], now, lancamento_id),
        )
        _audit(
            con,
            usuario["email"],
            "excluir",
            str(lancamento_id),
            {"legacy_id": row["legacy_id"], "unidade_id": row["unidade_id"]},
            {"status": "excluido"},
        )
        con.commit()
        return {"ok": True}
    finally:
        con.close()


@router.get("/lancamentos/{lancamento_id}/pdf")
def pdf_lancamento(
    lancamento_id: int, usuario: dict = Depends(usuario_atual)
) -> Response:
    con = connect()
    try:
        row = con.execute(
            "SELECT unidade_id, legacy_id FROM lancamentos WHERE id = ? AND status = 'ativo'",
            (lancamento_id,),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="lancamento nao encontrado")
        exigir_unidade(usuario["email"], row["unidade_id"])
        data = _carregar_completo(
            con, lancamento_id, mask_health=usuario["perfil"] != "admin"
        )
    finally:
        con.close()
    try:
        pdf = render_pdf(data)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"falha ao gerar PDF: {exc}") from exc
    filename = f"Relatorio_{row['legacy_id'] or lancamento_id}.pdf"
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
