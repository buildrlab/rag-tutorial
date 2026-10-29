"""Dense + lexical retrieval, RRF, evidence budgets and versioned Qdrant indexes."""
import hashlib
import json
import math
import os
import threading
from collections import Counter

from qdrant_client import QdrantClient, models

from .chunking import chunk_documents
from .providers import Provider, terms


def bm25(query, chunks):
    tokens = [terms(c["text"]) for c in chunks]
    n = len(tokens)
    avg = sum(map(len, tokens)) / max(n, 1) or 1
    df = Counter(t for doc in tokens for t in set(doc))
    scores = []
    for chunk, doc in zip(chunks, tokens):
        tf = Counter(doc)
        score = sum(math.log(1 + (n - df[t] + .5) / (df[t] + .5)) * tf[t] * 2.5 /
                    (tf[t] + 1.5 * (1 - .75 + .75 * len(doc) / avg)) for t in set(terms(query)) if tf[t])
        if score > 0:
            scores.append((chunk["id"], score))
    return sorted(scores, key=lambda p: (-p[1], p[0]))


def fuse(rankings, constant=60):
    scores = Counter()
    for ranking in rankings:
        for rank, (identity, _) in enumerate(ranking, 1):
            scores[identity] += 1 / (constant + rank)
    return sorted(scores.items(), key=lambda p: (-p[1], p[0]))


def pack_context(chunks, budget):
    packed, used = [], 0
    for chunk in chunks:
        # Never truncate a chunk and then pretend its full citation supported the answer.
        if used + chunk["words"] <= budget:
            packed.append(chunk)
            used += chunk["words"]
    return packed


class Workbench:
    def __init__(self, documents, path=":memory:", provider=None):
        self.documents = documents
        self.provider = provider or Provider()
        self.lock = threading.RLock()
        url = os.getenv("QDRANT_URL")
        self.db = QdrantClient(url=url, timeout=30) if url else QdrantClient(location=":memory:") if path == ":memory:" else QdrantClient(path=path)
        self.indexes = {}

    def build(self, strategy, size, overlap):
        with self.lock:
            contract = {"provider": self.provider.kind, "model": self.provider.embedding_model, "chunker": "word-v1", "strategy": strategy, "size": size, "overlap": overlap, "documents": self.documents}
            fingerprint = hashlib.sha256(json.dumps(contract, sort_keys=True).encode()).hexdigest()[:20]
            name = "rag_" + fingerprint
            if name in self.indexes:
                return name, self.indexes[name]
            chunks = chunk_documents(self.documents, strategy, size, overlap)
            if not self.db.collection_exists(name):
                vectors = []
                for start in range(0, len(chunks), 32):
                    vectors.extend(self.provider.embed([c["text"] for c in chunks[start:start + 32]]))
                dimension = len(vectors[0])
                self.db.create_collection(name, vectors_config=models.VectorParams(size=dimension, distance=models.Distance.COSINE))
                self.db.upsert(name, points=[models.PointStruct(id=c["id"], vector=v, payload=c) for c, v in zip(chunks, vectors)], wait=True)
            # Interrupted builds are rebuilt, not accepted just because a collection exists.
            if self.db.count(name, exact=True).count != len(chunks):
                self.db.delete_collection(name)
                return self.build(strategy, size, overlap)
            self.indexes[name] = chunks
            return name, chunks

    def retrieve(self, question, strategy="sections", size=100, overlap=15, method="hybrid", top_k=3, scope="public", budget=500):
        with self.lock:
            name, all_chunks = self.build(strategy, size, overlap)
            allowed = ["public"] if scope == "public" else ["public", "engineering"]
            chunks = [c for c in all_chunks if c.get("audience", "public") in allowed]
            by_id = {c["id"]: c for c in chunks}
            lexical = bm25(question, chunks)
            dense = []
            if method != "keyword":
                vector = self.provider.embed([question], query=True)[0]
                hits = self.db.query_points(name, query=vector, query_filter=models.Filter(must=[models.FieldCondition(key="audience", match=models.MatchAny(any=allowed))]), limit=min(20, len(chunks)), with_payload=False).points
                dense = [(str(p.id), p.score) for p in hits if p.score > 0]
            ranked = lexical if method == "keyword" else dense if method == "vector" else fuse([lexical[:20], dense])
            # This is a transparent lexical teaching gate, NOT a calibrated semantic confidence score.
            if self.provider.kind == "offline":
                eligible = {i for i, _ in lexical}
                ranked = [(i, s) for i, s in ranked if i in eligible]
            selected = [{**by_id[i], "score": round(score, 5)} for i, score in ranked[:top_k] if i in by_id]
            return {"collection": name, "chunks_total": len(all_chunks), "candidates": selected, "evidence": pack_context(selected, budget), "ranking": {"keyword": lexical[:5], "vector": dense[:5]}, "method": method}
