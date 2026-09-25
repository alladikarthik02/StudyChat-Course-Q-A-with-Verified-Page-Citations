import json
import unicodedata
from uuid import UUID

import pytest
from studychat.citations import PageSource, parse_citations, verify_answer
from studychat.text import normalize, normalize_with_offsets

DOC = UUID("11111111-1111-1111-1111-111111111111")
OTHER = UUID("22222222-2222-2222-2222-222222222222")


def cite(quote, alias="D1", page=1):
    return f"[{alias} p.{page} {json.dumps(quote, ensure_ascii=False)}]"


def verify(quote, source, **kwargs):
    return verify_answer(cite(quote), {"D1": DOC}, [PageSource(DOC, 1, source)], **kwargs)


@pytest.mark.parametrize(
    "source,expected",
    [
        ("  A ﬁrst inter-\nnational\t lecture  ", "A first international lecture"),
        ("Cafe\u0301", "Café"),
        ("ＡＢＣ  ①", "ABC 1"),
        ("가", "가"),
        ("ｶﾞ", "ガ"),
        ("  \n\t", ""),
        ("real-time", "real-time"),
        ("cost 1-\n2", "cost 1- 2"),
        ("a- \r\nb", "ab"),
    ],
)
def test_normalization_and_offsets(source, expected):
    mapped = normalize_with_offsets(source)
    assert mapped.text == expected == normalize(source)
    assert len(mapped.starts) == len(mapped.ends) == len(expected)
    for start, end in zip(mapped.starts, mapped.ends):
        assert 0 <= start < end <= len(source)
    assert list(mapped.starts) == sorted(mapped.starts)


def test_ligature_and_combining_highlights_map_to_original_source():
    result = verify("first café", "Prefix: ﬁrst cafe\u0301. Suffix.")
    citation = result.citations[0]
    assert citation.status == "exact"
    assert citation.matched_text == "ﬁrst cafe\u0301"
    assert citation.source_start == 8
    assert citation.source_end == 18


def test_dehyphenated_quote_maps_over_original_linebreak():
    source = "The inter-\nnational standard applies."
    citation = verify("international standard", source).citations[0]
    assert citation.status == "exact"
    assert source[citation.source_start : citation.source_end] == "inter-\nnational standard"


@pytest.mark.parametrize(
    "quote,source", [("Gravity", "gravity"), ("hello!", "hello?"), ("cats", "cuts")]
)
def test_short_quotes_are_exact_only_and_case_punctuation_preserved(quote, source):
    assert verify(quote, source).citations[0].status == "removed"


def test_unknown_document_wrong_page_and_metadata_are_removed():
    answer = " ".join([cite("gravity", "D2"), cite("gravity", page=2), cite("gravity", page=0)])
    result = verify_answer(answer, {"D1": DOC}, [PageSource(DOC, 1, "gravity")])
    assert [c.reason for c in result.citations] == [
        "unknown_document",
        "page_not_in_context",
        "invalid_page",
    ]
    assert result.text == "[citation removed] [citation removed] [citation removed]"
    assert not result.has_verified_citations


def test_identical_page_number_in_another_document_cannot_pass():
    result = verify_answer(
        cite("gravity"),
        {"D1": DOC, "D2": OTHER},
        [PageSource(DOC, 1, "inertia"), PageSource(OTHER, 1, "gravity")],
    )
    assert result.citations[0].status == "removed"


@pytest.mark.parametrize(
    "answer",
    [
        '[D1 p.1 "unterminated]',
        '[D1 p.x "quote"]',
        '[D1 p.1 ""]',
        '[D1 p.1 "bad\\q"]',
        '[p.1 "quote"]',
        "[D1 p.1 quote]",
        '[D0 p.1 "quote"]',
        '[D1 p.-1 "quote"]',
        '[D1 p.1 "quote"',
        '[X1 p.1 "quote"]',
    ],
)
def test_malformed_citations_fail_closed(answer):
    result = verify_answer(answer, {"D1": DOC}, [PageSource(DOC, 1, "quote")])
    assert len(result.citations) == 1
    assert result.citations[0].status == "removed"
    assert result.text == "[citation removed]"


def test_escaped_quotes_and_brackets_parse_without_truncation():
    quote = 'The array [a] is called "input".'
    answer = "Intro " + cite(quote) + " end."
    parsed = parse_citations(answer)
    assert len(parsed) == 1 and parsed[0].quote == quote
    result = verify_answer(answer, {"D1": DOC}, [PageSource(DOC, 1, quote)])
    assert result.citations[0].status == "exact"
    assert result.text == answer


def test_regular_brackets_and_uncited_prose_are_not_claimed_as_verified():
    text = "A claim [with a side note] and no citations."
    result = verify_answer(text, {}, [])
    assert result.text == text
    assert result.citations == [] and not result.has_verified_citations


def test_approximate_match_is_labeled_and_exact_only_mode_removes_it():
    source = "The gravitational force attracts objects toward Earth."
    quote = "The gravitationel force attracts objects toward Earth."
    result = verify(quote, source)
    citation = result.citations[0]
    assert citation.status == "approximate"
    assert 0.90 <= citation.score < 1
    assert citation.matched_text == source
    assert verify(quote, source, allow_fuzzy=False).citations[0].status == "removed"


@pytest.mark.parametrize(
    "quote,source",
    [
        (
            "The measured acceleration is 9.9 meters per second.",
            "The measured acceleration is 9.8 meters per second.",
        ),
        (
            "This reaction is reversible under these conditions.",
            "This reaction is not reversible under these conditions.",
        ),
        (
            "The success rate was 99% in this controlled trial.",
            "The success rate was 90% in this controlled trial.",
        ),
    ],
)
def test_fuzzy_does_not_accept_number_or_negation_changes(quote, source):
    citation = verify(quote, source).citations[0]
    assert citation.status == "removed"
    assert citation.reason == "sensitive_token_mismatch"


def test_repeated_quote_keeps_page_but_omits_ambiguous_highlight():
    result = verify("same quote", "same quote appears twice: same quote")
    citation = result.citations[0]
    assert citation.status == "exact"
    assert citation.ambiguous
    assert citation.source_start is None and citation.source_end is None


def test_multiple_citations_preserve_prose_and_remove_only_invalid_reference():
    answer = "First " + cite("gravity") + ". Second " + cite("inertia", page=2) + "."
    result = verify_answer(answer, {"D1": DOC}, [PageSource(DOC, 1, "gravity")])
    assert result.text == "First " + cite("gravity") + ". Second [citation removed]."
    assert result.has_verified_citations


@pytest.mark.parametrize("threshold", [float("nan"), float("inf"), 0.89, 1.01])
def test_invalid_threshold_is_rejected(threshold):
    with pytest.raises(ValueError, match="invalid_fuzzy_threshold"):
        verify("quote", "quote", threshold=threshold)


def test_answer_citation_and_quote_limits_fail_closed():
    with pytest.raises(ValueError, match="answer_limit"):
        parse_citations("a" * 100001)
    with pytest.raises(ValueError, match="citation_limit"):
        parse_citations(" ".join([cite("a")] * 101))
    assert verify("a" * 2001, "a" * 2001).citations[0].reason == "quote_limit"


def test_fuzzy_comparison_budget_and_large_page_fail_closed(monkeypatch):
    monkeypatch.setattr("studychat.citations.MAX_FUZZY_COMPARISONS", 0)
    citation = verify(
        "A sufficiently long approximate quote.", "A sufficiently long approximete quote."
    ).citations[0]
    assert citation.reason == "comparison_limit"
    citation = verify("A sufficiently long approximate quote.", "x " * 50001).citations[0]
    assert citation.reason == "fuzzy_page_limit"


def test_duplicate_and_oversized_context_rejected():
    with pytest.raises(ValueError, match="duplicate_page_source"):
        verify_answer("", {}, [PageSource(DOC, 1, "a")] * 2)
    with pytest.raises(ValueError, match="citation_context_limit"):
        verify_answer("", {}, [PageSource(DOC, 1, "a" * 2000001)])


def test_quote_match_does_not_establish_claim_entailment():
    result = verify_answer(
        "The moon is cheese. " + cite("Gravity attracts masses."),
        {"D1": DOC},
        [PageSource(DOC, 1, "Gravity attracts masses.")],
    )
    assert result.has_verified_citations  # Quote exists; misleading claim is outside this check.
    assert result.warnings and "factually correct" in result.warnings[0]


def test_normalization_equivalence_for_unicode_fixture_corpus():
    # Deliberately covers compatibility expansions, combining marks, Hangul and emoji.
    for source in ["oﬃce", "e\u0301", "각", "ｶﾞ", "👩‍💻", "ﬁ\nA", "a\u0308\u0301", "①½"]:
        mapped = normalize_with_offsets(source)
        assert mapped.text == " ".join(unicodedata.normalize("NFKC", source).split())


def test_fuzzy_threshold_boundary_is_inclusive():
    quote = "abcdefghijklmnopqrst"
    source = "abcdefghijklmnopqrXY"
    at_boundary = verify(quote, source, threshold=0.90).citations[0]
    assert at_boundary.status == "approximate"
    assert at_boundary.score == pytest.approx(0.90)
    assert verify(quote, source, threshold=0.9001).citations[0].status == "removed"


def test_approximate_duplicate_locations_do_not_guess_highlight():
    source = "The gravitationel force attracts objects toward Earth."
    quote = "The gravitational force attracts objects toward Earth."
    result = verify(quote, source + " " + source).citations[0]
    assert result.status == "approximate" and result.ambiguous
    assert result.source_start is None and result.source_end is None


def test_fuzzy_may_match_semantic_change_outside_number_negation_guards():
    # This intentionally records a limitation, not a claim of entailment verification.
    source = "The gravitational force attracts objects toward Earth."
    quote = "The gravitational force attracts objects toward Mars."
    result = verify(quote, source).citations[0]
    assert result.status == "approximate"
