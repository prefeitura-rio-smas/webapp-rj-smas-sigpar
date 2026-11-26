import sqlite3
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from jobs.healthcheck import check_backup

BRT = ZoneInfo("America/Sao_Paulo")


def _db(tmp_path: Path) -> Path:
    path = tmp_path / "sigpar.sqlite"
    con = sqlite3.connect(path)
    try:
        con.execute(
            "CREATE TABLE backup_runs (id INTEGER PRIMARY KEY, started_at TEXT, "
            "finished_at TEXT, status TEXT)"
        )
        con.commit()
    finally:
        con.close()
    return path


def test_backup_recente_ok(tmp_path):
    path = _db(tmp_path)
    now = datetime.now(BRT).strftime("%Y-%m-%d %H:%M:%S")
    con = sqlite3.connect(path)
    try:
        con.execute(
            "INSERT INTO backup_runs (started_at, finished_at, status) VALUES (?, ?, 'ok')",
            (now, now),
        )
        con.commit()
    finally:
        con.close()
    result = check_backup(str(path), max_age_hours=26)
    assert result["status"] == "ok"
    assert result["age_hours"] < 1


def test_backup_ausente_falha(tmp_path):
    path = _db(tmp_path)
    with pytest.raises(RuntimeError, match="nenhum backup"):
        check_backup(str(path))


def test_backup_antigo_falha(tmp_path):
    path = _db(tmp_path)
    con = sqlite3.connect(path)
    try:
        con.execute(
            "INSERT INTO backup_runs (started_at, finished_at, status) "
            "VALUES ('2020-01-01 00:00:00', '2020-01-01 00:00:00', 'ok')"
        )
        con.commit()
    finally:
        con.close()
    with pytest.raises(RuntimeError, match="backup antigo"):
        check_backup(str(path), max_age_hours=26)


def test_backup_com_erro_falha(tmp_path):
    path = _db(tmp_path)
    con = sqlite3.connect(path)
    try:
        con.execute(
            "INSERT INTO backup_runs (started_at, finished_at, status) "
            "VALUES ('2020-01-01 00:00:00', '2020-01-01 00:00:00', 'erro')"
        )
        con.commit()
    finally:
        con.close()
    with pytest.raises(RuntimeError, match="status erro"):
        check_backup(str(path))
