import math
from collections import Counter
from uuid import UUID

from studychat.db import connection
from studychat.providers import validate_embeddings


class ContextError(Exception):
    pass


def validate_documents(settings, selected: list[UUID], model: str):
    with connection(settings) as conn:
        rows = conn.execute(
            "SELECT id,state,embedding_model FROM documents WHERE id=ANY(%s::uuid[])",
            (selected,),
        ).fetchall()
    if len(rows) != len(set(selected)) or any(row["state"] != "ready" for row in rows):
        raise ContextError("document_not_ready")
    if any(row["embedding_model"] != model for row in rows):
        raise ContextError("embedding_model_mismatch_reupload_required")


def retrieve(
    settings,
    selected: list[UUID],
    vector: list[float],
    model: str,
    question: str = "",
    candidate_limit: int = 6,
):
    if candidate_limit not in {6, 32}:
        raise ValueError("invalid_candidate_limit")
    validate_embeddings([vector], 1, settings.embedding_dimensions)
    validate_documents(settings, selected, model)
    with connection(settings, vectors=True) as conn:
        ranked = conn.execute(
            "SELECT c.document_id,c.page,c.text,c.ordinal,"
            "1-(c.embedding <=> %s::vector) AS similarity "
            "FROM chunks c JOIN documents d ON d.id=c.document_id "
            "WHERE c.document_id=ANY(%s::uuid[]) AND d.state='ready' "
            "AND d.embedding_model=%s AND c.kind='page' AND c.page>0 "
            "ORDER BY c.embedding <=> %s::vector,c.document_id,c.page,c.ordinal LIMIT %s",
            (vector, selected, model, vector, 24 if candidate_limit == 32 else 6),
        ).fetchall()

        if not ranked:
            return []
        # A slide can introduce a concept whose explanation is on its neighbor.
        # Add at most two chunks from physical pages adjacent to the semantic anchor.
        anchor = ranked[0]
        neighbors = conn.execute(
            "SELECT c.document_id,c.page,c.text,c.ordinal,"
            "1-(c.embedding <=> %s::vector) AS similarity "
            "FROM chunks c JOIN documents d ON d.id=c.document_id "
            "WHERE c.document_id=%s AND c.page=ANY(%s::int[]) "
            "AND c.kind='page' AND c.page>0 AND d.state='ready' "
            "AND d.embedding_model=%s "
            "ORDER BY c.ordinal,c.page LIMIT 2",
            (vector, anchor["document_id"], [anchor["page"] - 1, anchor["page"] + 1], model),
        ).fetchall()
        lexical = []
        if question.strip():
            query_terms = conn.execute(
                "SELECT tsvector_to_array(to_tsvector('english', %s)) AS terms", (question,)
            ).fetchone()["terms"]
            candidates = conn.execute(
                "SELECT c.document_id,c.page,c.text,c.ordinal,"
                "1-(c.embedding <=> %s::vector) AS similarity, "
                "tsvector_to_array(to_tsvector('english',c.text)) AS terms "
                "FROM chunks c JOIN documents d ON d.id=c.document_id "
                "WHERE c.document_id=ANY(%s::uuid[]) AND d.state='ready' "
                "AND d.embedding_model=%s AND c.kind='page' AND c.page>0 "
                "ORDER BY c.document_id,c.page,c.ordinal",
                (vector, selected, model),
            ).fetchall()
            lexical = lexical_rank(candidates, query_terms)[: 12 if candidate_limit == 32 else 2]
        result, seen = [], set()
        # Hybrid mode keeps two semantic anchors, two lexical hits and two
        # neighboring chunks. Without query text preserve the legacy ranking.
        candidates = (
            [*ranked[:2], *lexical, *neighbors, *ranked[2:]]
            if question.strip()
            else [*ranked[:4], *neighbors, *ranked[4:]]
        )
        if candidate_limit == 32:
            candidates = [*ranked[:16], *lexical, *neighbors, *ranked[16:]]
        for row in candidates:
            key = (row["document_id"], row["page"], row["ordinal"])
            if key not in seen:
                seen.add(key)
                result.append(row)
            if len(result) == candidate_limit:
                break
        return result


def lexical_rank(rows, query_terms):
    """IDF-weighted word overlap; rare course terms outrank generic vocabulary."""
    query = set(query_terms)
    if not rows or not query:
        return []
    frequency = Counter(term for row in rows for term in set(row["terms"]))
    average_length = sum(len(row["terms"]) for row in rows) / len(rows) or 1
    scored = []
    for row in rows:
        overlap = query.intersection(row["terms"])
        if not overlap:
            continue
        weight = sum(
            math.log(1 + (len(rows) - frequency[t] + 0.5) / (frequency[t] + 0.5)) for t in overlap
        )
        weight /= 1 + 1.2 * (0.25 + 0.75 * len(row["terms"]) / average_length)
        scored.append((weight, {k: v for k, v in row.items() if k != "terms"}))
    scored.sort(
        key=lambda item: (
            -item[0],
            str(item[1]["document_id"]),
            item[1]["page"],
            item[1]["ordinal"],
        )
    )
    return [row for _, row in scored]
