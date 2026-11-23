#!/usr/bin/env python3
"""Restaura o SQLite do SIGPAR a partir do snapshot no Google Sheets.

Uso:
    SIGPAR_BACKUP_SHEET_ID=<id> \
    SIGPAR_BACKUP_SA_KEY=/root/sigpar/secrets/sigpar-backup.json \
    python3 etl/restore_from_sheet.py /root/sigpar/db/sigpar-restored.sqlite

O destino deve ser um arquivo novo (ou vazio). O script:
1. cria o schema v1;
2. lê cada aba do snapshot (cabeçalho + linhas);
3. limpa e reinsere as tabelas na ordem segura;
4. confere as contagens contra a aba `_meta`.

Não aponte para o banco de produção sem parar a API antes.
"""
from __future__ import annotations

import os
import sqlite3
import sys
from pathlib import Path

from google.auth.transport.requests import AuthorizedSession
from google.oauth2.service_account import Credentials

SHEET_ID = os.getenv("SIGPAR_BACKUP_SHEET_ID", "")
SA_KEY = os.getenv("SIGPAR_BACKUP_SA_KEY", "/root/sigpar/secrets/sigpar-backup.json")
SCHEMA = Path(__file__).resolve().parents[1] / "db" / "schema.sql"

ORDER = [
    "itens_contrato",
    "unidades",
    "usuarios",
    "postos",
    "insumos",
    "kit_operacional",
    "veiculos",
    "avaliacoes_servico",
    "lancamentos",
    "lancamento_postos",
    "lancamento_insumos",
    "lancamento_veiculos",
    "lancamento_lanches",
    "lancamento_kit",
    "lancamento_locacao",
    "avaliacao_central",
    "audit_log",
]
SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]


def sheets_session() -> tuple[AuthorizedSession, str]:
    creds = Credentials.from_service_account_file(SA_KEY, scopes=SCOPES)
    return AuthorizedSession(creds), f"https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}"


def read_tab(session: AuthorizedSession, base: str, title: str) -> list[list]:
    url = base + f"/values/'{title}'!A:ZZ?valueRenderOption=UNFORMATTED_VALUE"
    resp = session.get(url, timeout=180)
    if resp.status_code == 404:
        return []
    if resp.status_code >= 400:
        raise RuntimeError(f"{title}: {resp.status_code} {resp.text[:300]}")
    return resp.json().get("values", [])


def main(argv: list[str]) -> int:
    if not SHEET_ID:
        print("SIGPAR_BACKUP_SHEET_ID nao configurado", file=sys.stderr)
        return 2
    if not Path(SA_KEY).exists():
        print(f"chave da service account nao encontrada: {SA_KEY}", file=sys.stderr)
        return 2
    dest = Path(argv[1]) if len(argv) > 1 else Path("/root/sigpar/db/sigpar-restored.sqlite")
    if dest.exists() and dest.stat().st_size > 0:
        print(f"destino ja existe: {dest}. Use um arquivo novo.", file=sys.stderr)
        return 2

    dest.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(dest)
    con.execute("PRAGMA foreign_keys = OFF")
    con.executescript(SCHEMA.read_text(encoding="utf-8"))
    con.commit()

    session, base = sheets_session()
    meta = read_tab(session, base, "_meta")
    expected: dict[str, int] = {}
    for row in meta:
        if len(row) >= 2 and str(row[0]) not in ("", "table"):
            try:
                expected[str(row[0])] = int(row[1])
            except (TypeError, ValueError):
                pass

    try:
        con.execute("BEGIN")
        for table in reversed(ORDER):
            con.execute(f"DELETE FROM {table}")
        for table in ORDER:
            rows = read_tab(session, base, table)
            if not rows:
                print(f"vazio {table}")
                continue
            header = [str(c).strip() for c in rows[0]]
            placeholders = ",".join("?" for _ in header)
            cols = ",".join(f'"{c}"' for c in header)
            payload = []
            for row in rows[1:]:
                if not any(v not in (None, "") for v in row):
                    continue
                vals = list(row) + [""] * (len(header) - len(row))
                payload.append(
                    [None if v == "" else v for v in vals[: len(header)]]
                )
            if payload:
                con.executemany(
                    f'INSERT INTO {table} ({cols}) VALUES ({placeholders})',
                    payload,
                )
            got = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            print(f"ok {table}: {got}" + (f" (esperado {expected[table]})" if table in expected else ""))
        con.commit()
    except Exception as exc:  # noqa: BLE001
        con.rollback()
        print(f"ERRO restore: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    finally:
        con.close()

    print(f"restaurado em {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
