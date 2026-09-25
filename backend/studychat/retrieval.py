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
        return conn.execute(
            "SELECT c.document_id,c.page,c.text,c.ordinal,"
            "1-(c.embedding <=> %s::vector) AS similarity "
            "FROM chunks c JOIN documents d ON d.id=c.document_id "
            "WHERE c.document_id=ANY(%s::uuid[]) AND d.state='ready' "
            "AND d.embedding_model=%s AND c.kind='page' AND c.page>0 "
            "ORDER BY c.embedding <=> %s::vector,c.document_id,c.page,c.ordinal LIMIT 6",
            (vector, selected, model, vector),
        ).fetchall()
