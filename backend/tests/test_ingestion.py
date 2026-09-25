import asyncio
import io
import time
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfReader, PdfWriter
from studychat.db import connection
from studychat.main import create_app
from studychat.providers import FixtureProvider
from studychat.repository import DocumentRepository

pytestmark = pytest.mark.integration


def wait_document(client, doc_id):
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        response = client.get(f"/documents/{doc_id}")
        assert response.status_code == 200
        row = response.json()
        if row["state"] in {"ready", "failed"}:
            return row
        time.sleep(0.02)
    pytest.fail("ingestion did not finish")


def upload(client, body, name="lecture.pdf"):
    response = client.post("/documents", files={"file": (name, body, "application/pdf")})
    assert response.status_code == 202, response.text
    return response.json()["id"]


def test_upload_preserves_pages_metadata_vectors_and_delete(db_settings, pdf_bytes):
    with TestClient(create_app(db_settings)) as client:
        assert client.get("/ready").status_code == 200
        doc_id = upload(client, pdf_bytes(), "../../lecture.pdf")
        row = wait_document(client, doc_id)
        assert row["state"] == "ready", row
        assert row["filename"] == "lecture.pdf"
        assert row["page_count"] == 2
        assert len(client.get("/documents").json()) == 1
        assert client.get(f"/documents/{doc_id}/file").content == pdf_bytes()
        with connection(db_settings) as conn:
            pages = conn.execute("SELECT * FROM pages ORDER BY page").fetchall()
            assert len(pages) == 2 and "gravity" in pages[0]["text"]
            chunks = conn.execute(
                "SELECT page,kind,vector_dims(embedding) AS dim FROM chunks"
            ).fetchall()
            assert len(chunks) == 3
            assert {c["dim"] for c in chunks} == {1536}
            assert [c for c in chunks if c["kind"] == "metadata"][0]["page"] == 0
        assert client.delete(f"/documents/{doc_id}").status_code == 204
        assert client.delete(f"/documents/{doc_id}").status_code == 204
        assert client.get(f"/documents/{doc_id}/file").status_code == 404
        assert not (db_settings.storage_dir / f"{doc_id}.pdf").exists()
        with connection(db_settings) as conn:
            assert conn.execute("SELECT count(*) AS n FROM chunks").fetchone()["n"] == 0
            assert conn.execute("SELECT count(*) AS n FROM pages").fetchone()["n"] == 0


@pytest.mark.parametrize(
    "case,code",
    [
        ("malformed", "invalid_pdf"),
        ("encrypted", "encrypted_pdf"),
        ("blank", "no_extractable_text"),
        ("pages", "page_limit"),
        ("text", "text_limit"),
    ],
)
def test_failed_extraction_has_no_partial_index(db_settings, pdf_bytes, case, code):
    body = pdf_bytes()
    if case == "malformed":
        body = b"%PDF-1.7\nbroken"
    elif case == "encrypted":
        writer = PdfWriter(clone_from=PdfReader(io.BytesIO(body)))
        writer.encrypt("secret")
        stream = io.BytesIO()
        writer.write(stream)
        body = stream.getvalue()
    elif case == "blank":
        body = pdf_bytes([""])
    elif case == "pages":
        db_settings.max_pages = 1
    elif case == "text":
        db_settings.max_text_chars = 5
    with TestClient(create_app(db_settings)) as client:
        doc_id = upload(client, body)
        row = wait_document(client, doc_id)
        assert row["state"] == "failed"
        assert row["error_code"] == code
        assert not (db_settings.storage_dir / f"{doc_id}.pdf").exists()
        with connection(db_settings) as conn:
            assert conn.execute("SELECT count(*) AS n FROM chunks").fetchone()["n"] == 0


def test_upload_limits_origin_and_paths(db_settings, pdf_bytes):
    db_settings.max_upload_bytes = 1000
    with TestClient(create_app(db_settings)) as client:
        assert client.post("/documents", files={"file": ("x.pdf", b"bad")}).status_code == 422
        assert client.post("/documents", files={"file": ("x.pdf", b"")}).status_code == 422
        assert client.post("/documents", files={"file": ("x.pdf", pdf_bytes())}).status_code == 413
        assert client.post("/documents", content=b"x" * 70000).status_code == 413
        assert (
            client.post("/documents", headers={"Origin": "https://evil.example"}).status_code == 403
        )
        assert client.get("/documents/not-a-uuid/file").status_code == 422
        assert client.get(f"/documents/{uuid4()}/file").status_code == 404
        assert client.get("/documents").json() == []
        assert not list(db_settings.storage_dir.glob("*.pdf"))
        assert not list(db_settings.storage_dir.glob("*.part"))


class BrokenProvider(FixtureProvider):
    async def embed(self, texts):
        return [[1.0] for _ in texts]


def test_embedding_failure_is_atomic_and_retryable(db_settings, pdf_bytes):
    with TestClient(create_app(db_settings, BrokenProvider())) as client:
        doc_id = upload(client, pdf_bytes())
        row = wait_document(client, doc_id)
        assert row["error_code"] == "ingestion_failed"
        with connection(db_settings) as conn:
            assert conn.execute("SELECT count(*) AS n FROM pages").fetchone()["n"] == 0
    with TestClient(create_app(db_settings)) as client:
        retry = upload(client, pdf_bytes())
        assert wait_document(client, retry)["state"] == "ready"


class SlowProvider(FixtureProvider):
    async def embed(self, texts):
        await asyncio.sleep(60)
        return await super().embed(texts)


def test_concurrent_ingestion_rejected_and_delete_cancels(db_settings, pdf_bytes):
    with TestClient(create_app(db_settings, SlowProvider())) as client:
        doc_id = upload(client, pdf_bytes())
        response = client.post("/documents", files={"file": ("x.pdf", pdf_bytes())})
        assert response.status_code == 429
        assert client.get(f"/documents/{doc_id}/file").status_code == 404
        assert client.delete(f"/documents/{doc_id}").status_code == 204
        assert client.get(f"/documents/{doc_id}").status_code == 404
        assert not (db_settings.storage_dir / f"{doc_id}.pdf").exists()
        with connection(db_settings) as conn:
            assert conn.execute("SELECT count(*) AS n FROM chunks").fetchone()["n"] == 0


def test_embedding_timeout(db_settings, pdf_bytes):
    db_settings.embedding_timeout_seconds = 0.01
    with TestClient(create_app(db_settings, SlowProvider())) as client:
        doc_id = upload(client, pdf_bytes())
        assert wait_document(client, doc_id)["error_code"] == "embedding_timeout"


def test_restart_recovers_interrupted_jobs_and_orphan_files(db_settings):
    db_settings.storage_dir.mkdir()
    doc_id = uuid4()
    repo = DocumentRepository(db_settings)
    repo.create(doc_id, "x.pdf", "0" * 64, "fixture-hash-v1")
    (db_settings.storage_dir / f"{doc_id}.pdf").write_bytes(b"interrupted")
    (db_settings.storage_dir / f"{uuid4()}.pdf").write_bytes(b"orphan")
    (db_settings.storage_dir / "upload.part").write_bytes(b"partial")
    with TestClient(create_app(db_settings)) as client:
        row = client.get(f"/documents/{doc_id}").json()
        assert row["state"] == "failed" and row["error_code"] == "interrupted"
        assert not list(db_settings.storage_dir.glob("*.pdf"))
        assert not list(db_settings.storage_dir.glob("*.part"))


def test_publish_transaction_rolls_back_on_invalid_vector(db_settings):
    doc_id = uuid4()
    repo = DocumentRepository(db_settings)
    repo.create(doc_id, "x.pdf", "0" * 64, "fixture-hash-v1")
    chunk = dict(page=1, ordinal=0, kind="page", text="hello", start_offset=0, end_offset=5)
    with pytest.raises(Exception):
        repo.publish(doc_id, ["hello"], [chunk], [[1.0]])
    with connection(db_settings) as conn:
        assert conn.execute("SELECT count(*) AS n FROM pages").fetchone()["n"] == 0
    assert repo.get(doc_id)["state"] == "processing"


def test_delete_prevents_late_publish(db_settings):
    doc_id = UUID("11111111-1111-1111-1111-111111111111")
    repo = DocumentRepository(db_settings)
    repo.create(doc_id, "x.pdf", "0" * 64, "fixture-hash-v1")
    repo.mark_deleting(doc_id)
    assert repo.publish(doc_id, ["hello"], [], []) is False


def test_partial_embedding_batches_do_not_publish_pages(db_settings, pdf_bytes):
    class FailSecondBatch(FixtureProvider):
        calls = 0

        async def embed(self, texts):
            self.calls += 1
            if self.calls == 2:
                raise RuntimeError("private-provider-error-sentinel")
            return await super().embed(texts)

    provider = FailSecondBatch()
    with TestClient(create_app(db_settings, provider)) as client:
        doc_id = upload(client, pdf_bytes(["Page content for embedding."] * 35))
        row = wait_document(client, doc_id)
        assert provider.calls == 2
        assert row["error_code"] == "ingestion_failed"
        assert "sentinel" not in str(row)
        with connection(db_settings) as conn:
            assert conn.execute("SELECT count(*) AS n FROM pages").fetchone()["n"] == 0
            assert conn.execute("SELECT count(*) AS n FROM chunks").fetchone()["n"] == 0


def test_pending_delete_is_recovered_on_restart(db_settings):
    db_settings.storage_dir.mkdir()
    doc_id = uuid4()
    repo = DocumentRepository(db_settings)
    repo.create(doc_id, "x.pdf", "0" * 64, "fixture-hash-v1")
    repo.mark_deleting(doc_id)
    (db_settings.storage_dir / f"{doc_id}.pdf").write_bytes(b"pending-delete")
    with TestClient(create_app(db_settings)) as client:
        assert client.get(f"/documents/{doc_id}").status_code == 404
        assert not list(db_settings.storage_dir.glob("*.pdf"))


def test_second_api_cannot_recover_an_active_workers_jobs(db_settings):
    with TestClient(create_app(db_settings)):
        with pytest.raises(BlockingIOError):
            with TestClient(create_app(db_settings)):
                pass


def test_citation_sources_require_selected_ready_retrieved_pages(db_settings, pdf_bytes):
    with TestClient(create_app(db_settings)) as client:
        first = UUID(upload(client, pdf_bytes()))
        assert wait_document(client, first)["state"] == "ready"
        second = UUID(upload(client, pdf_bytes(["Another document at page one."])))
        assert wait_document(client, second)["state"] == "ready"
        repo = DocumentRepository(db_settings)
        sources = repo.citation_pages([first], [(first, 1), (first, 0), (second, 1)])
        assert len(sources) == 1
        assert sources[0].document_id == first and sources[0].page == 1
        assert repo.citation_pages([], [(first, 1)]) == []
        assert repo.citation_pages([first], [(first, 999)]) == []
        repo.mark_deleting(first)
        assert repo.citation_pages([first], [(first, 1)]) == []


def test_ingested_pdf_to_verified_citation_uses_original_page(db_settings, pdf_bytes):
    from studychat.citations import verify_answer

    with TestClient(create_app(db_settings)) as client:
        doc_id = UUID(upload(client, pdf_bytes()))
        assert wait_document(client, doc_id)["state"] == "ready"
        sources = DocumentRepository(db_settings).citation_pages([doc_id], [(doc_id, 2)])
        result = verify_answer(
            'Evidence [D1 p.2 "Second page explains inertia."]', {"D1": doc_id}, sources
        )
        citation = result.citations[0]
        assert citation.status == "exact"
        assert citation.document_id == doc_id and citation.citation.page == 2
        assert sources[0].text[citation.source_start : citation.source_end] == citation.matched_text
