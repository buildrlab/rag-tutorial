import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfReader

from app.chunking import split_text
from app.providers import Provider, ProviderError, teaching_vector
from app.retrieval import Workbench, pack_context

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def bench(monkeypatch):
    monkeypatch.delenv("QDRANT_URL", raising=False)
    monkeypatch.setenv("RAG_PROVIDER", "offline")
    return Workbench(json.loads((ROOT / "data/documents.json").read_text()))


def test_rule_and_exception_survive_section_chunking():
    text = "# Returns\n" + "return " * 35 + "\n\n# Exceptions\n" + "engraved " * 25
    chunks = split_text(text, "sections", 30, 5)
    assert all(len(c.split()) <= 30 for c in chunks)
    assert not any("Returns" in c and "Exceptions" in c for c in chunks)
    assert any("Exceptions" in c for c in chunks)


def test_fixed_overlap_terminates_and_covers_the_tail():
    text = " ".join(f"word{i}" for i in range(57))
    chunks = split_text(text, "fixed", 20, 19)
    assert chunks[-1].split()[-1] == "word56"
    assert len(chunks) == 38
    with pytest.raises(ValueError):
        split_text(text, "fixed", 20, 20)


@pytest.mark.parametrize("method", ["keyword", "vector", "hybrid"])
def test_permissions_filter_every_retrieval_path(bench, method):
    result = bench.retrieve("NORTHSTAR-STAGING-42 staging deployment", method=method, scope="public", top_k=6)
    assert all(c["audience"] == "public" for c in result["evidence"])
    result = bench.retrieve("NORTHSTAR-STAGING-42 staging deployment", method=method, scope="engineering", top_k=6)
    assert any(c["document_id"] == "engineering" for c in result["evidence"])


def test_matching_evidence_and_citations(bench):
    result = bench.retrieve("How long can unopened equipment be returned?")
    assert result["evidence"][0]["document_id"] == "returns"
    answer = bench.provider.answer("returns?", result["evidence"])
    assert "[1]" in answer["text"] and "30 days" in answer["text"]
    assert "no language model" in answer["text"]


def test_unknown_words_do_not_get_a_fake_answer(bench):
    result = bench.retrieve("zzzyx quuxxyz blorpyx")
    assert not result["evidence"]
    assert bench.provider.answer("unknown", [])["abstained"] is True


def test_whole_chunk_budget():
    chunks = [{"id": "a", "words": 80}, {"id": "b", "words": 30}]
    assert pack_context(chunks, 50) == [chunks[1]]


def test_new_chunk_configuration_gets_separate_index(bench):
    a, _ = bench.build("fixed", 40, 5)
    b, _ = bench.build("fixed", 60, 5)
    assert a != b
    assert bench.db.collection_exists(a) and bench.db.collection_exists(b)


def test_hash_is_deterministic_but_not_semantic():
    assert teaching_vector("battery warranty") == teaching_vector("warranty battery")
    assert teaching_vector("refund") != teaching_vector("money back")


def test_provider_rejects_incomplete_batch(monkeypatch):
    monkeypatch.setenv("RAG_PROVIDER", "ollama")
    p = Provider()
    monkeypatch.setattr(p, "request", lambda *a, **k: {"embeddings": [[1., 0.]]})
    with pytest.raises(ProviderError):
        p.embed(["one", "two"])


def test_nomic_query_and_document_prefixes(monkeypatch):
    monkeypatch.setenv("RAG_PROVIDER", "ollama")
    monkeypatch.delenv("EMBEDDING_MODEL", raising=False)
    p, requests = Provider(), []
    def request(url, body):
        requests.append(body)
        return {"embeddings": [[1., 0.]]}
    monkeypatch.setattr(p, "request", request)
    p.embed(["battery"])
    p.embed(["battery"], query=True)
    assert requests[0]["input"] == ["search_document: battery"]
    assert requests[1]["input"] == ["search_query: battery"]
    assert requests[0]["truncate"] is False


def test_pdf_and_scanned_fixture_are_different():
    digital = PdfReader(ROOT / "web/assets/northstar-handbook.pdf")
    scanned = PdfReader(ROOT / "web/assets/northstar-scanned.pdf")
    assert len(digital.pages) == len(scanned.pages) == 2
    assert "Custom engraved" in digital.pages[0].extract_text()
    assert not scanned.pages[0].extract_text().strip()


def test_api_validation_and_file_preview(monkeypatch):
    monkeypatch.delenv("QDRANT_URL", raising=False)
    from app.main import app
    client = TestClient(app)
    assert client.get("/api/health").status_code == 200
    assert client.post("/api/query", json={"question": "returns", "size": 20, "overlap": 20}).status_code == 422
    assert client.post("/api/query", json={"question": "returns"}, headers={"Origin": "https://untrusted.example"}).status_code == 403
    response = client.post("/api/extract", files={"file": ("sample.txt", b"A synthetic local preview.")})
    assert response.status_code == 200
    assert response.json()["pages"][0]["text"] == "A synthetic local preview."
    assert client.get("/api/source/.env").status_code == 404


def test_source_word_map_matches_text():
    source = json.loads((ROOT / "web/assets/handbook-map.json").read_text())
    words = source["text"].split()
    assert all(0 <= w["index"] < len(words) and 0 <= w["y"] < 842 for w in source["words"])
    assert len(source["words"]) == len(words) - 4  # four heading markers have no printed glyph


def test_openai_adapter_uses_responses_and_does_not_store(monkeypatch):
    monkeypatch.setenv("RAG_PROVIDER", "openai")
    monkeypatch.setenv("GENERATION_MODEL", "test-model")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-not-real")
    p, calls = Provider(), []
    def request(url, body, headers=None):
        calls.append((url, body))
        return {"output": [{"type": "reasoning", "summary": []}, {"type": "message", "content": [{"type": "output_text", "text": "Return it within 30 days. [1]"}]}], "usage": {"input_tokens": 10, "output_tokens": 8}}
    monkeypatch.setattr(p, "request", request)
    result = p.answer("Return period?", [{"title": "Policy", "text": "Returns within 30 days.", "page": 1}])
    assert result["text"].endswith("[1]")
    assert calls[0][0] == "https://api.openai.com/v1/responses"
    assert calls[0][1]["store"] is False
    assert "untrusted data" in calls[0][1]["instructions"]


def test_provider_rejects_mismatched_dimensions(monkeypatch):
    monkeypatch.setenv("RAG_PROVIDER", "ollama")
    p = Provider()
    monkeypatch.setattr(p, "request", lambda *a, **k: {"embeddings": [[1., 0.], [1.]]})
    with pytest.raises(ProviderError):
        p.embed(["one", "two"])
