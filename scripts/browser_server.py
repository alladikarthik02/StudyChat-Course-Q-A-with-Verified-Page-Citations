"""Disposable fixture API for browser tests. Never starts against a non-test database."""

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

import uvicorn  # noqa: E402
from studychat.config import Settings  # noqa: E402
from studychat.db import migrate  # noqa: E402
from studychat.main import create_app  # noqa: E402

url = os.environ.get("STUDYCHAT_TEST_DATABASE_URL", "")
if not url.split("?")[0].endswith("_test"):
    raise SystemExit("Set STUDYCHAT_TEST_DATABASE_URL to a dedicated _test database")
with tempfile.TemporaryDirectory(prefix="studychat-browser-") as directory:
    settings = Settings(database_url=url, storage_dir=Path(directory), provider_mode="fixture")
    migrate(settings)
    uvicorn.run(create_app(settings), host="127.0.0.1", port=8000, log_level="warning")
