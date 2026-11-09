"""Generate deterministic, fictitious Word/PDF input fixtures.

Requires python-docx, reportlab and Pillow. Not needed to run the application.
"""

from pathlib import Path

from docx import Document
from docx.shared import Inches, Pt, RGBColor
from PIL import Image, ImageDraw
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

root = Path(__file__).resolve().parents[1] / "samples"
root.mkdir(exist_ok=True)
title = "Solicitud de revisión de cobro"
paragraphs = [
    "Documento ficticio para probar la carga y extracción de texto en Nexo. No contiene información de personas reales.",
    "Referencia FAC-DEMO-004. Fecha 2026-11-08.",
    "Solicito revisar un cobro duplicado de $45.000 en la factura de mi servicio de internet. El pago se realizó una sola vez, pero el valor aparece dos veces en el detalle de la factura.",
    "Solicito verificar el origen del cargo y orientar los pasos para pedir una corrección si corresponde. Adjunto esta comunicación como soporte de la solicitud.",
    "Los nombres, referencias, importes y hechos de este documento son ejemplos de demostración.",
]
doc = Document()
section = doc.sections[0]
section.top_margin = section.bottom_margin = Inches(0.9)
section.left_margin = section.right_margin = Inches(1)
for name in ["Normal", "Title"]:
    doc.styles[name].font.name = "Calibri"
    doc.styles[name].font.color.rgb = RGBColor(0, 0, 0)
doc.styles["Normal"].font.size = Pt(11)
doc.styles["Normal"].paragraph_format.space_after = Pt(12)
doc.add_paragraph(title, "Title")
for paragraph in paragraphs:
    doc.add_paragraph(paragraph)
doc.save(root / "reclamo-ficticio.docx")
styles = getSampleStyleSheet()
styles.add(
    ParagraphStyle(
        name="DemoTitle",
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=25,
        textColor=colors.black,
        alignment=TA_LEFT,
        spaceAfter=22,
    )
)
styles["BodyText"].fontName = "Helvetica"
styles["BodyText"].fontSize = 11
styles["BodyText"].leading = 17
story = [Paragraph(title, styles["DemoTitle"])]
for paragraph in paragraphs:
    story += [Paragraph(paragraph, styles["BodyText"]), Spacer(1, 12)]
SimpleDocTemplate(
    str(root / "reclamo-ficticio.pdf"),
    rightMargin=72,
    leftMargin=72,
    topMargin=65,
    bottomMargin=65,
).build(story)
image = Image.new("RGB", (1200, 500), "white")
draw = ImageDraw.Draw(image)
draw.text((80, 80), "DOCUMENTO ESCANEADO FICTICIO", fill="black", font_size=38)
draw.text(
    (80, 160), "Esta pagina solo contiene una imagen.", fill="black", font_size=30
)
draw.text(
    (80, 220),
    "El sistema debe pedir texto manual: OCR pendiente.",
    fill="black",
    font_size=28,
)
pdf = canvas.Canvas(str(root / "escaneado-sin-texto.pdf"))
pdf.drawImage(ImageReader(image), 40, 500, width=515, height=215)
pdf.save()
(root / "documento-vacio.docx").write_bytes(b"")
(root / "documento-corrupto.pdf").write_bytes(b"%PDF-1.7\nDemo intentionally corrupt")
print("Generated 5 fixtures in", root)
