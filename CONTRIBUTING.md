# Contributing

Keep the no-key first run working. Every new lesson should have a plain-language explanation, a runnable experiment, a useful failure case, links to primary documentation, and an accessible textual alternative for visuals.

For code changes, run `uv run pytest -q`, the appropriate provider contract tests, and the Docker smoke test when runtime/Compose/ingestion changes. Do not put real customer data, credentials or invented benchmark claims into fixtures. Version prompts, data and evaluation settings with the source.

Dependencies are resolved in `uv.lock` and exported to `requirements.lock`. After changing `pyproject.toml`, run `uv lock`, `uv sync`, then `uv export --no-dev --no-hashes --no-emit-project --format requirements-txt -o requirements.lock`. Rebuild the source download using `python scripts/package.py` after changes.

The PDF fixture generator needs reportlab, Pillow and Poppler's `pdftoppm`; these are authoring dependencies only. Generated PDFs, page PNGs and the coordinate map are committed so a new learner does not need those packages.
