"""Quote matching only: successful verification is not a factuality/entailment claim."""

import json
import math
import re
from dataclasses import dataclass, field
from typing import Literal
from uuid import UUID

from rapidfuzz.fuzz import ratio

from studychat.text import NORMALIZATION_VERSION, normalize, normalize_with_offsets

VERIFIER_VERSION = "quote-v1"
MAX_ANSWER_CHARS = 100_000
MAX_CITATIONS = 100
MAX_QUOTE_CHARS = 2000
MAX_PAGE_CHARS = 2_000_000
MAX_FUZZY_PAGE_CHARS = 100_000
MAX_FUZZY_COMPARISONS = 10_000  # Shared across an entire answer.
CITATION_START = re.compile(r"\[(?:D\d+\b|p\.|[A-Za-z]\w*\s+p\.)")
CITATION = re.compile(r'\[(D[1-9]\d{0,5})\s+p\.([0-9]{1,6})\s+("(?:[^"\\]|\\.)*")\s*\]')
NUMBERS = re.compile(r"(?<!\w)[+-]?\d+(?:[.,]\d+)*(?:%|\b)")
NEGATIONS = re.compile(r"\b(?:no|not|never|neither|nor|without|cannot)\b|\b\w+n['’]t\b", re.I)


@dataclass(frozen=True)
class Citation:
    start: int
    end: int
    raw: str
    alias: str | None = None
    page: int | None = None
    quote: str | None = None
    error: str | None = None


@dataclass(frozen=True)
class PageSource:
    document_id: UUID
    page: int
    text: str


@dataclass
class Verification:
    citation: Citation
    status: Literal["exact", "approximate", "removed"]
    reason: str | None = None
    document_id: UUID | None = None
    score: float | None = None
    source_start: int | None = None
    source_end: int | None = None
    matched_text: str | None = None
    ambiguous: bool = False


@dataclass
class VerifiedAnswer:
    text: str
    citations: list[Verification]
    has_verified_citations: bool
    normalization_version: str = NORMALIZATION_VERSION
    verifier_version: str = VERIFIER_VERSION
    fuzzy_algorithm: str = "rapidfuzz-normalized-indel-ratio-word-windows-v1"
    warnings: list[str] = field(default_factory=list)


def parse_citations(answer: str) -> list[Citation]:
    if len(answer) > MAX_ANSWER_CHARS:
        raise ValueError("answer_limit")
    citations = []
    cursor = 0
    while match := CITATION_START.search(answer, cursor):
        if len(citations) >= MAX_CITATIONS:
            raise ValueError("citation_limit")
        start = match.start()
        in_quote = escaped = False
        first_close = None
        end = None
        for i in range(start + 1, len(answer)):
            char = answer[i]
            if char == "]" and first_close is None:
                first_close = i + 1
            if escaped:
                escaped = False
            elif char == "\\" and in_quote:
                escaped = True
            elif char == '"':
                in_quote = not in_quote
            elif char == "]" and not in_quote:
                end = i + 1
                break
            elif char == "\n" and not in_quote:
                break
        end = end or first_close or len(answer)
        raw = answer[start:end]
        parsed = CITATION.fullmatch(raw)
        alias, page, quote, error = None, None, None, "malformed_citation"
        if parsed:
            alias, page_string, encoded_quote = parsed.groups()
            page = int(page_string)
            try:
                quote = json.loads(encoded_quote)
                error = None if quote.strip() else "empty_quote"
                if len(quote) > MAX_QUOTE_CHARS:
                    error = "quote_limit"
            except ValueError:
                pass
        citations.append(Citation(start, end, raw, alias, page, quote, error))
        cursor = end
    return citations


def sensitive_tokens(text: str):
    return NUMBERS.findall(text), [m.group().casefold() for m in NEGATIONS.finditer(text)]


def find_fuzzy(quote: str, page: str, threshold: float, budget: list[int]):
    """Bounded word-aligned candidates; no claim of exhaustive approximate substring search."""
    if len(page) > MAX_FUZZY_PAGE_CHARS:
        return None, "fuzzy_page_limit"
    words = list(re.finditer(r"\S+", page))
    quote_words = len(quote.split())
    best = None
    sensitive_mismatch = False
    for first in range(len(words)):
        for count in range(max(1, quote_words - 2), quote_words + 3):
            if first + count > len(words):
                continue
            start, end = words[first].start(), words[first + count - 1].end()
            length = end - start
            # Maximum possible indel similarity by length, before allocating/scoring.
            if 2 * min(len(quote), length) / (len(quote) + length) < threshold:
                continue
            if budget[0] == 0:
                return None, "comparison_limit"
            budget[0] -= 1
            candidate = page[start:end]
            score = ratio(quote, candidate, score_cutoff=threshold * 100) / 100
            if score < threshold:
                continue
            if sensitive_tokens(quote) != sensitive_tokens(candidate):
                sensitive_mismatch = True
                continue
            if best is None or score > best[0]:
                best = [score, start, end, False]
            elif score == best[0] and (start, end) != (best[1], best[2]):
                best[3] = True
    return best, "sensitive_token_mismatch" if sensitive_mismatch else "quote_not_found"


def verify_answer(
    answer: str,
    aliases: dict[str, UUID],
    sources: list[PageSource],
    *,
    allow_fuzzy: bool = True,
    threshold: float = 0.90,
) -> VerifiedAnswer:
    """Pass only server-selected, retrieved ready pages; never accept browser-supplied sources."""
    if not math.isfinite(threshold) or not 0.90 <= threshold <= 1.0:
        raise ValueError("invalid_fuzzy_threshold")
    if len(sources) > 6 or sum(len(source.text) for source in sources) > MAX_PAGE_CHARS:
        raise ValueError("citation_context_limit")
    pages = {}
    for source in sources:
        key = (source.document_id, source.page)
        if key in pages:
            raise ValueError("duplicate_page_source")
        pages[key] = source.text
    parsed = parse_citations(answer)
    budget = [MAX_FUZZY_COMPARISONS]
    normalized = {}
    results = []
    for citation in parsed:

        def removed(reason):
            return Verification(citation, "removed", reason=reason)

        if citation.error:
            results.append(removed(citation.error))
            continue
        doc_id = aliases.get(citation.alias)
        if doc_id is None:
            results.append(removed("unknown_document"))
            continue
        if citation.page is None or citation.page <= 0:
            results.append(removed("invalid_page"))
            continue
        key = (doc_id, citation.page)
        if key not in pages:
            results.append(removed("page_not_in_context"))
            continue
        source = pages[key]
        if len(source) > MAX_PAGE_CHARS:
            results.append(removed("page_limit"))
            continue
        quote = normalize(citation.quote or "")
        if not quote or len(quote) > MAX_QUOTE_CHARS:
            results.append(removed("empty_quote" if not quote else "quote_limit"))
            continue
        if key not in normalized:
            try:
                normalized[key] = normalize_with_offsets(source)
            except ValueError:
                results.append(removed("normalization_mapping_unsupported"))
                continue
        page = normalized[key]
        start = page.text.find(quote)
        if start >= 0:
            end = start + len(quote)
            score, status = 1.0, "exact"
            ambiguous = page.text.find(quote, start + 1) >= 0
        elif allow_fuzzy and len(quote) >= 20:
            match, reason = find_fuzzy(quote, page.text, threshold, budget)
            if match is None:
                results.append(removed(reason))
                continue
            score, start, end, ambiguous = match
            status = "approximate"
        else:
            results.append(removed("quote_not_found"))
            continue
        source_start, source_end = page.source_span(start, end)
        results.append(
            Verification(
                citation,
                status,
                document_id=doc_id,
                score=score,
                source_start=None if ambiguous else source_start,
                source_end=None if ambiguous else source_end,
                matched_text=source[source_start:source_end],
                ambiguous=ambiguous,
            )
        )
    pieces, cursor = [], 0
    for result in results:
        pieces.append(answer[cursor : result.citation.start])
        pieces.append("[citation removed]" if result.status == "removed" else result.citation.raw)
        cursor = result.citation.end
    pieces.append(answer[cursor:])
    return VerifiedAnswer(
        "".join(pieces),
        results,
        any(r.status != "removed" for r in results),
        warnings=["Quote matching does not establish that an answer is factually correct."],
    )
