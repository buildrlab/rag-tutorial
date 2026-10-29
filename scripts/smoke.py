"""Check the running Docker stack, including OCR; no hosted model calls."""
import json
import os
from pathlib import Path
import httpx

base = os.getenv("RAG_BASE_URL", "http://127.0.0.1:8000")
with httpx.Client(base_url=base, timeout=120) as c:
    health = c.get("/api/health").raise_for_status().json()
    assert health["provider"] == "offline", "Smoke checks must not trigger paid model calls."
    answer = c.post("/api/query", json={"question": "How long do I have to return unopened equipment?"}).raise_for_status().json()
    assert "30 days" in answer["answer"]
    assert answer["evidence"][0]["document_id"] == "returns"
    source = Path(__file__).resolve().parent.parent / "web/assets/northstar-scanned.pdf"
    with source.open("rb") as f:
        result = c.post("/api/extract", files={"file": (source.name, f, "application/pdf")}).raise_for_status().json()
    assert all(p["method"] == "ocr-eng" for p in result["pages"])
    assert "30 days" in result["pages"][0]["text"]
    assert c.get("/starter.zip").status_code == 200
    print(json.dumps({"health": health, "retrieval": "passed", "scanned_pdf_ocr": "passed", "download": "passed"}, indent=2))
