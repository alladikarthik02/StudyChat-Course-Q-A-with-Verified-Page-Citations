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
