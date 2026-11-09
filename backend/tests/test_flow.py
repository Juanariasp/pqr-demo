from io import BytesIO

import pytest
from docx import Document
from fastapi.testclient import TestClient
from pypdf import PdfWriter

from app import agents
from app.config import settings
from app.main import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("APP_MODE", "local")
    monkeypatch.setenv("AI_MODE", "rules")
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.delenv("K_SERVICE", raising=False)
    settings.cache_clear()
    with TestClient(app) as value:
        yield value
    settings.cache_clear()


def account(client, email="demo@example.test"):
    response = client.post("/auth/register", json={"email": email, "password": "Demo-pqr-2026!"})
    assert response.status_code == 201, response.text
    return {"Authorization": f"Bearer {response.json()['token']}"}


def payload(**kwargs):
    return {
        "title": "Revisión de cobro duplicado",
        "text": "Solicito revisar un cobro duplicado de $45.000 en la factura FAC-DEMO-001.",
        **kwargs,
    }


def test_full_text_flow_and_ownership(client):
    headers = account(client)
    assert client.get("/pqrs").status_code == 401
    created = client.post("/pqrs", json=payload(), headers=headers)
    assert created.status_code == 201, created.text
    item = created.json()
    assert item["status"] == "recibida"
    result = client.post(f"/pqrs/{item['id']}/analyze", headers=headers).json()
    assert result["status"] == "completada"
    assert result["result"]["category"] == "reclamo"
    assert result["result"]["engine"] == "rules"
    assert result["attempts"] == 1
    again = client.post(f"/pqrs/{item['id']}/analyze", headers=headers).json()
    assert again["attempts"] == 1
    assert len(client.get("/pqrs", headers=headers).json()) == 1
    other = account(client, "other@example.test")
    assert client.get("/pqrs", headers=other).json() == []
    for path in (item["id"], f"{item['id']}/file", f"{item['id']}/result"):
        assert client.get(f"/pqrs/{path}", headers=other).status_code == 404
    assert client.post(f"/pqrs/{item['id']}/analyze", headers=other).status_code == 404


def test_docx_preview_edit_attach_and_download(client):
    headers = account(client)
    doc = Document()
    doc.add_paragraph("Solicito un certificado de servicio para una cuenta ficticia.")
    buffer = BytesIO()
    doc.save(buffer)
    raw = buffer.getvalue()
    upload = client.post("/uploads", files={"file": ("peticion.docx", raw)}, headers=headers)
    assert upload.status_code == 201, upload.text
    item = upload.json()
    assert "certificado" in item["text"]
    other = account(client, "other@example.test")
    assert (
        client.post("/pqrs", json=payload(upload_id=item["id"]), headers=other).status_code == 404
    )
    created = client.post("/pqrs", json=payload(upload_id=item["id"]), headers=headers).json()
    assert created["original_text"] == item["text"]
    assert created["text"] != item["text"]
    assert client.get(f"/pqrs/{created['id']}/file", headers=headers).content == raw
    assert (
        client.post("/pqrs", json=payload(upload_id=item["id"]), headers=headers).status_code == 409
    )


@pytest.mark.parametrize(
    "name,data,status",
    [
        ("a.exe", b"abc", 415),
        ("a.docx", b"", 422),
        ("a.docx", b"broken", 422),
        ("a.pdf", b"garbage", 422),
        ("a.pdf", b"x" * (5 * 1024 * 1024 + 1), 413),
    ],
)
def test_reject_invalid_documents(client, name, data, status):
    headers = account(client)
    response = client.post("/uploads", files={"file": (name, data)}, headers=headers)
    assert response.status_code == status, response.text


def test_pdf_without_text(client):
    headers = account(client)
    writer = PdfWriter()
    writer.add_blank_page(width=300, height=300)
    buffer = BytesIO()
    writer.write(buffer)
    response = client.post(
        "/uploads", files={"file": ("scanned.pdf", buffer.getvalue())}, headers=headers
    )
    assert response.status_code == 422
    assert "escaneado" in response.json()["detail"]


def test_analysis_failure_and_retry(client, monkeypatch):
    headers = account(client)
    key = client.post("/pqrs", json=payload(), headers=headers).json()["id"]
    real = agents.analyze

    async def fail(text):
        raise RuntimeError("fake unavailable model")

    monkeypatch.setattr(agents, "analyze", fail)
    output = client.post(f"/pqrs/{key}/analyze", headers=headers).json()
    assert output["status"] == "error"
    assert output["result"] is None
    monkeypatch.setattr(agents, "analyze", real)
    output = client.post(f"/pqrs/{key}/analyze", headers=headers).json()
    assert output["status"] == "completada"
    assert output["attempts"] == 2


def test_login_and_invalid_token(client):
    account(client)
    assert (
        client.post(
            "/auth/login", json={"email": "demo@example.test", "password": "bad-password"}
        ).status_code
        == 401
    )
    login = client.post(
        "/auth/login", json={"email": "demo@example.test", "password": "Demo-pqr-2026!"}
    )
    assert login.status_code == 200
    assert client.get("/auth/me", headers={"Authorization": "Bearer invalid"}).status_code == 401


def test_local_mode_refused_in_cloud(monkeypatch):
    monkeypatch.setenv("K_SERVICE", "pqr-api")
    monkeypatch.setenv("APP_MODE", "local")
    settings.cache_clear()
    with pytest.raises(RuntimeError, match="APP_MODE=cloud"):
        settings().validate_runtime()
    settings.cache_clear()


def test_adk_pipeline_has_three_agents():
    coordinator = agents.build_coordinator()
    assert [agent.name for agent in coordinator.sub_agents] == [
        "clasificador",
        "analista",
        "redactor",
    ]
