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
    rows.append({**case, "retrieved": ids, "hit": case["expected"] in ids if case["expected"] else None})
print(json.dumps({"provider": bench.provider.kind, "embedding_model": bench.provider.embedding_model, "method": args.method, "rows": rows}, indent=2))
