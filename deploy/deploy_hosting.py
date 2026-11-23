#!/usr/bin/env python3
"""Deploy do front SIGPAR para o Firebase Hosting (site sigpar).

Projeto: sigpar-smas
Site:    sigpar  -> https://sigpar.web.app
Conta:   SIGPAR_FIREBASE_ACCOUNT (local); no CI/CD usar Workload Identity Federation

Protocolo (aprendido com o CORIN):
- gzip.compress UMA vez por arquivo; hash = sha256 desses bytes.
- populateFiles com {"/caminho": hash}; upload octet-stream puro.
- versionName relativo: sites/<site>/versions/<id>.
Uso: python3 deploy/deploy_hosting.py "mensagem do release"
"""
from __future__ import annotations

import gzip
import hashlib
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

WEB = Path(__file__).resolve().parents[1] / "web"
PROJECT = "sigpar-smas"
SITE = "sigpar"
ACCOUNT = os.getenv("SIGPAR_FIREBASE_ACCOUNT", "")


def token() -> str:
    cmd = ["gcloud", "auth", "print-access-token"]
    if ACCOUNT:
        cmd.append(f"--account={ACCOUNT}")
    return subprocess.check_output(cmd, text=True).strip()


def api(method: str, url: str, body: dict | None = None) -> dict:
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode() if body is not None else None,
        headers={
            "Authorization": f"Bearer {token()}",
            "Content-Type": "application/json",
            "X-Goog-User-Project": PROJECT,
        },
        method=method,
    )
    with urllib.request.urlopen(req, timeout=300) as r:
        raw = r.read().decode()
        return json.loads(raw) if raw else {}


def collect_files() -> dict[str, bytes]:
    files: dict[str, bytes] = {}
    for path in sorted(WEB.rglob("*")):
        if not path.is_file():
            continue
        rel = "/" + str(path.relative_to(WEB))
        files[rel] = path.read_bytes()
    if "/index.html" not in files:
        raise SystemExit("web/index.html nao encontrado")
    return files


def main() -> int:
    msg = sys.argv[1] if len(sys.argv) > 1 else "sigpar web deploy"
    base = f"https://firebasehosting.googleapis.com/v1beta1/projects/{PROJECT}/sites/{SITE}"

    raw = collect_files()
    if "/index.html" in raw and "/app.js" in raw:
        import hashlib as _h
        v = _h.sha256(raw["/app.js"]).hexdigest()[:8]
        idx = raw["/index.html"].decode("utf-8")
        idx = idx.replace('src="/app.js"', f'src="/app.js?v={v}"')
        raw["/index.html"] = idx.encode("utf-8")
    blobs = {p: gzip.compress(b) for p, b in raw.items()}
    hashes = {p: hashlib.sha256(g).hexdigest() for p, g in blobs.items()}

    version = api("POST", f"{base}/versions", {})
    vname = version["name"].split("/")[-1]
    print("version:", vname, flush=True)

    populated = api(
        "POST",
        f"{base}/versions/{vname}:populateFiles",
        {"files": hashes},
    )
    upload_url = populated.get("uploadUrl")
    needed = set(populated.get("uploadRequiredHashes", []))
    print(f"files={len(blobs)} need_upload={len(needed)}", flush=True)

    for path, blob in blobs.items():
        digest = hashlib.sha256(blob).hexdigest()
        if digest not in needed:
            print(" cached", path, flush=True)
            continue
        req = urllib.request.Request(
            f"{upload_url}/{digest}",
            data=blob,
            headers={
                "Authorization": f"Bearer {token()}",
                "Content-Type": "application/octet-stream",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                print(" uploaded", path, r.status, flush=True)
        except urllib.error.HTTPError as exc:
            print(" FAIL", path, exc.code, exc.read().decode()[:300], flush=True)
            print(f"ABORTADO (versao {vname} incompleta, site intacto)")
            return 1

    finalized = api("PATCH", f"{base}/versions/{vname}", {"status": "FINALIZED"})
    print("finalized:", finalized.get("status"), flush=True)
    time.sleep(5)
    release = api(
        "POST",
        f"{base}/releases?versionName=sites/{SITE}/versions/{vname}",
        {"message": msg},
    )
    print("released:", release.get("name"), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
