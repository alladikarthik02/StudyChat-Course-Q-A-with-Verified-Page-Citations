"""Deterministic PDF text normalization with conservative source-offset mapping."""

import re
import unicodedata
from array import array
from dataclasses import dataclass

import regex

NORMALIZATION_VERSION = "nfkc-grapheme-dehyphen-ws-v2"
DEHYPHEN = re.compile(r"(?<=[^\W\d_])-\s*\n\s*(?=[^\W\d_])")


@dataclass
class NormalizedText:
    text: str
    starts: array
    ends: array

    def source_span(self, start: int, end: int) -> tuple[int, int]:
        if not 0 <= start < end <= len(self.text):
            raise ValueError("invalid_normalized_span")
        return self.starts[start], self.ends[end - 1]


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = DEHYPHEN.sub("", text)
    return " ".join(text.split())


def normalize_with_offsets(source: str) -> NormalizedText:
    pieces = []
    starts, ends = array("I"), array("I")
    # A grapheme keeps combining marks and Hangul composition together. Each expanded
    # character maps conservatively to its original grapheme, including ligatures.
    for match in regex.finditer(r"\X", source):
        piece = unicodedata.normalize("NFKC", match.group())
        pieces.append(piece)
        starts.extend([match.start()] * len(piece))
        ends.extend([match.end()] * len(piece))
    text = "".join(pieces)
    if text != unicodedata.normalize("NFKC", source):
        # Never return an invented highlight if an unusual composition crosses a grapheme.
        raise ValueError("normalization_mapping_unsupported")
    kept, kept_starts, kept_ends = [], array("I"), array("I")
    cursor = 0
    for match in DEHYPHEN.finditer(text):
        kept.append(text[cursor : match.start()])
        kept_starts.extend(starts[cursor : match.start()])
        kept_ends.extend(ends[cursor : match.start()])
        cursor = match.end()
    kept.append(text[cursor:])
    kept_starts.extend(starts[cursor:])
    kept_ends.extend(ends[cursor:])
    text = "".join(kept)
    pieces, starts, ends = [], array("I"), array("I")
    for match in re.finditer(r"\s+|\S+", text):
        if match.group().isspace():
            if not pieces or match.end() == len(text):
                continue
            pieces.append(" ")
            starts.append(kept_starts[match.start()])
            ends.append(kept_ends[match.end() - 1])
        else:
            pieces.append(match.group())
            starts.extend(kept_starts[match.start() : match.end()])
            ends.extend(kept_ends[match.start() : match.end()])
    return NormalizedText("".join(pieces), starts, ends)


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
