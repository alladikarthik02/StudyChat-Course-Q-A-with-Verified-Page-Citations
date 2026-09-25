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
