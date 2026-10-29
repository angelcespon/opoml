# retrieval.py

import json

from sqlalchemy import text

from app.database import engine

class DocumentNotFoundError(ValueError):
    pass

class DocumentEmptyError(ValueError):
    pass

def get_document(document_id: int) -> dict:
    if document_id <= 0:
        raise ValueError("document_id must be greater than zero.")

    with engine.connect() as connection:
        document = connection.execute(
            text("""
                SELECT
                    id,
                    filename,
                    embedding_model,
                    embedding_dimensions
                FROM public.documents
                WHERE id = :document_id
            """),
            {"document_id": document_id},
        ).mappings().one_or_none()

    if document is None:
        raise DocumentNotFoundError(
            "The specified document does not exist."
        )

    return dict(document)


def search_chunks(
    document_id: int,
    query_embedding: list[float],
    top_k: int = 5,
) -> list[dict]:
    if document_id <= 0:
        raise ValueError("document_id must be greater than zero.")

    if top_k <= 0:
        raise ValueError("top_k must be greater than zero.")

    with engine.connect() as connection:
        results = connection.execute(
            text("""
                SELECT
                    id AS chunk_id,
                    chunk_number,
                    page_numbers,
                    content AS text,
                    embedding OPERATOR(extensions.<=>)
                        CAST(:query_embedding AS extensions.vector)
                        AS distance
                FROM public.document_chunks
                WHERE document_id = :document_id
                ORDER BY distance ASC, chunk_number ASC
                LIMIT :top_k
            """),
            {
                "document_id": document_id,
                "query_embedding": json.dumps(
                    query_embedding,
                    allow_nan=False,
                ),
                "top_k": top_k,
            },
        ).mappings().all()

    return [dict(row) for row in results]