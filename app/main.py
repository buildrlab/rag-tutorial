import json
import os
import re
import shutil
import time
import uuid
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, model_validator

from .chunking import split_text
from .ingest import extract
from .providers import ProviderError
from .retrieval import Workbench

ROOT = Path(__file__).resolve().parent.parent
docs = json.loads((ROOT / "data/documents.json").read_text())
bench = Workbench(docs)
app = FastAPI(title="RAG Field Guide API", version="0.1.0", description="Local teaching application. Do not expose this unauthenticated lab to the internet.")


@app.middleware("http")
async def protect_local_lab(request: Request, call_next):
    # Prevent cross-origin browser writes to a local unauthenticated teaching server.
    origin = request.headers.get("origin")
    if request.method == "POST" and origin and origin != str(request.base_url).rstrip("/"):
        return JSONResponse({"detail": "Cross-origin requests are not allowed."}, status_code=403)
    size = request.headers.get("content-length")
    if size and int(size) > 3 * 1024 * 1024 + 16_384:
        return JSONResponse({"detail": "Request exceeds the 3 MB lab limit."}, status_code=413)
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
    return response


class Settings(BaseModel):
    strategy: Literal["fixed", "paragraphs", "sections"] = "sections"
    size: int = Field(100, ge=20, le=400)
    overlap: int = Field(15, ge=0, le=100)
    method: Literal["keyword", "vector", "hybrid"] = "hybrid"
    top_k: int = Field(3, ge=1, le=6)
    scope: Literal["public", "engineering"] = "public"
    budget: int = Field(500, ge=50, le=1500)

    @model_validator(mode="after")
    def check_overlap(self):
        if self.overlap >= self.size:
            raise ValueError("Overlap must be smaller than the chunk size.")
        return self


class Query(Settings):
    question: str = Field(min_length=3, max_length=1000)


class ChunkRequest(BaseModel):
    text: str = Field(min_length=1, max_length=20_000)
    strategy: Literal["fixed", "paragraphs", "sections"] = "sections"
    size: int = Field(60, ge=20, le=400)
    overlap: int = Field(10, ge=0, le=100)


@app.get("/api/health")
def health():
    return {"status": "ok", "provider": bench.provider.kind, "embedding_model": bench.provider.embedding_model,
            "generation_model": bench.provider.generation_model, "documents": len(bench.documents),
            "vector_store": "Qdrant server" if os.getenv("QDRANT_URL") else "Qdrant embedded (in memory)",
            "ocr_available": bool(shutil.which("tesseract") and shutil.which("pdftoppm")),
            "data_leaves_machine": bench.provider.kind == "openai"}


@app.get("/api/documents")
def documents():
    return bench.documents


@app.post("/api/chunks")
def chunks(request: ChunkRequest):
    try:
        result = split_text(request.text, request.strategy, request.size, request.overlap)
        return {"chunks": result, "word_counts": [len(c.split()) for c in result]}
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@app.post("/api/query")
def query(request: Query):
    start = time.perf_counter()
    try:
        result = bench.retrieve(**request.model_dump())
        retrieval_ms = (time.perf_counter() - start) * 1000
        answer = bench.provider.answer(request.question, result["evidence"])
        citations = [int(v) for v in re.findall(r"\[(\d+)\]", answer["text"])]
        valid = all(1 <= i <= len(result["evidence"]) for i in citations)
        return {**result, "answer": answer["text"], "usage": answer["usage"], "abstained": answer["abstained"],
                "citation_ids_valid": valid, "citations_present": bool(citations), "citation_check": "IDs only; factual support still requires evaluation.",
                "retrieval_ms": round(retrieval_ms, 1), "total_ms": round((time.perf_counter() - start) * 1000, 1),
                "provider": bench.provider.kind, "context_words": sum(c["words"] for c in result["evidence"])}
    except ProviderError as exc:
        raise HTTPException(503, str(exc)) from exc


@app.post("/api/evaluate")
def evaluate(request: Settings):
    if bench.provider.kind != "offline":
        raise HTTPException(409, "The browser benchmark runs offline only. Use the evaluation CLI for an explicit live-model run.")
    cases = json.loads((ROOT / "data/evaluation.json").read_text())
    rows = []
    for case in cases:
        result = bench.retrieve(case["question"], **request.model_dump())
        found = list(dict.fromkeys(c["document_id"] for c in result["evidence"]))
        rank = found.index(case["expected"]) + 1 if case["expected"] in found else None
        rows.append({**case, "retrieved": found, "hit": bool(rank) if case["expected"] else None, "reciprocal_rank": 1 / rank if rank else 0,
                     "empty_result": not found})
    answerable = [r for r in rows if r["expected"]]
    return {"rows": rows, "hit_at_k": sum(r["hit"] for r in answerable) / len(answerable),
            "mrr": sum(r["reciprocal_rank"] for r in answerable) / len(answerable),
            "note": "Small synthetic retrieval benchmark, not answer accuracy. Negative cases are reported separately; a lexical gate can retrieve irrelevant evidence."}


@app.post("/api/extract")
async def extraction(file: UploadFile = File(...)):
    # Preview only. Uploading is not consent to send content to a hosted model.
    content = await file.read(3 * 1024 * 1024 + 1)
    try:
        pages = extract(file.filename or "upload.txt", content)
        return {"pages": pages, "filename": Path(file.filename or "upload").name,
                "note": "Extracted locally for inspection only. It has not been added to the index or sent to an inference provider."}
    except (ValueError, UnicodeError) as exc:
        raise HTTPException(422, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(422, "Extraction failed. Check the file format, OCR availability and page quality.") from exc


@app.get("/api/source/{name}")
def source(name: str):
    allowed = {"chunking.py", "providers.py", "retrieval.py", "ingest.py"}
    if name not in allowed:
        raise HTTPException(404)
    return FileResponse(ROOT / "app" / name, media_type="text/plain")


@app.get("/api/readme")
def readme():
    return FileResponse(ROOT / "README.md", media_type="text/plain")


app.mount("/", StaticFiles(directory=ROOT / "web", html=True), name="tutorial")
