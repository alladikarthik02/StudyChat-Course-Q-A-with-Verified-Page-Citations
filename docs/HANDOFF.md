# StudyChat handoff

StudyChat is a complete local personal learning project: PDF ingestion, hybrid retrieval, streaming answers, deterministic quote verification, source viewing and reproducible evaluation.

## Run locally

Follow RUNBOOK.md to start PostgreSQL, apply migrations, start the backend and frontend. Open http://127.0.0.1:5173, upload or select a ready PDF, acknowledge live transmission, ask a question, and open a citation chip to inspect its physical page. The local environment currently uses GPT-5.4 mini with low reasoning and a frozen development threshold of -1. Live calls incur API charges. Fixture mode runs offline and requires fixture-embedded documents.

The local backend and frontend run on ports 8000 and 5173. To stop, stop the terminal servers and use docker compose stop; this retains the database. Removing Docker volumes erases stored documents and requires migrations/reuploading.

## Verification and results

- 118 backend cases passed, including real PostgreSQL/pgvector integration.
- Eleven frontend unit tests, seven Chromium browser workflows, production build and Ruff passed.
- R1 code and handoff commits 5299ae0 and a373ba5 passed GitHub CI. Final publication CI is checked separately.
- Latest frozen synthetic evaluation: 20/20 cited answers and 19/20 passing page checks (100% coverage, 95% page accuracy).
- Original separate evaluation retained: 16/16 cited answers and 13/16 page checks (100%, 81.25%).

See EVALUATION_RESULTS.md for exact counts, uncertainty and limitations; PROJECT_EVIDENCE.md for learning goals; INTERVIEW_GUIDE.md for architecture discussion. Different datasets do not establish a controlled accuracy improvement.

## Privacy and reproduction

The API key remains in ignored .env. Source PDFs, extracted pages, corpus snapshots and raw responses remain in ignored eval/private. Public files contain code, synthetic questions, hashes, aggregate reports and documentation only. The user approved cloud chapter excerpt transmission to OpenAI for the evaluation.

The newest frozen capture is eval/private/cloud/heldout. Replay with eval/cite_eval.py using eval/private/cloud/questions.jsonl, corpus.json, heldout/records.jsonl and heldout/manifest.json. Select quote-off, quote-on or exact-only; no API request is needed for replay. Public reproduction uses generated fixtures; private coursework runs require matching permitted source PDFs.

## Scope and limitations

Single-user local use only: no public authentication, OCR or multi-user access controls. PDF diagrams can contain information absent from extracted text. Quote matches do not prove entailment. Synthetic labels can omit valid pages; failed checks were preserved. No human research or independent answer audit is claimed. The selector adds latency and cost; lexical scanning should be indexed for larger deployments. The -1 threshold preserves coverage but is not a validated unanswerable-question rejection policy.

## Publication audit

Checked current tracked filenames and file contents for the requested wording, PDF files, private evaluation paths and API-key patterns: no findings. Documentation links resolve locally. GitHub has one branch (main), no tags, releases or issues; its description, homepage and topics are empty. Historical commits are preserved pending separate authorization to rewrite history, so earlier document versions remain accessible through old commits. Do not describe current-file cleanup as historical erasure.
