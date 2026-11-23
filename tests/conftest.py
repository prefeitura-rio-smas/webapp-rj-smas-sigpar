import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api"))

_TMP_DB = os.path.join(tempfile.mkdtemp(prefix="sigpar-test-"), "sigpar.sqlite")
os.environ["SIGPAR_DB"] = _TMP_DB
os.environ["SIGPAR_NOAUTH"] = "1"
os.environ["SIGPAR_DEV_EMAIL"] = "dev@local"

from app.main import app  # noqa: E402

__all__ = ["app", "_TMP_DB"]
