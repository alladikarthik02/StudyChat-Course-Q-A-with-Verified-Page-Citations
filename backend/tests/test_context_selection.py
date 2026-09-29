import json

import httpx
import pytest
from studychat.config import Settings
from studychat.providers import OpenAIProvider, ProviderError
from studychat.retrieval import lexical_rank


@pytest.mark.parametrize("indices", [[0, 1], [], [2], [0, 0], [True], ["0"]])
async def test_context_selection_validates_indices(indices):
    def handle(request):
        body = json.loads(request.content)
        assert body["store"] is False
        assert body["text"]["format"]["strict"] is True
        assert "tools" not in body
        return httpx.Response(
            200,
            json={
                "status": "completed",
                "output": [
                    {
                        "type": "message",
                        "content": [
                            {"type": "output_text", "text": json.dumps({"indices": indices})}
                        ],
                    }
                ],
            },
        )

    client = httpx.AsyncClient(
        transport=httpx.MockTransport(handle), base_url="https://api.openai.com/v1/"
    )
    provider = OpenAIProvider(Settings(provider_mode="live", openai_api_key="dummy"), client)
    chunks = [{"text": "first"}, {"text": "second"}]
    try:
        if indices in ([0, 1], []) and all(type(i) is int for i in indices):
            assert await provider.select_context("question", chunks) == [chunks[i] for i in indices]
        else:
            with pytest.raises(ProviderError, match="context_selection_failed"):
                await provider.select_context("question", chunks)
    finally:
        await provider.close()


def test_rare_terms_outweigh_common_words():
    rows = [
        {"document_id": "d", "page": i, "ordinal": 0, "terms": terms}
        for i, terms in enumerate(
            [["common", "rare"], ["common", "other"], ["common", "other"], ["common", "other"]], 1
        )
    ]
    assert lexical_rank(rows, ["common", "rare"])[0]["page"] == 1
    assert lexical_rank(rows, []) == []
