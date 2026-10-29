# BuildrLab RAG tutorial integration

## Purpose

Make `/learn/rag` a useful, public technical resource that demonstrates Damien's ability to explain, implement and evaluate AI systems. Link the resource from an Upwork portfolio case study and the BuildrLab engineering section.

## Delivery plan

1. Integrate the tutorial shell and lesson content into the existing BuildrLab site after inspecting that repository's routing, design and deployment setup. Preserve the main site's established navigation.
2. Replace root-relative asset/API paths with a configurable base path or native routes. The current starter intentionally runs at `/`; copying it under a subdirectory without path changes will break links.
3. Keep the educational interactions available without signup. The vector toy and migration simulation run in the browser. Chunking can be ported to a shared browser implementation with parity tests.
4. Host actual inference behind a separate authenticated/rate-limited service, or keep it local-only and provide recorded, clearly labelled traces on the public site. Never expose this starter's unauthenticated API as a production endpoint.
5. Publish a versioned GitHub repository and ZIP download; link each code sample to the matching release. The current local repository has not been published to GitHub.
6. Add a three-minute walkthrough and an honest case study: problem, architecture, evaluation methodology, measured failures, trade-offs and next steps.
7. End the guide with a focused AI discovery consultation link. Keep the learning experience useful in its own right.

## Quality gates before public launch

- Fresh-machine Compose smoke test on macOS Apple Silicon and a Linux CI runner; a Windows Docker Desktop walkthrough.
- Live local-model test with documented hardware, versions, query results and latency. Hosted adapter contract tests plus an explicit live test when credentials are available.
- Keyboard and screen-reader checks, mobile layouts, accessible figures and full textual equivalents for PDF visuals.
- Citation review against primary documentation; no unsupported “best” or “production-ready” claims.
- Human review of the evaluation fixtures, separation of development and held-out reports, and a transparent report of negative cases.
- Production hosting design, privacy, upload restrictions, authentication, quotas and cost controls if visitors can submit their own data.

## Model-free lesson requirement

Start with fixed-vocabulary bag-of-words vectors and cosine similarity. Show exact numbers, shared words, synonyms that fail, negation that disappears and unknown words. Then show feature hashing, including collisions, before learned embeddings. Make the differences visible in prose and UI labels. Never present lexical feature hashing as semantic AI.

## Chunking visual requirement

Use the same original PDF, extracted text, coloured chunks and sample questions. Change one setting at a time. Explain fixed windows, paragraph packing and headings through runnable examples. Teach semantic, parent-child, table and code strategies as separate patterns with clear use cases and costs; implement them only with corresponding experiments and tests. Include a digital PDF, an image-only scanned PDF, and a table page with units and footnotes.
