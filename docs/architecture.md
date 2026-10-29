# Architecture and boundaries

## Current architecture

The browser requests a same-origin FastAPI service. The service loads a small synthetic corpus, chunks it, creates a versioned Qdrant collection, retrieves candidates, packs evidence, and calls the selected answer provider. Both dense and lexical retrieval filter the selected example audience. Offline output quotes the actual passages. No tool can send email, edit accounts or perform business actions.

Qdrant is a separate service with persistent volume in Compose, or an embedded in-memory store for native development/tests. The lexical BM25 scorer runs over the small in-memory corpus. This makes the implementation inspectable but is not a scaling strategy for large corpora.

The provider abstraction separates embedding and generation transport from retrieval. The current provider selector pairs offline, Ollama or OpenAI embeddings and generation; independently mixing providers is a future extension. Nomic prefixes distinguish documents and queries. The same configured embedding model is used for indexing and queries. Model errors do not silently change provider.

## State and migration

A collection fingerprint includes provider, model name, chunker version and settings, and source content. A different configuration creates a different collection. Count validation prevents accepting a partially populated collection; incomplete teaching indexes are rebuilt. The in-process lock serializes construction, not distributed production writes. Use one worker.

This design does not prove consistency under concurrent ingestion from multiple processes. It does not implement a migration controller, alias cutover, dual writes or tombstone replay. The migration UI is explicitly a simulation. Pin immutable model versions or weight digests for real deployments; a name alone cannot detect an upstream alias change.

## Security and privacy boundaries

- Bound to loopback by default; Qdrant is internal to the Compose network.
- No authentication: example audience selection is not a security identity.
- Same-origin browser POST checks reduce casual cross-origin requests, but are not an authentication mechanism.
- File preview is local extraction only, with temporary files removed afterward. No upload is automatically indexed or sent to a provider.
- Upload size, page count, extracted text size and subprocess time are bounded. A production parser should run in a separately isolated worker with resource limits; this app runs extraction in the web service.
- File names are not used as executable commands. OCR subprocess calls use argument arrays and fixed executable names.
- Generated and source text are HTML-escaped in the UI. API keys are server environment variables and excluded from the ZIP.
- The model receives an instruction to treat evidence as untrusted. This alone is not a robust prompt-injection defense. The starter provides no action tools.
- Hosted mode sends document chunks and queries to the provider. `store=false` is not a zero-retention guarantee. Embeddings are not encryption.

## Evaluation and quality

The 18-question fixture is a small inspectable baseline. It includes 16 answerable questions and two negative cases, one involving a restricted source. Hit@k/MRR measure retrieval of the labelled source, not correctness or completeness of the answer. Negative cases can return irrelevant documents; do not hide those outcomes. The public fixture is not a secret held-out benchmark.

Add human-labelled paraphrases, multilingual queries, OCR noise, multi-source questions, adversarial content and realistic updates before making deployment claims. Separate retrieval, generation, citation support, abstention, isolation, cost and latency measures. Track worst cases and category regressions as well as aggregates.

## Production backlog

Authentication and verified ACLs; isolated ingestion workers; durable source registry; version-aware changes and deletion; model token budgets; structural PDF/table processing; cross-encoder experiments; cost and rate limits; retries/backpressure; privacy-aware traces; production migration/recovery; backup/restore tests; load tests; deployment-specific infrastructure.

## Portfolio evidence

Show a real demonstration, code walkthrough, measured test report and a failure analysis. Present this as an independent educational reference implementation. Reuse a real pilot later only with client permission and accurate descriptions of the work performed.
