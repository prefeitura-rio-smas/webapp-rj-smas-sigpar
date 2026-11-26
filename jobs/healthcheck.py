#!/usr/bin/env python3
"""Verifica a API local e a idade do último backup no SQLite."""
from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import datetime
from urllib.request import urlopen
from zoneinfo import ZoneInfo

BRT = ZoneInfo("America/Sao_Paulo")


def check_api(url: str, timeout: float = 10) -> dict:
    with urlopen(url, timeout=timeout) as response:
        body = json.loads(response.read().decode("utf-8"))
    if body.get("ok") is not True or body.get("db") != "ok":
        raise RuntimeError("health retornou estado nao ok")
    return {
        "ok": True,
        "app": body.get("app"),
        "version": body.get("version"),
        "schema_version": body.get("schema_version"),
    }


def check_backup(db_path: str, max_age_hours: float = 26) -> dict:
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        row = con.execute(
            "SELECT status, finished_at FROM backup_runs ORDER BY id DESC LIMIT 1"
        ).fetchone()
    finally:
        con.close()
    if not row:
        raise RuntimeError("nenhum backup registrado")
    status, finished_at = row
    if status != "ok" or not finished_at:
        raise RuntimeError(f"ultimo backup com status {status or 'vazio'}")
    finished = datetime.strptime(finished_at, "%Y-%m-%d %H:%M:%S").replace(tzinfo=BRT)
    age_hours = (datetime.now(BRT) - finished).total_seconds() / 3600
    if age_hours < 0:
        raise RuntimeError("data de backup no futuro")
    if age_hours > max_age_hours:
        raise RuntimeError(
            f"backup antigo: {age_hours:.1f}h (limite {max_age_hours:g}h)"
        )
    return {
        "status": status,
        "finished_at": finished_at,
        "age_hours": round(age_hours, 1),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Healthcheck do SIGPAR")
    parser.add_argument(
        "--url", default="http://127.0.0.1:3103/health", help="URL do /health"
    )
    parser.add_argument(
        "--db",
        default="/var/lib/sigpar/prod/sigpar.sqlite",
        help="caminho do SQLite de producao",
    )
    parser.add_argument("--max-backup-age", type=float, default=26)
    parser.add_argument("--timeout", type=float, default=10)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result: dict = {"ok": True}
    errors: list[str] = []
    try:
        result["api"] = check_api(args.url, args.timeout)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"api: {type(exc).__name__}: {exc}")
    try:
        result["backup"] = check_backup(args.db, args.max_backup_age)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"backup: {type(exc).__name__}: {exc}")
    if errors:
        result["ok"] = False
        result["errors"] = errors
        print(json.dumps(result, ensure_ascii=False))
        return 1
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
