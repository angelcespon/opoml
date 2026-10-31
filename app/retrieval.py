# retrieval.py

import json
import random

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

def get_generation_context(document_id: int) -> dict:
    document = get_document(document_id)
    block_size = 3

    with engine.connect() as connection:
        chunk_count = connection.execute(
            text("""
                SELECT COUNT(*)
                FROM public.document_chunks
                WHERE document_id = :document_id
            """),
            {"document_id": document_id},
        ).scalar_one()

        if chunk_count == 0:
            raise DocumentEmptyError(
                "The document contains no chunks."
            )

        # Choose a starting position that allows a complete block
        # whenever the document contains enough chunks.
        max_offset = max(0, chunk_count - block_size)
        offset = random.randint(0, max_offset)

        rows = connection.execute(
            text("""
                SELECT
                    id AS chunk_id,
                    chunk_number,
                    page_numbers,
                    content AS text
                FROM public.document_chunks
                WHERE document_id = :document_id
                ORDER BY chunk_number
                LIMIT :block_size
                OFFSET :offset
            """),
            {
                "document_id": document_id,
                "block_size": block_size,
                "offset": offset,
            },
        ).mappings().all()

    sources = [
        {
            "source_id": f"S{position}",
            "chunk_id": row["chunk_id"],
            "chunk_number": row["chunk_number"],
            "page_numbers": row["page_numbers"],
            "text": row["text"],
        }
        for position, row in enumerate(rows, start=1)
    ]

    return {
        "document": document,
        "sources": sources,
    }

def get_generation_contexts(
    document_id: int,
    block_count: int,
) -> list[dict]:
    if not 1 <= block_count <= 100:
        raise ValueError("block_count must be between 1 and 100.")

    document = get_document(document_id)

    with engine.connect() as connection:
        rows = connection.execute(
            text("""
                SELECT
                    id AS chunk_id,
                    chunk_number,
                    page_numbers,
                    content AS text
                FROM public.document_chunks
                WHERE document_id = :document_id
                ORDER BY chunk_number
            """),
            {"document_id": document_id},
        ).mappings().all()

    if not rows:
        raise DocumentEmptyError(
            "The document contains no chunks."
        )

    block_size = 3

    blocks = [
        rows[start:start + block_size]
        for start in range(0, len(rows), block_size)
    ]

    selected_count = min(block_count, len(blocks))

    # Divide the document into regions and choose one block per region.
    selected_blocks = []

    for index in range(selected_count):
        start = index * len(blocks) // selected_count
        end = (index + 1) * len(blocks) // selected_count

        block_index = random.randrange(start, end)
        selected_blocks.append(blocks[block_index])

    contexts = []

    for block in selected_blocks:
        sources = [
            {
                "source_id": f"S{position}",
                "chunk_id": row["chunk_id"],
                "chunk_number": row["chunk_number"],
                "page_numbers": row["page_numbers"],
                "text": row["text"],
            }
            for position, row in enumerate(block, start=1)
        ]

        contexts.append({
            "document": document,
            "sources": sources,
        })

    return contexts