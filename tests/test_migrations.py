import sqlite3
import tempfile
from pathlib import Path

from app.migrate import apply_migrations


def test_migrations_aplicam_e_sao_idempotentes():
    db = str(Path(tempfile.mkdtemp(prefix="sigpar-mig-")) / "sigpar.sqlite")
    applied = apply_migrations(db)
    assert applied == [1]

    con = sqlite3.connect(db)
    try:
        version = con.execute(
            "SELECT value FROM schema_meta WHERE key = 'version'"
        ).fetchone()[0]
        tabelas = {
            r[0]
            for r in con.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
    finally:
        con.close()

    assert version == "1"
    assert {"unidades", "usuarios", "lancamentos", "lancamento_insumos"} <= tabelas
    assert apply_migrations(db) == []
