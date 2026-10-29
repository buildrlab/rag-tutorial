"""Bounded local extraction. OCR is available in the Docker image."""
import shutil
import subprocess
import tempfile
from io import BytesIO
from pathlib import Path

from pypdf import PdfReader


def extract(filename, content):
    suffix = Path(filename).suffix.lower()
    if len(content) > 3 * 1024 * 1024:
        raise ValueError("Use a file smaller than 3 MB for this teaching lab.")
    if suffix in {".txt", ".md"}:
        text = content.decode("utf-8")
        if not text.strip():
            raise ValueError("The file has no text.")
        return [{"page": 1, "text": text, "method": "text"}]
    if suffix not in {".pdf", ".png", ".jpg", ".jpeg"}:
        raise ValueError("Use PDF, PNG, JPEG, TXT or Markdown.")
    pages = []
    if suffix == ".pdf":
        reader = PdfReader(BytesIO(content))
        if reader.is_encrypted:
            raise ValueError("Unlock the PDF locally before importing it.")
        if len(reader.pages) > 12:
            raise ValueError("Use at most 12 PDF pages in the lab.")
        pages = [{"page": i + 1, "text": page.extract_text() or "", "method": "pdf-text"} for i, page in enumerate(reader.pages)]
    else:
        pages = [{"page": 1, "text": "", "method": "image"}]
    with tempfile.TemporaryDirectory() as directory:
        source = Path(directory) / ("source" + suffix)
        source.write_bytes(content)
        for page in pages:
            if len(page["text"].strip()) >= 40:
                continue
            if not shutil.which("tesseract") or (suffix == ".pdf" and not shutil.which("pdftoppm")):
                raise ValueError("This page needs OCR. Use the Docker quickstart, which includes Tesseract and Poppler.")
            image = source
            if suffix == ".pdf":
                out = Path(directory) / f'page-{page["page"]}'
                subprocess.run(["pdftoppm", "-f", str(page["page"]), "-l", str(page["page"]), "-singlefile", "-scale-to", "2200", "-png", str(source), str(out)], check=True, capture_output=True, timeout=30)
                image = out.with_suffix(".png")
            result = subprocess.run(["tesseract", str(image), "stdout", "-l", "eng"], check=True, capture_output=True, text=True, timeout=30)
            page["text"], page["method"] = result.stdout, "ocr-eng"
    if not any(p["text"].strip() for p in pages):
        raise ValueError("No usable text was extracted. Inspect the source quality or OCR language.")
    if sum(len(p["text"]) for p in pages) > 80_000:
        raise ValueError("Extracted content exceeds the 80,000-character lab limit.")
    return pages
