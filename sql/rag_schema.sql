BEGIN;

CREATE SCHEMA IF NOT EXISTS extensions;

CREATE EXTENSION IF NOT EXISTS vector
    WITH SCHEMA extensions;

CREATE TABLE public.documents (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    filename TEXT NOT NULL
        CHECK (char_length(btrim(filename)) > 0),

    file_sha256 TEXT NOT NULL UNIQUE
        CHECK (file_sha256 ~ '^[0-9a-f]{64}$'),

    page_count INTEGER NOT NULL
        CHECK (page_count > 0),

    chunking_method TEXT NOT NULL
        CHECK (chunking_method = 'word_window'),

    chunk_size INTEGER NOT NULL
        CHECK (chunk_size > 0),

    chunk_overlap INTEGER NOT NULL
        CHECK (
            chunk_overlap >= 0
            AND chunk_overlap < chunk_size
        ),

    embedding_model TEXT NOT NULL
        CHECK (char_length(btrim(embedding_model)) > 0),

    embedding_dimensions INTEGER NOT NULL
        CHECK (embedding_dimensions = 1536),

    created_at TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE public.document_chunks (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    document_id INTEGER NOT NULL
        REFERENCES public.documents (id),

    chunk_number INTEGER NOT NULL
        CHECK (chunk_number > 0),

    page_numbers INTEGER[] NOT NULL
        CHECK (
            cardinality(page_numbers) > 0
            AND array_position(page_numbers, NULL) IS NULL
            AND 0 < ALL (page_numbers)
        ),

    content TEXT NOT NULL
        CHECK (char_length(btrim(content)) > 0),

    embedding extensions.vector(1536) NOT NULL,

    CONSTRAINT document_chunks_document_number_key
        UNIQUE (document_id, chunk_number)
);

ALTER TABLE public.documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.document_chunks ENABLE ROW LEVEL SECURITY;

COMMIT;