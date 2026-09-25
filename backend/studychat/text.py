"""Shared page normalization; richer source mapping is introduced with verification."""

import re
import unicodedata

NORMALIZATION_VERSION = "nfkc-dehyphen-ws-v1"


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"([^\W\d_])-\s*\n\s*([^\W\d_])", r"\1\2", text)
    return " ".join(text.split())


def split_page(text: str, size: int = 2400, overlap: int = 240) -> list[dict]:
    if size <= 0 or not 0 <= overlap < size:
        raise ValueError("invalid_chunk_size")
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        if text[start:end].strip():
            chunks.append({"text": text[start:end], "start_offset": start, "end_offset": end})
        if end == len(text):
            break
        start = end - overlap
    return chunks
