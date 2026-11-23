"""Aplica migrações SQL versionadas no SQLite do SIGPAR.

Uso:
    python -m app.migrate [--db /caminho/sigpar.sqlite]

As migrações ficam em db/migrations/NNN_descricao.sql e são imutáveis após
o merge. O deploy de produção faz backup antes de chamar este módulo.
"""
from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

from .config import get_settings

MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "db" / "migrations"


def _ensure_meta(con: sqlite3.Connection) -> None:
    con.execute(
        "CREATE TABLE IF NOT EXISTS schema_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
    )


def current_version(con: sqlite3.Connection) -> int:
    row = con.execute("SELECT value FROM schema_meta WHERE key = 'version'").fetchone()
    return int(row[0]) if row else 0


def apply_migrations(db_path: str | None = None) -> list[int]:
    path = db_path or get_settings().db_path
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path, timeout=30)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    con.execute("PRAGMA busy_timeout = 5000")
    applied: list[int] = []
    try:
        _ensure_meta(con)
        version = current_version(con)
        files = sorted(MIGRATIONS_DIR.glob("[0-9][0-9][0-9]_*.sql"))
        for file in files:
            number = int(file.name[:3])
            if number <= version:
                continue
            sql = file.read_text(encoding="utf-8")
            try:
                con.executescript(sql)
                con.execute(
                    "INSERT INTO schema_meta(key, value) VALUES ('version', ?) "
                    "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                    (str(number),),
                )
                con.commit()
            except Exception:
                con.rollback()
                raise
            applied.append(number)
            version = number
        return applied
    finally:
        con.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default=None)
    args = parser.parse_args()
    applied = apply_migrations(args.db)
    if applied:
        print("migrações aplicadas:", ", ".join(str(x) for x in applied))
    else:
        print("banco já está na última versão")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
