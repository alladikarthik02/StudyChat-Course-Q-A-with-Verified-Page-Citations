from uuid import UUID, uuid4

from studychat.config import Settings
from studychat.db import connection
from studychat.text import NORMALIZATION_VERSION, normalize

PUBLIC_COLUMNS = "id, filename, state, page_count, embedding_model, error_code, created_at"


class DocumentRepository:
    def __init__(self, settings: Settings):
        self.settings = settings

    def create(self, doc_id: UUID, filename: str, digest: str, model: str):
        with connection(self.settings) as conn:
            conn.execute(
                "INSERT INTO documents (id,filename,sha256,state,embedding_model) "
                "VALUES (%s,%s,%s,'processing',%s)",
                (doc_id, filename, digest, model),
            )

    def get(self, doc_id: UUID):
        with connection(self.settings) as conn:
            return conn.execute(
                f"SELECT {PUBLIC_COLUMNS} FROM documents WHERE id=%s", (doc_id,)
            ).fetchone()

    def list_documents(self):
        with connection(self.settings) as conn:
            return conn.execute(
                f"SELECT {PUBLIC_COLUMNS} FROM documents ORDER BY created_at DESC, id"
            ).fetchall()

    def publish(self, doc_id: UUID, pages: list[str], chunks: list[dict], vectors: list):
        with connection(self.settings, vectors=True) as conn:
            row = conn.execute(
                "SELECT state FROM documents WHERE id=%s FOR UPDATE", (doc_id,)
            ).fetchone()
            if not row or row["state"] != "processing":
                return False
            with conn.cursor() as cursor:
                cursor.executemany(
                    "INSERT INTO pages VALUES (%s,%s,%s,%s,%s)",
                    [
                        (doc_id, i, text, normalize(text), NORMALIZATION_VERSION)
                        for i, text in enumerate(pages, 1)
                    ],
                )
                cursor.executemany(
                    "INSERT INTO chunks (id,document_id,page,ordinal,kind,text,start_offset,"
                    "end_offset,embedding) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                    [
                        (
                            uuid4(),
                            doc_id,
                            c["page"],
                            c["ordinal"],
                            c["kind"],
                            c["text"],
                            c["start_offset"],
                            c["end_offset"],
                            vector,
                        )
                        for c, vector in zip(chunks, vectors, strict=True)
                    ],
                )
            conn.execute(
                "UPDATE documents SET state='ready',page_count=%s,error_code=NULL WHERE id=%s",
                (len(pages), doc_id),
            )
            return True

    def fail(self, doc_id: UUID, code: str):
        with connection(self.settings) as conn:
            conn.execute(
                "UPDATE documents SET state='failed',error_code=%s "
                "WHERE id=%s AND state IN ('processing','pending')",
                (code, doc_id),
            )

    def mark_deleting(self, doc_id: UUID):
        with connection(self.settings) as conn:
            return conn.execute(
                "UPDATE documents SET state='deleting' WHERE id=%s RETURNING id", (doc_id,)
            ).fetchone()

    def remove(self, doc_id: UUID):
        with connection(self.settings) as conn:
            conn.execute("DELETE FROM documents WHERE id=%s AND state='deleting'", (doc_id,))

    def all_ids(self):
        with connection(self.settings) as conn:
            return {str(row["id"]) for row in conn.execute("SELECT id FROM documents").fetchall()}

    def recover(self):
        with connection(self.settings) as conn:
            conn.execute(
                "UPDATE documents SET state='failed',error_code='interrupted' "
                "WHERE state IN ('pending','processing')"
            )
            return conn.execute(
                "SELECT id,state FROM documents WHERE state IN ('failed','deleting')"
            ).fetchall()

    def citation_pages(self, selected_ids: list[UUID], retrieved_pages: list[tuple[UUID, int]]):
        """Load only ready, selected, physically numbered pages named by server retrieval."""
        from studychat.citations import PageSource

        pairs = list(dict.fromkeys(retrieved_pages))
        if len(selected_ids) > 10 or len(pairs) > 6:
            raise ValueError("citation_context_limit")
        if not selected_ids or not pairs:
            return []
        with connection(self.settings) as conn:
            rows = conn.execute(
                "SELECT p.document_id,p.page,p.text FROM pages p "
                "JOIN documents d ON d.id=p.document_id "
                "JOIN unnest(%s::uuid[],%s::int[]) AS wanted(document_id,page) "
                "ON wanted.document_id=p.document_id AND wanted.page=p.page "
                "WHERE d.state='ready' AND p.document_id=ANY(%s::uuid[]) AND p.page>0 "
                "ORDER BY p.document_id,p.page",
                ([pair[0] for pair in pairs], [pair[1] for pair in pairs], selected_ids),
            ).fetchall()
            return [PageSource(row["document_id"], row["page"], row["text"]) for row in rows]
