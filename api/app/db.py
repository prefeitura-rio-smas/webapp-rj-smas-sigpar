import sqlite3
from pathlib import Path

from .config import get_settings

SCHEMA_PATH = Path(__file__).resolve().parents[2] / "db" / "schema.sql"


def connect() -> sqlite3.Connection:
    cfg = get_settings()
    Path(cfg.db_path).parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(cfg.db_path, timeout=5)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    con.execute("PRAGMA journal_mode = WAL")
    con.execute("PRAGMA busy_timeout = 5000")
    return con


def init_db() -> None:
    con = connect()
    try:
        con.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        con.commit()
    finally:
        con.close()
