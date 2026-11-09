"""Verify the deployed demo using two fictitious accounts and sample files.

Run with backend/.venv Python. Generates credentials only in memory, never
prints them, and creates a small set of fictitious records for validation.
"""

import argparse
import hashlib
import json
import secrets
import uuid
from pathlib import Path

import httpx

parser = argparse.ArgumentParser()
parser.add_argument("--base-url", default="https://pqr-web-53950210571.us-central1.run.app")
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
tag = uuid.uuid4().hex[:10]
password = secrets.token_urlsafe(24)
with (
    httpx.Client(base_url=args.base_url, timeout=110) as alice,
    httpx.Client(base_url=args.base_url, timeout=40) as bob,
):
    health = alice.get("/api/health")
    health.raise_for_status()
    assert health.json()["mode"] == "cloud"
    assert health.json()["ai_mode"] == "gemini"
    for client, suffix in ((alice, "a"), (bob, "b")):
        response = client.post(
            "/api/auth/register",
            json={"email": f"smoke-{tag}-{suffix}@nexo.test", "password": password},
        )
        assert response.status_code in (200, 201), response.text
        assert "HttpOnly" in response.headers["set-cookie"]
        assert "Secure" in response.headers["set-cookie"]
    raw = (root / "samples/reclamo-ficticio.pdf").read_bytes()
    preview = alice.post(
        "/api/uploads", files={"file": ("reclamo-ficticio.pdf", raw, "application/pdf")}
    )
    assert preview.status_code == 201, preview.text
    upload = preview.json()
    assert "FAC-DEMO-004" in upload["text"]
    response = alice.post(
        "/api/pqrs",
        json={
            "title": "PDF ficticio para validación integrada",
            "text": upload["text"] + "\nTexto complementado durante la prueba cloud.",
            "upload_id": upload["id"],
        },
    )
    assert response.status_code == 201, response.text
    item = response.json()
    key = item["id"]
    assert item["original_text"] == upload["text"]
    assert item["text"] != item["original_text"]
    result = alice.post(f"/api/pqrs/{key}/analyze")
    result.raise_for_status()
    result = result.json()
    assert result["status"] == "completada", result.get("error")
    assert result["result"]["engine"] == "google-adk"
    download = alice.get(f"/api/pqrs/{key}/file")
    assert download.status_code == 200
    assert hashlib.sha256(download.content).digest() == hashlib.sha256(raw).digest()
    assert bob.get("/api/pqrs").json() == []
    for suffix in ("", "/file", "/result"):
        assert bob.get(f"/api/pqrs/{key}{suffix}").status_code == 404
    assert bob.post(f"/api/pqrs/{key}/analyze").status_code == 404
    scanned = alice.post(
        "/api/uploads",
        files={
            "file": (
                "escaneado.pdf",
                (root / "samples/escaneado-sin-texto.pdf").read_bytes(),
                "application/pdf",
            )
        },
    )
    assert scanned.status_code == 422
    assert "escaneado" in scanned.json()["detail"]
    docx = alice.post(
        "/api/uploads",
        files={"file": ("reclamo.docx", (root / "samples/reclamo-ficticio.docx").read_bytes())},
    )
    assert docx.status_code == 201, docx.text
    assert "FAC-DEMO-004" in docx.json()["text"]
    evidence = {
        "cloud_flow": "passed",
        "pqr_reference": item["reference"],
        "pqr_id": key,
        "engine": result["result"]["engine"],
        "model": result["result"]["model"],
        "original_download": "sha256_match",
        "owner_isolation": "passed",
        "pdf_extraction": "passed",
        "docx_extraction": "passed",
        "scanned_pdf": "rejected_422",
        "session_cookie": "HttpOnly_Secure",
    }
    (root / ".local").mkdir(exist_ok=True)
    (root / ".local/cloud-validation.json").write_text(json.dumps(evidence, indent=2))
    print(json.dumps(evidence, indent=2))
