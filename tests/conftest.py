import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "api"))

_TMP_DB = os.path.join(tempfile.mkdtemp(prefix="sigpar-test-"), "sigpar.sqlite")
os.environ["SIGPAR_DB"] = _TMP_DB
os.environ["SIGPAR_NOAUTH"] = "1"
os.environ["SIGPAR_DEV_EMAIL"] = "dev@local"

from app.db import init_db  # noqa: E402
from app.main import app  # noqa: E402
from app.migrate import apply_migrations  # noqa: E402

init_db()
apply_migrations()

__all__ = ["app", "_TMP_DB"]
