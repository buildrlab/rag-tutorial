"""Run explicit retrieval evaluations. Live providers require --allow-provider-calls."""
import argparse
import json
from pathlib import Path
from app.retrieval import Workbench

parser = argparse.ArgumentParser()
parser.add_argument("--method", choices=["keyword", "vector", "hybrid"], default="hybrid")
parser.add_argument("--allow-provider-calls", action="store_true")
args = parser.parse_args()
root = Path(__file__).resolve().parent.parent
bench = Workbench(json.loads((root / "data/documents.json").read_text()))
if bench.provider.kind != "offline" and not args.allow_provider_calls:
    parser.error("Use --allow-provider-calls to opt in to model calls and any provider charges.")
rows = []
for case in json.loads((root / "data/evaluation.json").read_text()):
    hits = bench.retrieve(case["question"], method=args.method)["evidence"]
    ids = list(dict.fromkeys(c["document_id"] for c in hits))
    rank = ids.index(case["expected"]) + 1 if case["expected"] in ids else None
    rows.append({**case, "retrieved": ids, "hit": bool(rank) if case["expected"] else None,
                 "reciprocal_rank": 1 / rank if rank else 0, "empty_result": not ids})
summary = {}
for split in sorted({r.get("split", "all") for r in rows}):
    answerable = [r for r in rows if r.get("split", "all") == split and r["expected"]]
    if answerable:
        summary[split] = {"cases": len(answerable), "hit_at_k": sum(r["hit"] for r in answerable) / len(answerable),
                          "mrr": sum(r["reciprocal_rank"] for r in answerable) / len(answerable)}
print(json.dumps({"provider": bench.provider.kind, "embedding_model": bench.provider.embedding_model, "method": args.method, "summary": summary, "rows": rows}, indent=2))
