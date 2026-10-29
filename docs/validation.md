# Validation record — 29 October 2026

This is a local teaching release, not a production service or a published BuildrLab deployment.

- 17 Python checks passed, including chunk limits and section boundaries, retrieval scope filtering, provider request contracts, malformed embeddings, extraction and API input validation.
- JavaScript syntax checks passed.
- Default Docker Compose stack built and ran with the Qdrant server. A running-service smoke check verified retrieval, actual OCR of the two-page scanned sample and the downloadable source archive.
- Native Ollama was tested with nomic-embed-text and qwen2.5:1.5b. A real embed → retrieve → generate query returned the correct 30-day return period in 6.44 seconds on the development laptop. This single measurement is not a performance benchmark. The small model omitted a citation; the UI reports missing citation IDs separately from invalid IDs. Human review of factual support remains necessary.
- The optional Ollama Docker image download failed with an unexpected EOF. Its Compose configuration validates, but that full container path has not been verified end to end. Native local inference was verified separately.
- Hosted OpenAI requests are covered by mocked contract checks. No paid live OpenAI request was made.
- Browser checks covered the BuildrLab-themed overview, live chunking, retrieval results, vector examples, evaluation, quiz feedback and the migration simulation. At a 390px emulated viewport the document width remained 390px; tables scroll inside their own containers. Desktop appearance was visually reviewed and captured.
- The 18-question synthetic hybrid fixture returned the expected document in the top three for all 16 answerable questions; MRR was 0.9375. One negative query returned no evidence; the other returned irrelevant public evidence. These are small-fixture retrieval results, not general answer accuracy. The negative failure is shown explicitly.

## Before public launch

Integrate the static lessons with BuildrLab routing and its shared navigation; resolve base paths. Keep model calls and uploads behind suitable authentication, quotas and operational controls. Add real-world, human-reviewed evaluation cases and broader browser/platform coverage. See architecture.md and buildrlab-integration.md for the remaining deployment work.
