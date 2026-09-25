import asyncio
import fcntl
from contextlib import asynccontextmanager

import psycopg
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware

from studychat.config import Settings
from studychat.db import ready
from studychat.documents import router
from studychat.guards import RequestGuards
from studychat.ingestion import IngestionService
from studychat.providers import EmbeddingProvider, FixtureProvider


def create_app(
    settings: Settings | None = None, provider: EmbeddingProvider | None = None
) -> FastAPI:
    settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(app):
        app.state.ingestion_available = False
        if not await asyncio.to_thread(ready, settings):
            yield
            return
        service = IngestionService(settings, provider or FixtureProvider())
        # One local service owns both database recovery and the storage directory.
        with (service.storage / ".service.lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with psycopg.connect(
                settings.database_url.get_secret_value(), connect_timeout=3, autocommit=True
            ) as lease:
                acquired = lease.execute("SELECT pg_try_advisory_lock(83012002)").fetchone()[0]
                if not acquired:
                    raise RuntimeError("StudyChat already owns this database; use one API worker")
                try:
                    await service.recover()
                    app.state.ingestion = service
                    app.state.ingestion_available = True
                    yield
                finally:
                    app.state.ingestion_available = False
                    await service.close()

    app = FastAPI(title="StudyChat", version="0.2.0", lifespan=lifespan)
    app.state.settings = settings
    app.state.ingestion_available = False
    app.add_middleware(RequestGuards, max_body_bytes=settings.max_upload_bytes + 64 * 1024)
    app.add_middleware(
        TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1", "testserver"]
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["Content-Type"],
    )
    app.include_router(router)

    @app.exception_handler(psycopg.Error)
    async def database_error(request, exc):
        return JSONResponse({"detail": "database_unavailable"}, status_code=503)

    @app.get("/health")
    def health():
        return {"status": "ok", "provider_mode": settings.provider_mode}

    @app.get("/ready")
    def readiness():
        ok = app.state.ingestion_available and ready(settings)
        return JSONResponse({"ready": ok}, status_code=200 if ok else 503)

    return app


app = create_app()
