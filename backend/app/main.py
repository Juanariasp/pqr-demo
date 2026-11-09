import asyncio
import logging
import uuid
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from pathlib import PurePath
from urllib.parse import quote

from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse, Response
from starlette.concurrency import run_in_threadpool

from . import agents
from .auth import authenticate, current_user
from .config import settings
from .extraction import extract
from .models import Credentials, PqrInput
from .store import Files, FirestoreStore, LocalStore, now

logger = logging.getLogger("pqr")


@asynccontextmanager
async def lifespan(app):
    settings().validate_runtime()
    app.state.store = FirestoreStore() if settings().app_mode == "cloud" else LocalStore()
    app.state.files = Files()
    yield


app = FastAPI(
    title="PQR Demo API",
    version="1.0.0",
    description="Peticiones, quejas y reclamos con Firebase y Google ADK. Solo datos ficticios.",
    lifespan=lifespan,
)


@app.middleware("http")
async def limit_body(request: Request, call_next):
    limit = (settings().max_upload_mb + 1) * 1024 * 1024
    if request.method in ("POST", "PUT", "PATCH"):
        chunks, size = [], 0
        async for chunk in request.stream():
            size += len(chunk)
            if size > limit:
                return JSONResponse(
                    {"detail": "La solicitud supera el tamaño permitido."}, status_code=413
                )
            chunks.append(chunk)
        request._body = b"".join(chunks)
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Cache-Control"] = "no-store"
    return response


def store(request: Request):
    return request.app.state.store


def owned(db, collection, key, uid):
    value = db.get(collection, key)
    if not value or value.get("owner") != uid:
        raise HTTPException(404, "No se encontró el recurso.")
    return value


def public_pqr(value):
    return {key: val for key, val in value.items() if key not in ("owner", "lease")}


@app.get("/health", tags=["Sistema"])
def health():
    return {
        "status": "ok",
        "mode": settings().app_mode,
        "ai_mode": settings().ai_mode,
        "max_upload_mb": settings().max_upload_mb,
    }


@app.post("/auth/register", tags=["Autenticación"], status_code=201)
async def register(credentials: Credentials):
    return await authenticate(credentials, register=True)


@app.post("/auth/login", tags=["Autenticación"])
async def login(credentials: Credentials):
    return await authenticate(credentials)


@app.get("/auth/me", tags=["Autenticación"])
def me(user=Depends(current_user)):
    return user


def cleanup_expired(db, files, uid):
    for item in db.list("uploads", uid):
        if not item.get("pqr_id") and not item.get("deleted") and item["expires_at"] < now():
            # Claim the expiry under the same transaction used for attachment.
            def expire(current):
                if current and not current.get("pqr_id"):
                    current["deleted"] = True
                return current

            expired = db.mutate("uploads", item["id"], expire)
            if expired.get("deleted"):
                files.delete(expired["storage_key"])


@app.post("/uploads", tags=["Documentos"], status_code=201)
def upload(
    request: Request, file: UploadFile = File(...), user=Depends(current_user), db=Depends(store)
):
    cleanup_expired(db, request.app.state.files, user["id"])
    filename = PurePath((file.filename or "documento").replace("\\", "/")).name[:200]
    data = file.file.read(settings().max_upload_mb * 1024 * 1024 + 1)
    text, mime = extract(filename, data)
    key = uuid.uuid4().hex
    storage_key = f"documents/{user['id']}/{key}"
    request.app.state.files.save(storage_key, data, mime)
    item = {
        "id": key,
        "owner": user["id"],
        "filename": filename,
        "mime": mime,
        "size": len(data),
        "original_text": text,
        "storage_key": storage_key,
        "created_at": now(),
        "expires_at": (datetime.now(UTC) + timedelta(hours=24)).isoformat(),
        "pqr_id": None,
    }
    db.put("uploads", key, item)
    return {
        "id": key,
        "filename": filename,
        "size": len(data),
        "text": text,
        "expires_at": item["expires_at"],
    }


@app.post("/pqrs", tags=["PQRs"], status_code=201)
def create_pqr(payload: PqrInput, user=Depends(current_user), db=Depends(store)):
    if len(payload.text) > settings().max_text_chars:
        raise HTTPException(422, "El texto supera el límite configurado.")
    key = uuid.uuid4().hex
    original_text, file_info = None, None
    if payload.upload_id:

        def claim(item):
            if not item or item["owner"] != user["id"]:
                raise HTTPException(404, "No se encontró el documento.")
            if item.get("pqr_id") or item.get("deleted") or item["expires_at"] < now():
                raise HTTPException(409, "El documento ya fue usado o venció. Cárgalo nuevamente.")
            item["pqr_id"] = key
            return item

        item = db.mutate("uploads", payload.upload_id, claim)
        original_text = item["original_text"]
        file_info = {"id": item["id"], "filename": item["filename"], "size": item["size"]}
    item = {
        "id": key,
        "reference": f"PQR-{datetime.now(UTC):%Y}-{key[:6].upper()}",
        "owner": user["id"],
        "title": payload.title,
        "text": payload.text,
        "original_text": original_text,
        "file": file_info,
        "status": "recibida",
        "created_at": now(),
        "updated_at": now(),
        "result": None,
        "error": None,
        "attempts": 0,
    }
    db.put("pqrs", key, item)
    return public_pqr(item)


@app.get("/pqrs", tags=["PQRs"])
def list_pqrs(user=Depends(current_user), db=Depends(store)):
    return [
        public_pqr(item)
        for item in sorted(
            db.list("pqrs", user["id"]), key=lambda item: item["created_at"], reverse=True
        )
    ]


@app.get("/pqrs/{key}", tags=["PQRs"])
def get_pqr(key: str, user=Depends(current_user), db=Depends(store)):
    return public_pqr(owned(db, "pqrs", key, user["id"]))


@app.get("/pqrs/{key}/result", tags=["PQRs"])
def result(key: str, user=Depends(current_user), db=Depends(store)):
    item = owned(db, "pqrs", key, user["id"])
    return {"status": item["status"], "result": item["result"], "error": item["error"]}


@app.post("/pqrs/{key}/analyze", tags=["Agentes"])
async def analyze_pqr(key: str, user=Depends(current_user), db=Depends(store)):
    lease = uuid.uuid4().hex

    def claim(item):
        if not item or item["owner"] != user["id"]:
            raise HTTPException(404, "No se encontró la PQR.")
        if item["status"] == "completada":
            return item
        if (
            item["status"] == "procesando"
            and (datetime.now(UTC) - datetime.fromisoformat(item["updated_at"])).total_seconds()
            < 120
        ):
            raise HTTPException(409, "La PQR ya se está analizando. Actualiza en un momento.")
        item.update(
            status="procesando",
            updated_at=now(),
            error=None,
            lease=lease,
            attempts=item["attempts"] + 1,
        )
        return item

    item = await run_in_threadpool(db.mutate, "pqrs", key, claim)
    if item["status"] == "completada":
        return public_pqr(item)
    try:
        output = await asyncio.wait_for(
            agents.analyze(item["text"]), settings().analysis_timeout_seconds
        )
        changes = {"status": "completada", "result": output.model_dump(), "error": None}
    except Exception as exc:
        logger.warning("Analysis failed for %s (%s)", key, type(exc).__name__)
        changes = {
            "status": "error",
            "result": None,
            "error": "No se pudo completar el análisis. Revisa la disponibilidad y cuota de Gemini, y vuelve a intentar.",
        }

    def finish(current):
        if current.get("lease") == lease:
            current.update(**changes, updated_at=now())
        return current

    item = await run_in_threadpool(db.mutate, "pqrs", key, finish)
    return public_pqr(item)


@app.get("/pqrs/{key}/file", tags=["Documentos"])
def download(key: str, request: Request, user=Depends(current_user), db=Depends(store)):
    item = owned(db, "pqrs", key, user["id"])
    if not item["file"]:
        raise HTTPException(404, "Esta PQR no tiene documento.")
    document = owned(db, "uploads", item["file"]["id"], user["id"])
    data = request.app.state.files.read(document["storage_key"])
    return Response(
        data,
        media_type=document["mime"],
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{quote(document['filename'])}"
        },
    )
