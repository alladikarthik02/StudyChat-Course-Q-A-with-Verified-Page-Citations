import asyncio
import hashlib
import os
from contextlib import suppress
from uuid import UUID, uuid4

from fastapi import HTTPException, UploadFile

from studychat.async_utils import settled_thread
from studychat.config import Settings
from studychat.extraction import IngestionError, extract_pdf
from studychat.providers import EmbeddingProvider, validate_embeddings
from studychat.repository import DocumentRepository
from studychat.text import split_page


class IngestionService:
    def __init__(self, settings: Settings, provider: EmbeddingProvider):
        self.settings = settings
        self.provider = provider
        self.repo = DocumentRepository(settings)
        self.tasks: dict[UUID, asyncio.Task] = {}
        self.busy = False
        self.storage = settings.storage_dir.resolve()
        self.storage.mkdir(parents=True, exist_ok=True, mode=0o700)

    def path(self, doc_id: UUID):
        return self.storage / f"{doc_id}.pdf"

    async def recover(self):
        for row in await settled_thread(self.repo.recover):
            self.path(row["id"]).unlink(missing_ok=True)
            if row["state"] == "deleting":
                await settled_thread(self.repo.remove, row["id"])
        for path in self.storage.glob("*.part"):
            path.unlink(missing_ok=True)
        known = await settled_thread(self.repo.all_ids)
        for path in self.storage.glob("*.pdf"):
            if path.stem not in known:
                path.unlink(missing_ok=True)

    async def accept(self, upload: UploadFile):
        if self.busy:
            raise HTTPException(429, "ingestion_busy")
        self.busy = True
        doc_id = uuid4()
        staging = self.storage / f"{doc_id}.part"
        try:
            digest = hashlib.sha256()
            total = 0
            with staging.open("xb") as stream:
                os.chmod(staging, 0o600)
                while block := await upload.read(64 * 1024):
                    if total == 0 and not block.startswith(b"%PDF-"):
                        raise HTTPException(422, "invalid_pdf_signature")
                    total += len(block)
                    if total > self.settings.max_upload_bytes:
                        raise HTTPException(413, "upload_limit")
                    digest.update(block)
                    stream.write(block)
            if total == 0:
                raise HTTPException(422, "empty_upload")
            filename = (upload.filename or "document.pdf").replace("\\", "/").split("/")[-1]
            filename = "".join(c for c in filename if c.isprintable())[:255] or "document.pdf"
            # Publish the file first; readiness remains gated on the final database commit.
            staging.replace(self.path(doc_id))
            await settled_thread(
                self.repo.create, doc_id, filename, digest.hexdigest(), self.provider.model
            )
            task = asyncio.create_task(self.run(doc_id))
            self.tasks[doc_id] = task
            task.add_done_callback(lambda done: self.finished(doc_id, done))
            return {"id": doc_id, "state": "processing"}
        except BaseException:
            try:
                await settled_thread(self.repo.fail, doc_id, "upload_interrupted")
            finally:
                staging.unlink(missing_ok=True)
                self.path(doc_id).unlink(missing_ok=True)
                self.busy = False
            raise
        finally:
            await upload.close()

    def finished(self, doc_id: UUID, task: asyncio.Task):
        self.tasks.pop(doc_id, None)
        # Retrieve exceptions so outages do not print raw database or document details.
        if not task.cancelled():
            task.exception()

    async def run(self, doc_id: UUID):
        try:
            result = await extract_pdf(self.path(doc_id), self.settings)
            chunks = []
            for page, text in enumerate(result["pages"], 1):
                chunks.extend(
                    dict(c, page=page, ordinal=i, kind="page")
                    for i, c in enumerate(split_page(text))
                )
            metadata = result["metadata"]
            if metadata:
                chunks.append(
                    dict(
                        page=0,
                        ordinal=0,
                        kind="metadata",
                        text=metadata,
                        start_offset=0,
                        end_offset=len(metadata),
                    )
                )
            vectors = []
            async with asyncio.timeout(self.settings.embedding_timeout_seconds):
                for start in range(0, len(chunks), 32):
                    batch = chunks[start : start + 32]
                    result_vectors = await self.provider.embed([c["text"] for c in batch])
                    validate_embeddings(
                        result_vectors, len(batch), self.settings.embedding_dimensions
                    )
                    vectors.extend(result_vectors)
            await settled_thread(self.repo.publish, doc_id, result["pages"], chunks, vectors)
        except asyncio.CancelledError:
            # A shielded final commit may have completed just before cancellation.
            row = await settled_thread(self.repo.get, doc_id)
            if not row or row["state"] != "ready":
                try:
                    await settled_thread(self.repo.fail, doc_id, "interrupted")
                finally:
                    self.path(doc_id).unlink(missing_ok=True)
            raise
        except Exception as exc:
            code = str(exc) if isinstance(exc, IngestionError) else "ingestion_failed"
            if isinstance(exc, TimeoutError):
                code = "embedding_timeout"
            self.path(doc_id).unlink(missing_ok=True)
            await settled_thread(self.repo.fail, doc_id, code)
        finally:
            self.busy = False

    async def delete(self, doc_id: UUID):
        if not await settled_thread(self.repo.mark_deleting, doc_id):
            return
        task = self.tasks.get(doc_id)
        if task:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task
        try:
            self.path(doc_id).unlink(missing_ok=True)
        except OSError:
            raise HTTPException(503, "cleanup_pending") from None
        await settled_thread(self.repo.remove, doc_id)

    async def close(self):
        tasks = list(self.tasks.values())
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
