"""Rebuild the synthetic PDF fixtures. Requires reportlab, Pillow and pdftoppm."""
import json
import subprocess
from pathlib import Path

from reportlab.pdfgen import canvas
from reportlab.pdfbase.pdfmetrics import stringWidth

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "web/assets"
OUT.mkdir(parents=True, exist_ok=True)
sections = [
    ("Returns and refunds", "Unopened equipment can be returned within 30 days of delivery. A receipt or order number is required. Opened equipment is eligible only if it is faulty. Refunds use the original payment method and take 5 to 10 business days after inspection."),
    ("Exceptions", "Custom engraved equipment cannot be returned unless faulty. Subscription renewals are covered by a separate cancellation policy. Contact support before shipping a battery because transport restrictions apply."),
    ("Delivery", "Standard delivery takes 3 to 5 business days. Express delivery takes 1 to 2 business days. Delivery estimates start after dispatch, not when an order is placed. A tracking email is sent when the package leaves the warehouse."),
    ("Warranty", "The Trail 200 and Trail 400 have a two-year limited warranty against manufacturing defects. Proof of purchase is required. Accidental damage, water immersion and ordinary wear are excluded. Replacement parts retain the original warranty end date.")
]
width, height = 595, 842
c = canvas.Canvas(str(OUT / "northstar-handbook.pdf"), pagesize=(width, height))
c.setTitle("Northstar equipment handbook - synthetic RAG sample")
c.setAuthor("BuildrLab")
words, tokens = [], []


def frame(number, subtitle):
    c.setFillColorRGB(.13, .3, .26)
    c.rect(0, height-12, width, 12, stroke=0, fill=1)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(48, 791, "NORTHSTAR / FIELD EQUIPMENT")
    c.setFillColorRGB(.38, .44, .39)
    c.setFont("Helvetica", 8)
    c.drawRightString(547, 791, "SYNTHETIC TRAINING DOCUMENT")
    c.setFillColorRGB(.13, .21, .17)
    c.setFont("Times-Roman", 29)
    c.drawString(48, 744, subtitle)
    c.setFont("Helvetica", 10)
    c.setFillColorRGB(.4, .45, .4)
    c.drawString(48, 720, "An example document for the BuildrLab RAG Field Guide")
    c.setStrokeColorRGB(.82, .86, .8)
    c.line(48, 700, 547, 700)
    c.line(48, 55, 547, 55)
    c.setFont("Helvetica", 8)
    c.drawString(48, 38, "Fictional policies and products. Not real customer guidance.")
    c.drawRightString(547, 38, f"{number} / 2")


frame(1, "Equipment handbook")
y = 666
text_parts = []
for heading, paragraph in sections:
    text_parts.append(f"# {heading}\n{paragraph}")
    tokens.append("#")
    x = 48
    c.setFont("Helvetica-Bold", 14)
    c.setFillColorRGB(.13, .3, .26)
    c.drawString(x, y, heading)
    for token in heading.split():
        w = stringWidth(token, "Helvetica-Bold", 14)
        words.append({"index": len(tokens), "x": round(x, 2), "y": height-y-12, "width": round(w, 2), "height": 15})
        tokens.append(token)
        x += w + stringWidth(" ", "Helvetica-Bold", 14)
    y -= 27
    x = 48
    c.setFont("Helvetica", 11)
    c.setFillColorRGB(.2, .27, .22)
    line = []
    for token in paragraph.split():
        w = stringWidth(token, "Helvetica", 11)
        if x + w > 540:
            c.drawString(48, y, " ".join(line))
            line = []
            x, y = 48, y-18
        words.append({"index": len(tokens), "x": round(x, 2), "y": height-y-9, "width": round(w, 2), "height": 12})
        tokens.append(token)
        line.append(token)
        x += w + stringWidth(" ", "Helvetica", 11)
    if line:
        c.drawString(48, y, " ".join(line))
    y -= 47
assert y > 70, y
c.showPage()
frame(2, "Read the table as a table")
c.setFont("Helvetica", 11)
c.setFillColorRGB(.2, .27, .22)
c.drawString(48, 667, "A value needs its row label, column heading, units and footnotes.")
rows = [["Model", "Runtime*", "Weight", "Resistance"], ["Trail 200", "8 hours", "310 grams", "IP54"], ["Trail 400", "14 hours", "470 grams", "IP65"]]
xs = [48, 190, 310, 430, 547]
for i, row in enumerate(rows):
    top = 620 - i*47
    c.setFillColorRGB(*((.13, .3, .26) if i == 0 else (.93, .95, .91) if i%2 else (.98, .98, .96)))
    c.rect(48, top-47, 499, 47, stroke=0, fill=1)
    c.setFillColorRGB(*((1, 1, 1) if i == 0 else (.2, .27, .22)))
    c.setFont("Helvetica-Bold" if i == 0 else "Helvetica", 11)
    for x, value in zip(xs, row):
        c.drawString(x+12, top-28, value)
c.setFillColorRGB(.35, .41, .36)
c.setFont("Helvetica", 10)
c.drawString(48, 453, "* Runtime at 50% brightness and room temperature.")
c.drawString(48, 435, "Cold weather and maximum brightness reduce runtime.")
c.drawString(48, 417, "IP65 does not mean the device is safe for immersion.")
c.setFont("Helvetica-Bold", 14)
c.setFillColorRGB(.13, .3, .26)
c.drawString(48, 355, "A useful retrieval unit")
c.setFont("Helvetica", 11)
for i, line in enumerate(["Trail 400 | Battery runtime: 14 hours | Weight: 470 grams | IP65.", "Runtime measured at 50% brightness and room temperature.", "Keep the footnote with the row when it changes the meaning."]):
    c.drawString(48, 326-i*21, line)
c.setFont("Helvetica-Bold", 14)
c.drawString(48, 224, "A misleading fragment")
c.setFont("Helvetica", 11)
c.drawString(48, 195, '"14 hours | 470 grams | IP65" - which product, under what conditions?')
c.save()
(OUT / "handbook-map.json").write_text(json.dumps({"text": "\n\n".join(text_parts), "words": words}, indent=2))
subprocess.run(["pdftoppm", "-r", "110", "-png", str(OUT / "northstar-handbook.pdf"), str(OUT / "handbook-page")], check=True)
# Image-only PDF: there is deliberately no text layer, so the OCR path is exercised.
scan = canvas.Canvas(str(OUT / "northstar-scanned.pdf"), pagesize=(width, height))
scan.setTitle("Northstar image-only handbook - OCR fixture")
for i in [1, 2]:
    scan.drawImage(str(OUT / f"handbook-page-{i}.png"), 0, 0, width, height)
    scan.showPage()
scan.save()
print("Created 2 sample PDFs, 2 rendered pages and the word-coordinate map.")
