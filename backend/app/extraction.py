from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph
from fastapi import HTTPException
from pypdf import PdfReader

from .config import settings

MIMES = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


def extract(filename: str, data: bytes):
    suffix = Path(filename).suffix.lower()
    if suffix not in MIMES:
        raise HTTPException(415, "Solo se permiten archivos Word (.docx) o PDF (.pdf).")
    if not data:
        raise HTTPException(422, "El archivo está vacío.")
    if len(data) > settings().max_upload_mb * 1024 * 1024:
        raise HTTPException(413, "El archivo supera el tamaño permitido.")
    try:
        if suffix == ".docx":
            with ZipFile(BytesIO(data)) as archive:
                entries = archive.infolist()
                if (
                    len(entries) > 1000
                    or sum(info.file_size for info in entries) > 20 * 1024 * 1024
                ):
                    raise HTTPException(
                        422, "El documento Word es demasiado complejo o grande al descomprimir."
                    )
                names = [entry.filename.lower() for entry in entries]
                if "word/document.xml" not in names:
                    raise HTTPException(422, "El archivo no es un documento Word válido.")
                if any(
                    "vbaproject" in name or name.startswith("word/embeddings/") for name in names
                ):
                    raise HTTPException(
                        422, "No se admite contenido activo ni objetos incrustados."
                    )
            doc = Document(BytesIO(data))
            lines = []
            for block in doc.iter_inner_content():
                if isinstance(block, Paragraph):
                    lines.append(block.text)
                elif isinstance(block, Table):
                    lines.extend(" | ".join(cell.text for cell in row.cells) for row in block.rows)
            text = "\n\n".join(lines).strip()
        else:
            if not data.startswith(b"%PDF-"):
                raise HTTPException(422, "El contenido no corresponde a un PDF válido.")
            pdf = PdfReader(BytesIO(data), strict=False)
            if pdf.is_encrypted:
                raise HTTPException(422, "El PDF está protegido. Sube una copia sin contraseña.")
            if len(pdf.pages) > 100:
                raise HTTPException(422, "El PDF no puede superar 100 páginas.")
            text = "\n\n".join(page.extract_text() or "" for page in pdf.pages).strip()
            if len(text) < 5:
                raise HTTPException(
                    422,
                    "El PDF no contiene texto seleccionable; puede ser un documento escaneado. Copia el texto en el formulario. OCR pendiente.",
                )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            422, "No se pudo leer el documento. Puede estar dañado o tener un formato incorrecto."
        ) from None
    if not text:
        raise HTTPException(422, "El documento no contiene texto.")
    if len(text) > settings().max_text_chars:
        raise HTTPException(
            422,
            f"El texto supera {settings().max_text_chars} caracteres. Sube un documento más corto.",
        )
    return text, MIMES[suffix]
