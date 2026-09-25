import asyncio
import json
from contextlib import aclosing, suppress
from dataclasses import asdict
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator
from starlette.background import BackgroundTask

from studychat.citations import MAX_ANSWER_CHARS, verify_answer
from studychat.prompt import PROMPT_HASH
from studychat.providers import ProviderError, validate_embeddings
from studychat.retrieval import ContextError, retrieve, validate_documents

router = APIRouter(tags=["chat"])


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question: str = Field(min_length=1, max_length=4000)
    document_ids: list[UUID] = Field(min_length=1, max_length=10)
    live_consent: bool = False

    @field_validator("question")
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError("question_required")
        return value.strip()

    @field_validator("document_ids")
    @classmethod
    def unique(cls, value):
        if len(set(value)) != len(value):
            raise ValueError("duplicate_documents")
        return value


class ChatService:
    def __init__(self, settings, provider, repository):
        self.settings, self.provider, self.repo = settings, provider, repository
        self.active = set()

    def reserve(self):
        if len(self.active) >= self.settings.max_concurrent_chats:
            raise HTTPException(429, "chat_busy")
        request_id = str(uuid4())
        self.active.add(request_id)
        return request_id

    def release(self, request_id):
        self.active.discard(request_id)

    async def events(self, body: ChatRequest, request_id: str):
        seq = 0

        def event(kind, **payload):
            nonlocal seq
            seq += 1
            return {"event": kind, "request_id": request_id, "seq": seq, **payload}

        try:
            async with asyncio.timeout(self.settings.chat_timeout_seconds):
                yield event(
                    "start",
                    provider_mode=self.settings.provider_mode,
                    model=self.provider.chat_model,
                    prompt_hash=PROMPT_HASH,
                    threshold=self.settings.similarity_threshold,
                    threshold_label=self.settings.threshold_label,
                )
                vectors = await self.provider.embed([body.question])
                validate_embeddings(vectors, 1, self.settings.embedding_dimensions)
                chunks = await asyncio.to_thread(
                    retrieve, self.settings, body.document_ids, vectors[0], self.provider.model
                )
                aliases = {
                    f"D{i}": doc_id
                    for i, doc_id in enumerate(
                        sorted({c["document_id"] for c in chunks}, key=str), 1
                    )
                }
                inverse = {doc_id: alias for alias, doc_id in aliases.items()}
                for chunk in chunks:
                    chunk["alias"] = inverse[chunk["document_id"]]
                trace = [
                    {key: c[key] for key in ("document_id", "page", "similarity", "alias")}
                    for c in chunks
                ]
                if not chunks or chunks[0]["similarity"] < self.settings.similarity_threshold:
                    yield event("abstain", reason="insufficient_context", retrieval=trace)
                    yield event("done", outcome="abstained")
                    return
                answer = ""
                async with aclosing(self.provider.stream_answer(body.question, chunks)) as stream:
                    async for delta in stream:
                        if (
                            not isinstance(delta, str)
                            or len(answer) + len(delta) > MAX_ANSWER_CHARS
                        ):
                            raise ProviderError("answer_limit")
                        answer += delta
                        yield event("delta", text=delta)
                # Re-check readiness after generation: deletion invalidates this response.
                await asyncio.to_thread(
                    validate_documents, self.settings, body.document_ids, self.provider.model
                )
                pairs = list(dict.fromkeys((c["document_id"], c["page"]) for c in chunks))
                sources = await asyncio.to_thread(
                    self.repo.citation_pages, body.document_ids, pairs
                )
                if len(sources) != len(pairs):
                    raise ContextError("source_unavailable")
                verified = await asyncio.to_thread(verify_answer, answer, aliases, sources)
                yield event("verification", result=asdict(verified), retrieval=trace)
                yield event(
                    "done",
                    outcome="answered"
                    if verified.has_verified_citations
                    else "no_verified_citations",
                )
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            code = "chat_failed"
            if isinstance(exc, TimeoutError):
                code = "chat_timeout"
            elif isinstance(exc, (ContextError, ProviderError)):
                code = str(exc)
            yield event("error", code=code)
            yield event("done", outcome="error")
        finally:
            self.release(request_id)


async def sse(events):
    """Heartbeat while awaiting provider output; close pending work on disconnect."""
    pending = None
    async with aclosing(events):
        try:
            while True:
                pending = asyncio.create_task(anext(events))
                while not pending.done():
                    done, _ = await asyncio.wait({pending}, timeout=10)
                    if not done:
                        yield ": heartbeat\n\n"
                try:
                    item = pending.result()
                except StopAsyncIteration:
                    return
                yield f"event: {item['event']}\ndata: {json.dumps(item, default=str)}\n\n"
        finally:
            if pending and not pending.done():
                pending.cancel()
                with suppress(asyncio.CancelledError, StopAsyncIteration):
                    await pending


@router.post("/chat")
async def chat(body: ChatRequest, request: Request):
    if not request.app.state.ingestion_available:
        raise HTTPException(503, "database_unavailable")
    service = request.app.state.chat
    if service.settings.provider_mode == "live" and not body.live_consent:
        raise HTTPException(400, "live_transmission_consent_required")
    request_id = service.reserve()
    try:
        await asyncio.to_thread(
            validate_documents, service.settings, body.document_ids, service.provider.model
        )
    except ContextError as exc:
        service.release(request_id)
        raise HTTPException(409, str(exc)) from None
    except BaseException:
        service.release(request_id)
        raise
    return StreamingResponse(
        sse(service.events(body, request_id)),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
        background=BackgroundTask(service.release, request_id),
    )
