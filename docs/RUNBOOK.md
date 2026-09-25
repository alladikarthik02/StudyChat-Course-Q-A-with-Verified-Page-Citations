# Local development

Requires Python 3.12, Node 24, pnpm 11.19.0, and Docker with Compose. Run commands from the repository root unless indicated. This version is a single-user local service; use one API worker. Do not expose it publicly.

```sh
python3.12 -m venv .venv
.venv/bin/pip install -r backend/requirements-dev.txt
docker compose up -d --wait
PYTHONPATH=backend .venv/bin/python -m studychat.db
PYTHONPATH=backend .venv/bin/uvicorn studychat.main:app --host 127.0.0.1 --port 8000
```

In another terminal:

```sh
cd frontend
pnpm install --frozen-lockfile
pnpm dev
```

Open http://127.0.0.1:5173. The frontend proxies `/api` to the local API. Health is at http://127.0.0.1:8000/health, readiness at `/ready`, and API documentation at `/docs`. Readiness is false until migrations succeed.

Configuration uses `STUDYCHAT_` environment variables or a local `.env` based on `.env.example`. The example database password is only for the loopback-bound development database. No provider key is needed: only fixture mode is implemented through T3. Fixture embeddings test storage and plumbing, not semantic retrieval quality.

## Checks

Create a separate test database once:

```sh
docker compose exec -T db createdb -U studychat studychat_test
```

Then:

```sh
.venv/bin/ruff check backend
STUDYCHAT_TEST_DATABASE_URL=postgresql://studychat:local-studychat@127.0.0.1:54329/studychat_test .venv/bin/pytest -q
cd frontend
pnpm build
```

Without `STUDYCHAT_TEST_DATABASE_URL`, database integration tests are explicitly skipped. A passing skipped suite is not evidence that database integration works. Test fixtures use a dedicated database and generated PDFs; never point tests at a database containing personal documents.

`docker compose stop` stops the local database while retaining its volume. Uploaded documents, dependencies, temporary files, environment files, and build output are ignored by Git. Commit exact dependency lockfiles, source, tests, configuration, and relevant documentation only.

## Dependency updates

Backend runtime and development locks are generated with pip-tools 7.6.1 from the corresponding `.in` files. Review changes and rerun checks when updating. Frontend dependencies are locked with pnpm. CI runs the backend suite with a real pgvector service and builds the frontend.

## Technical references

- [FastAPI lifecycle](https://fastapi.tiangolo.com/advanced/events/)
- [pgvector Python integration](https://github.com/pgvector/pgvector-python)
- [Vite setup](https://vite.dev/guide/)

## PDF API (T2)

Upload one PDF using multipart field `file` to `POST /documents`. A 202 response returns its ID; poll `GET /documents/{id}` until `ready` or `failed`. `GET /documents` lists state, `GET /documents/{id}/file` serves ready PDFs, and `DELETE /documents/{id}` removes the source plus derived rows. The upload UI is scheduled for T5; use `/docs` to exercise the API now.

Only one ingestion runs at a time; overlapping uploads return 429. Malformed, encrypted, empty-text, oversized, and over-limit PDFs fail with safe codes. Raw request size is bounded before multipart parsing, with a 64 KiB multipart allowance. Parser limits default to 60 seconds and 512 MiB. Linux enforces an address-space limit; macOS uses a 10 ms RSS watchdog with possible sampling overshoot. CPU time is also bounded. Uploaded files are mode 0600 in a private directory.

Startup acquires both storage and database ownership, recovers interrupted jobs, retries pending deletes, and removes staging/orphan files. Run one API worker. If the database was unavailable at startup, migrate/restore it and restart the API. Windows native parsing is not supported; use Linux or macOS. No deduplication is currently applied: reuploads get a new ID so failed attempts remain retryable.

[pypdf extraction limitations](https://pypdf.readthedocs.io/en/stable/user/extract-text.html) informed the isolated-parser design. This project handles text PDFs; OCR and browser highlighting arrive outside this checkpoint.

## Citation verification (T3)

`studychat.citations.verify_answer` consumes an answer, server-owned alias-to-document UUID mapping, and `PageSource` records from `DocumentRepository.citation_pages(selected_ids, retrieved_pages)`. It returns exact/approximate/removed statuses, reasons, scores, source spans, a rendered text with invalid citations replaced, and whether any citations survived. The text remains untrusted and must be escaped by T5's UI.

Use `[D1 p.2 "exact quote"]`; the quote string uses JSON escaping. Unknown aliases, metadata page 0, pages outside context, and malformed references cannot become verified citations. Pass `allow_fuzzy=False` for exact-only sensitivity runs. The default fuzzy score is a normalized indel ratio, not a probability of correctness. See [RapidFuzz's ratio definition](https://rapidfuzz.github.io/RapidFuzz/Usage/fuzz.html#ratio).

Run `pytest backend/tests/test_citations.py` with the project environment to exercise the 46 pure verifier tests. The full suite also tests real PDF ingestion through database-backed page selection into the verifier. Streaming integration is intentionally deferred to T4; there is no working chat endpoint yet.
