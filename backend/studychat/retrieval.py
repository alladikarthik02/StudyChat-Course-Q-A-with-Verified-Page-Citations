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


def retrieve(settings, selected: list[UUID], vector: list[float], model: str):
    validate_embeddings([vector], 1, settings.embedding_dimensions)
    validate_documents(settings, selected, model)
    with connection(settings, vectors=True) as conn:
        ranked = conn.execute(
            "SELECT c.document_id,c.page,c.text,c.ordinal,"
            "1-(c.embedding <=> %s::vector) AS similarity "
            "FROM chunks c JOIN documents d ON d.id=c.document_id "
            "WHERE c.document_id=ANY(%s::uuid[]) AND d.state='ready' "
            "AND d.embedding_model=%s AND c.kind='page' AND c.page>0 "
            "ORDER BY c.embedding <=> %s::vector,c.document_id,c.page,c.ordinal LIMIT 6",
            (vector, selected, model, vector),
        ).fetchall()

        if not ranked:
            return []
        # A slide can introduce a concept whose explanation is on its neighbor.
        # Keep four semantic hits and use at most two slots for neighboring context.
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
        result, seen = [], set()
        for row in [*ranked[:4], *neighbors, *ranked[4:]]:
            key = (row["document_id"], row["page"], row["ordinal"])
            if key not in seen:
                seen.add(key)
                result.append(row)
            if len(result) == 6:
                break
        return result
