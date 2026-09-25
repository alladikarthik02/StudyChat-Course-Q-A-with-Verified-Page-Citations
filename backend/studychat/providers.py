"""Offline fixtures exercise plumbing; they are not semantic embeddings or eval evidence."""

import hashlib
import math
import re
from typing import Protocol


class EmbeddingProvider(Protocol):
    model: str
    dimensions: int

    async def embed(self, texts: list[str]) -> list[list[float]]: ...


class FixtureProvider:
    model = "fixture-hash-v1"
    dimensions = 1536
    chat_model = "fixture-extractive-v1"

    async def stream_answer(self, question, chunks):
        import asyncio
        import json

        from studychat.text import normalize

        chunk = chunks[0]
        quote = normalize(chunk["text"])[:300]
        answer = (
            f"Offline fixture excerpt: {quote} "
            f"[{chunk['alias']} p.{chunk['page']} {json.dumps(quote)}]"
        )
        for start in range(0, len(answer), 24):
            await asyncio.sleep(0.005)
            yield answer[start : start + 24]

    async def close(self):
        pass

    async def embed(self, texts: list[str]) -> list[list[float]]:
        output = []
        for text in texts:
            vector = [0.0] * self.dimensions
            for token in re.findall(r"\w+", text.lower()) or ["empty"]:
                digest = hashlib.sha256(token.encode()).digest()
                vector[int.from_bytes(digest[:4], "big") % self.dimensions] += 1.0
            norm = math.sqrt(sum(v * v for v in vector))
            output.append([v / norm for v in vector])
        return output


def validate_embeddings(vectors: list[list[float]], count: int, dimensions: int):
    if len(vectors) != count:
        raise ValueError("embedding_count_mismatch")
    for vector in vectors:
        if len(vector) != dimensions or not all(math.isfinite(v) for v in vector):
            raise ValueError("embedding_dimension_or_value_invalid")
        if not any(vector):
            raise ValueError("embedding_zero_vector")


class ProviderError(Exception):
    """A safe public error code, never a provider response body."""


class OpenAIProvider:
    model = "text-embedding-3-small"
    dimensions = 1536

    def __init__(self, settings, client=None):
        import httpx

        self.settings = settings
        self.chat_model = settings.chat_model
        self.client = client or httpx.AsyncClient(
            base_url="https://api.openai.com/v1/",
            headers={"Authorization": f"Bearer {settings.openai_api_key.get_secret_value()}"},
            timeout=httpx.Timeout(30, connect=10),
        )

    async def embed(self, texts):
        import httpx

        try:
            response = await self.client.post(
                "embeddings",
                json={
                    "model": self.model,
                    "input": texts,
                    "dimensions": self.dimensions,
                    "encoding_format": "float",
                },
            )
            response.raise_for_status()
            data = response.json()["data"]
            if sorted(item["index"] for item in data) != list(range(len(texts))):
                raise ValueError("embedding_indices")
            vectors = [item["embedding"] for item in sorted(data, key=lambda row: row["index"])]
            validate_embeddings(vectors, len(texts), self.dimensions)
            return vectors
        except (httpx.HTTPError, ValueError, KeyError, TypeError):
            raise ProviderError("embedding_provider_error") from None

    async def stream_answer(self, question, chunks):
        import json

        import httpx

        from studychat.prompt import SYSTEM_PROMPT, prompt_input

        try:
            async with self.client.stream(
                "POST",
                "responses",
                json={
                    "model": self.chat_model,
                    "instructions": SYSTEM_PROMPT,
                    "input": prompt_input(question, chunks),
                    "stream": True,
                    "store": False,
                    "max_output_tokens": self.settings.max_output_tokens,
                },
            ) as response:
                response.raise_for_status()
                completed = False
                async for line in response.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    if len(line) > 200_000:
                        raise ProviderError("provider_event_limit")
                    event = json.loads(line[5:].strip())
                    event_type = event.get("type")
                    if event_type == "response.output_text.delta":
                        yield event["delta"]
                    elif event_type == "response.completed":
                        completed = True
                        break
                    elif event_type in {"error", "response.failed", "response.incomplete"}:
                        raise ProviderError("generation_incomplete")
                if not completed:
                    raise ProviderError("provider_disconnected")
        except (httpx.HTTPError, ValueError, KeyError, TypeError):
            raise ProviderError("chat_provider_error") from None

    async def close(self):
        await self.client.aclose()
