#!/usr/bin/env python3
"""Snapshot completo do SQLite do SIGPAR para uma planilha Google.

Uso:
    SIGPAR_BACKUP_SHEET_ID=<id> \
    SIGPAR_BACKUP_SA_KEY=/root/sigpar/secrets/sigpar-backup.json \
    python3 jobs/backup_to_sheet.py

A planilha precisa estar compartilhada como Editor com o e-mail da service
account (ex.: sigpar-backup@sigpar-smas.iam.gserviceaccount.com).

Importante: este snapshot é a cópia de recuperação do MVP (não há backup
binário local). O restore é feito por etl/restore_from_sheet.py.
"""
from __future__ import annotations

import os
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from google.auth.transport.requests import AuthorizedSession
from google.oauth2.service_account import Credentials

DB = os.getenv("SIGPAR_DB", "/root/sigpar/db/sigpar.sqlite")
SHEET_ID = os.getenv("SIGPAR_BACKUP_SHEET_ID", "")
SA_KEY = os.getenv("SIGPAR_BACKUP_SA_KEY", "/root/sigpar/secrets/sigpar-backup.json")

TABLES = [
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
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def now_brt() -> str:
    return datetime.now(ZoneInfo("America/Sao_Paulo")).strftime("%Y-%m-%d %H:%M:%S")


class Sheets:
    def __init__(self, sheet_id: str, sa_key: str):
        creds = Credentials.from_service_account_file(sa_key, scopes=SCOPES)
        self.session = AuthorizedSession(creds)
        self.base = f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}"
        self.sheet_id = sheet_id
        self.titles: set[str] = set()

    def _call(self, method: str, path: str, **kwargs):
        url = self.base + path
        resp = self.session.request(method, url, timeout=180, **kwargs)
        if resp.status_code >= 400:
            raise RuntimeError(f"{method} {path}: {resp.status_code} {resp.text[:300]}")
        return resp.json() if resp.content else {}

    def load_titles(self) -> None:
        data = self._call("GET", "?fields=sheets.properties.title")
        self.titles = {s["properties"]["title"] for s in data.get("sheets", [])}

    def ensure_sheet(self, title: str) -> None:
        if title in self.titles:
            return
        self._call(
            "POST",
            ":batchUpdate",
            json={"requests": [{"addSheet": {"properties": {"title": title}}}]},
        )
        self.titles.add(title)

    def write(self, title: str, values: list[list]) -> None:
        self.ensure_sheet(title)
        rng = f"'{title}'!A:ZZ"
        self._call("POST", f"/values/{rng}:clear", json={})
        if values:
            self._call(
                "PUT",
                f"/values/'{title}'!A1?valueInputOption=USER_ENTERED",
                json={"values": values},
            )


def dump_table(con: sqlite3.Connection, table: str) -> tuple[list[str], list[list]]:
    cur = con.execute(f"SELECT * FROM {table}")
    cols = [d[0] for d in cur.description]
    out: list[list] = []
    for row in cur:
        out.append(["" if v is None else v for v in row])
    return cols, out


def main() -> int:
    if not SHEET_ID:
        print("SIGPAR_BACKUP_SHEET_ID nao configurado", file=sys.stderr)
        return 2
    if not Path(SA_KEY).exists():
        print(f"chave da service account nao encontrada: {SA_KEY}", file=sys.stderr)
        return 2
    if not Path(DB).exists():
        print(f"banco nao encontrado: {DB}", file=sys.stderr)
        return 2

    started = now_brt()
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    run_id = None
    try:
        cur = con.execute(
            "INSERT INTO backup_runs (started_at, status, sheet_id) VALUES (?, 'running', ?)",
            (started, SHEET_ID),
        )
        run_id = cur.lastrowid
        con.commit()

        con.execute("BEGIN")
        data = {t: dump_table(con, t) for t in TABLES}
        con.rollback()

        sh = Sheets(SHEET_ID, SA_KEY)
        sh.load_titles()
        counts: list[list] = []
        for table, (cols, rows) in data.items():
            sh.write(table, [cols] + rows)
            counts.append([table, len(rows), len(cols)])
            print(f"ok {table}: {len(rows)} linhas")

        meta = [
            ["snapshot_at", now_brt()],
            ["db", DB],
            ["schema_version", con.execute(
                "SELECT value FROM schema_meta WHERE key='version'"
            ).fetchone()["value"]],
            ["tables", len(TABLES)],
            [],
            ["table", "rows", "cols"],
        ] + counts
        sh.write("_meta", meta)

        finished = now_brt()
        con.execute(
            "UPDATE backup_runs SET finished_at=?, status='ok', detalhe=? WHERE id=?",
            (finished, f"{len(TABLES)} tabelas", run_id),
        )
        con.commit()
        print(f"backup ok em {finished}")
        return 0
    except Exception as exc:  # noqa: BLE001
        con.rollback()
        msg = f"{type(exc).__name__}: {exc}"
        print(f"ERRO backup: {msg}", file=sys.stderr)
        if run_id is not None:
            con.execute(
                "UPDATE backup_runs SET finished_at=?, status='erro', erro=? WHERE id=?",
                (now_brt(), msg[:2000], run_id),
            )
            con.commit()
        return 1
    finally:
        con.close()


if __name__ == "__main__":
    raise SystemExit(main())
