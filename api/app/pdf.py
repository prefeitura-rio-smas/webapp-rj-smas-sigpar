from __future__ import annotations

import base64
import os
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from jinja2 import Environment, FileSystemLoader, select_autoescape

BASE = Path(__file__).resolve().parent
TEMPLATES = BASE / "templates"
ASSETS = BASE / "static" / "assets"
CHROME = Path(
    os.getenv(
        "SIGPAR_CHROME",
        "/root/.cache/ms-playwright/chromium-1246/chrome-linux-arm64/chrome",
    )
)

AVALIACAO_LABELS = [
    ("CSIMAS — Capacidade de Contratação", "nota1"),
    ("CSIMAS — Adimplência", "nota2"),
    ("COP — Insumos", "nota3"),
    ("COP — Veículos", "nota4"),
    ("CIN — Aluguéis", "nota5"),
    ("CCPAR — Prestação", "nota6"),
    ("CCPAR — Diligência", "nota7"),
    ("CSIMAS — Ergon", "nota8"),
    ("COP — Motoristas", "nota9"),
    ("CCPAR — SIAFIC", "nota10"),
    ("CCPAR — Osinfo", "nota11"),
]

_env = Environment(
    loader=FileSystemLoader(str(TEMPLATES)),
    autoescape=select_autoescape(["html", "xml"]),
)


def _logo(name: str) -> str:
    path = ASSETS / name
    if not path.exists():
        return ""
    mime = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
    return f"data:{mime};base64," + base64.b64encode(path.read_bytes()).decode()


def logos() -> dict[str, str]:
    return {
        "pref": _logo("1fX_17J8ASxDcGC5m5oOp35yArWObWC7r.png"),
        "mrosc": _logo("1e0yDTpbHSlpIlhDlX3fywWSGLIEL5b_d.png"),
        "footer": _logo("1mC5uHmAkEq-mP4pHCLrVuRdLG_3Hb3YH.png"),
    }


def fmt_num(value) -> str:
    if value is None or value == "":
        return "-"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if abs(number - round(number)) < 1e-9:
        return str(int(round(number)))
    return f"{number:.2f}".replace(".", ",")


def fmt_pct(value) -> str:
    if value is None or value == "":
        return "-"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    return f"{number * 100:.2f}%".replace(".", ",")


def fmt_mes(value: str | None) -> str:
    if not value:
        return "-"
    text = str(value)
    if len(text) >= 7 and text[4] == "-":
        return f"{text[5:7]}/{text[:4]}"
    return text


def now_brt() -> str:
    return datetime.now(ZoneInfo("America/Sao_Paulo")).strftime("%d/%m/%Y %H:%M:%S")


def render_pdf(data: dict) -> bytes:
    """Renderiza o relatório em PDF via Chromium headless."""
    lanc = data["lancamento"]
    postos_total = lanc.get("postos_total") or 0
    postos_ocupados = lanc.get("postos_ocupados") or 0
    lanches_prev = lanc.get("lanches_previsto") or 0
    lanches_exec = lanc.get("lanches_executado") or 0

    context = {
        **data,
        "logos": logos(),
        "emitido_em": now_brt(),
        "mes_display": fmt_mes(lanc.get("referencia_mes")),
        "postos_pct": (postos_ocupados / postos_total) if postos_total else None,
        "lanches_pct": (lanches_exec / lanches_prev) if lanches_prev else None,
        "perfil_autor": data.get("autor_perfil") or "Usuário",
        "avaliacao_labels": AVALIACAO_LABELS,
        "fmt_num": fmt_num,
        "fmt_pct": fmt_pct,
    }
    html = _env.get_template("relatorio.html").render(**context)
    if not CHROME.exists():
        raise RuntimeError(f"Chromium não encontrado em {CHROME}")

    with tempfile.TemporaryDirectory(prefix="sigpar-pdf-") as tmp:
        tmpdir = Path(tmp)
        html_path = tmpdir / "relatorio.html"
        pdf_path = tmpdir / "relatorio.pdf"
        html_path.write_text(html, encoding="utf-8")
        cmd = [
            str(CHROME),
            "--headless",
            "--no-sandbox",
            "--disable-gpu",
            "--disable-dev-shm-usage",
            "--no-pdf-header-footer",
            "--virtual-time-budget=5000",
            f"--print-to-pdf={pdf_path}",
            html_path.as_uri(),
        ]
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=90,
            check=False,
        )
        if proc.returncode != 0 or not pdf_path.exists():
            raise RuntimeError(
                f"falha ao gerar PDF (rc={proc.returncode}): "
                f"{(proc.stderr or proc.stdout or '')[-800:]}"
            )
        pdf = pdf_path.read_bytes()
        if not pdf.startswith(b"%PDF"):
            raise RuntimeError("Chromium não retornou um PDF válido")
        return pdf
