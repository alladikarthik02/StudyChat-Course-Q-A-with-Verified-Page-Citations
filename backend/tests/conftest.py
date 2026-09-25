import io
import os

import pytest
from reportlab.pdfgen import canvas
from studychat.config import Settings
from studychat.db import connection, migrate


@pytest.fixture
def pdf_bytes():
    def make(pages=("First page explains gravity.", "Second page explains inertia.")):
        stream = io.BytesIO()
        writer = canvas.Canvas(stream, invariant=True)
        writer.setTitle("Fixture lecture")
        writer.setSubject("Generated testing material")
        for text in pages:
            writer.drawString(40, 750, text)
            writer.showPage()
        writer.save()
        return stream.getvalue()

    return make


@pytest.fixture
def db_settings(tmp_path):
    url = os.environ.get("STUDYCHAT_TEST_DATABASE_URL")
    if not url:
        pytest.skip("Set STUDYCHAT_TEST_DATABASE_URL to a dedicated test database")
    # Never erase arbitrary databases: tests require the explicit _test suffix.
    if not url.split("?")[0].endswith("_test"):
        pytest.fail("Integration tests require a database name ending in _test")
    settings = Settings(database_url=url, storage_dir=tmp_path / "documents")
    migrate(settings)
    with connection(settings) as conn:
        conn.execute("TRUNCATE documents CASCADE")
    yield settings
    with connection(settings) as conn:
        conn.execute("TRUNCATE documents CASCADE")
