import asyncio
import json
from contextlib import aclosing
from uuid import UUID, uuid4

import httpx
import pytest
from fastapi.testclient import TestClient
from studychat.chat import ChatRequest, ChatService, sse
from studychat.config import Settings
from studychat.main import create_app
from studychat.providers import FixtureProvider, OpenAIProvider, ProviderError
from studychat.retrieval import retrieve
from test_ingestion import upload, wait_document


def events(response):
    return [
        json.loads(line[6:]) for line in response.text.splitlines() if line.startswith("data: ")
    ]


@pytest.mark.integration
def test_chat_retrieves_selected_document_and_verifies(db_settings, pdf_bytes):
    with TestClient(create_app(db_settings)) as client:
        first = upload(client, pdf_bytes())
        wait_document(client, first)
        second = upload(client, pdf_bytes(["Other document gravity gravity gravity"]))
        wait_document(client, second)
        response = client.post("/chat", json={"question": "gravity", "document_ids": [first]})
        assert response.status_code == 200
        output = events(response)
        assert [item["seq"] for item in output] == list(range(1, len(output) + 1))
        assert len({item["request_id"] for item in output}) == 1
        assert output[0]["event"] == "start"
        assert output[-1]["outcome"] == "answered"
        verification = output[-2]
        assert verification["result"]["has_verified_citations"]
        assert {c["document_id"] for c in verification["retrieval"]} == {first}
        assert all(c["page"] > 0 for c in verification["retrieval"])
        assert client.app.state.chat.active == set()


@pytest.mark.integration
def test_abstention_before_delta_and_invalid_document(db_settings, pdf_bytes):
    db_settings.similarity_threshold = 1
    with TestClient(create_app(db_settings)) as client:
        doc_id = upload(client, pdf_bytes())
        wait_document(client, doc_id)
        output = events(
            client.post("/chat", json={"question": "unrelatedxyz", "document_ids": [doc_id]})
        )
        assert [e["event"] for e in output] == ["start", "abstain", "done"]
        assert (
            client.post(
                "/chat", json={"question": "hi", "document_ids": [str(uuid4())]}
            ).status_code
            == 409
        )
        assert (
            client.post("/chat", json={"question": " ", "document_ids": [doc_id]}).status_code
            == 422
        )
        assert client.post("/chat", content=b"x" * 33000).status_code == 413


class FailingProvider(FixtureProvider):
    async def stream_answer(self, question, chunks):
        yield "Partial answer"
        raise ProviderError("chat_provider_error")


@pytest.mark.integration
def test_midstream_error_has_no_verification_or_retry(db_settings, pdf_bytes):
    with TestClient(create_app(db_settings, FailingProvider())) as client:
        doc_id = upload(client, pdf_bytes())
        wait_document(client, doc_id)
        output = events(
            client.post("/chat", json={"question": "gravity", "document_ids": [doc_id]})
        )
        assert [e["event"] for e in output] == ["start", "delta", "error", "done"]
        assert output[-1]["outcome"] == "error"
        assert client.app.state.chat.active == set()


@pytest.mark.integration
async def test_model_mismatch_and_stable_cosine_retrieval(db_settings, pdf_bytes):
    with TestClient(create_app(db_settings)) as client:
        doc_id = UUID(upload(client, pdf_bytes()))
        wait_document(client, doc_id)
        vector = (await FixtureProvider().embed(["gravity"]))[0]
        rows = retrieve(db_settings, [doc_id], vector, "fixture-hash-v1")
        assert rows[0]["page"] == 1
        assert rows == retrieve(db_settings, [doc_id], vector, "fixture-hash-v1")
        from studychat.retrieval import ContextError

        with pytest.raises(ContextError, match="embedding_model_mismatch"):
            retrieve(db_settings, [doc_id], vector, "other-model")


async def test_disconnect_closes_pending_generation_and_releases_slot(monkeypatch):
    provider = FixtureProvider()
    started, closed = asyncio.Event(), asyncio.Event()

    async def slow(question, chunks):
        try:
            started.set()
            await asyncio.sleep(60)
            yield "unreachable"
        finally:
            closed.set()

    provider.stream_answer = slow
    doc_id = uuid4()
    monkeypatch.setattr(
        "studychat.chat.retrieve",
        lambda *a: [{"document_id": doc_id, "page": 1, "similarity": 1, "text": "hello"}],
    )
    service = ChatService(Settings(), provider, None)
    request_id = service.reserve()
    generator = sse(
        service.events(ChatRequest(question="hello", document_ids=[doc_id]), request_id)
    )
    await anext(generator)  # start
    pending = asyncio.create_task(anext(generator))
    await started.wait()
    pending.cancel()
    with pytest.raises(asyncio.CancelledError):
        await pending
    await generator.aclose()
    assert closed.is_set() and not service.active


async def test_timeout_and_concurrency_limit(monkeypatch):
    class SlowEmbedding(FixtureProvider):
        async def embed(self, texts):
            await asyncio.sleep(1)

    service = ChatService(
        Settings(chat_timeout_seconds=0.01, max_concurrent_chats=1), SlowEmbedding(), None
    )
    request_id = service.reserve()
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        service.reserve()
    assert exc.value.status_code == 429
    output = [
        e
        async for e in service.events(
            ChatRequest(question="hi", document_ids=[uuid4()]), request_id
        )
    ]
    assert [e["event"] for e in output] == ["start", "error", "done"]
    assert output[1]["code"] == "chat_timeout" and not service.active


@pytest.mark.parametrize("status", [429, 500])
async def test_openai_errors_are_sanitized_without_retry(status):
    calls = []

    async def handle(request):
        calls.append(request)
        return httpx.Response(status, json={"error": "private-sentinel"})

    client = httpx.AsyncClient(
        transport=httpx.MockTransport(handle), base_url="https://api.openai.com/v1/"
    )
    provider = OpenAIProvider(Settings(provider_mode="live", openai_api_key="dummy"), client)
    async with aclosing(provider.stream_answer("question", [])) as stream:
        with pytest.raises(ProviderError, match="chat_provider_error"):
            await anext(stream)
    assert len(calls) == 1
    await provider.close()


async def test_openai_adapter_contract_and_completion():
    calls = []

    async def handle(request):
        body = json.loads(request.content)
        calls.append(body)
        if request.url.path.endswith("embeddings"):
            return httpx.Response(200, json={"data": [{"index": 0, "embedding": [1.0] * 1536}]})
        data = (
            "\n\n".join(
                "data: " + json.dumps(e)
                for e in [
                    {"type": "response.output_text.delta", "delta": "Hello"},
                    {"type": "response.completed"},
                ]
            )
            + "\n\n"
        )
        return httpx.Response(200, text=data, headers={"Content-Type": "text/event-stream"})

    client = httpx.AsyncClient(
        transport=httpx.MockTransport(handle), base_url="https://api.openai.com/v1/"
    )
    provider = OpenAIProvider(Settings(provider_mode="live", openai_api_key="dummy"), client)
    assert len((await provider.embed(["hi"]))[0]) == 1536
    assert [t async for t in provider.stream_answer("hi", [])] == ["Hello"]
    assert calls[1]["store"] is False and calls[1]["model"].endswith("2025-04-14")
    assert "tools" not in calls[1]
    await provider.close()


async def test_provider_disconnect_not_treated_as_complete():
    client = httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda r: httpx.Response(
                200, text='data: {"type":"response.output_text.delta","delta":"hi"}\n\n'
            )
        ),
        base_url="https://api.openai.com/v1/",
    )
    provider = OpenAIProvider(Settings(provider_mode="live", openai_api_key="dummy"), client)
    with pytest.raises(ProviderError, match="provider_disconnected"):
        _ = [t async for t in provider.stream_answer("hi", [])]
    await provider.close()


@pytest.mark.integration
def test_deleted_source_cannot_receive_verified_citation(db_settings, pdf_bytes):
    class DeletingProvider(FixtureProvider):
        async def stream_answer(self, question, chunks):
            from studychat.repository import DocumentRepository

            DocumentRepository(db_settings).mark_deleting(chunks[0]["document_id"])
            yield 'Claim [D1 p.1 "First page explains gravity."]'

    with TestClient(create_app(db_settings, DeletingProvider())) as client:
        doc_id = upload(client, pdf_bytes())
        wait_document(client, doc_id)
        output = events(
            client.post("/chat", json={"question": "gravity", "document_ids": [doc_id]})
        )
        assert output[-2]["event"] == "error" and output[-1]["outcome"] == "error"
        assert not any(e["event"] == "verification" for e in output)


@pytest.mark.integration
def test_live_transmission_requires_explicit_consent(db_settings, pdf_bytes):
    db_settings.provider_mode = "live"
    db_settings.openai_api_key = "not-used-by-fixture"
    with TestClient(create_app(db_settings, FixtureProvider())) as client:
        assert client.post("/documents", files={"file": ("x.pdf", pdf_bytes())}).status_code == 400
        assert (
            client.post(
                "/chat", json={"question": "hi", "document_ids": [str(uuid4())]}
            ).status_code
            == 400
        )
        assert "not-used" not in client.get("/config").text


@pytest.mark.integration
def test_no_surviving_citations_is_not_an_answered_outcome(db_settings, pdf_bytes):
    class UncitedProvider(FixtureProvider):
        async def stream_answer(self, question, chunks):
            yield 'Unsupported claim [D99 p.4 "invented"]'

    with TestClient(create_app(db_settings, UncitedProvider())) as client:
        doc_id = upload(client, pdf_bytes())
        wait_document(client, doc_id)
        output = events(
            client.post("/chat", json={"question": "gravity", "document_ids": [doc_id]})
        )
        assert output[-1]["outcome"] == "no_verified_citations"
        assert output[-2]["result"]["has_verified_citations"] is False
