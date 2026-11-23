from fastapi import HTTPException

from .db import connect


def get_usuario(email: str) -> dict | None:
    con = connect()
    try:
        row = con.execute(
            "SELECT email, nome, perfil, unidade_padrao_id, territorio, meta, ativo "
            "FROM usuarios WHERE email = ?",
            (email.lower(),),
        ).fetchone()
        return dict(row) if row else None
    finally:
        con.close()


def get_usuario_ativo(email: str) -> dict:
    usuario = get_usuario(email)
    if not usuario:
        raise HTTPException(status_code=403, detail="nao autorizado")
    if not usuario["ativo"]:
        raise HTTPException(status_code=403, detail="usuario inativo")
    return usuario


def unidades_permitidas(email: str) -> list[dict]:
    con = connect()
    try:
        rows = con.execute(
            "SELECT unidade_id, nome, tipo, territorio "
            "FROM vw_unidades_permitidas WHERE email = ? ORDER BY nome",
            (email.lower(),),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        con.close()


def unidades_ids(email: str) -> list[int]:
    con = connect()
    try:
        rows = con.execute(
            "SELECT unidade_id FROM vw_unidades_permitidas WHERE email = ?",
            (email.lower(),),
        ).fetchall()
        return [r["unidade_id"] for r in rows]
    finally:
        con.close()


def pode_unidade(email: str, unidade_id: int) -> bool:
    con = connect()
    try:
        row = con.execute(
            "SELECT 1 FROM vw_unidades_permitidas WHERE email = ? AND unidade_id = ?",
            (email.lower(), unidade_id),
        ).fetchone()
        return bool(row)
    finally:
        con.close()


def exigir_unidade(email: str, unidade_id: int) -> None:
    if not pode_unidade(email, unidade_id):
        raise HTTPException(status_code=403, detail="sem permissao para a unidade")
