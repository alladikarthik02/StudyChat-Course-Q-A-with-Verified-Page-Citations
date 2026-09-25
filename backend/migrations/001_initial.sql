CREATE EXTENSION IF NOT EXISTS vector;
CREATE TABLE documents (
    id uuid PRIMARY KEY,
    filename text NOT NULL,
    sha256 text NOT NULL CHECK (length(sha256) = 64),
    state text NOT NULL CHECK (state IN ('pending','processing','ready','failed','deleting')),
    page_count integer NOT NULL DEFAULT 0 CHECK (page_count >= 0),
    embedding_model text NOT NULL,
    error_code text,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE pages (
    document_id uuid NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    page integer NOT NULL CHECK (page > 0),
    text text NOT NULL,
    normalized_text text NOT NULL,
    normalization_version text NOT NULL,
    PRIMARY KEY (document_id, page)
);
CREATE TABLE chunks (
    id uuid PRIMARY KEY,
    document_id uuid NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    page integer NOT NULL CHECK (page >= 0),
    ordinal integer NOT NULL CHECK (ordinal >= 0),
    kind text NOT NULL CHECK (kind IN ('page','metadata')),
    text text NOT NULL,
    start_offset integer NOT NULL CHECK (start_offset >= 0),
    end_offset integer NOT NULL CHECK (end_offset >= start_offset),
    embedding vector(1536) NOT NULL,
    CHECK ((kind = 'metadata' AND page = 0) OR (kind = 'page' AND page > 0)),
    UNIQUE (document_id, page, ordinal)
);
CREATE INDEX chunks_document_page_idx ON chunks(document_id, page);
