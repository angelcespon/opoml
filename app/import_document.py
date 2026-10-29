# import_document.py

import argparse
import hashlib
import json
from pathlib import Path

from sqlalchemy import text

from app.database import engine


def import_document(pdf_path: Path, embeddings_path: Path) -> None:
    document = json.loads(
        embeddings_path.read_text(encoding="utf-8")
    )

    # Basic checks before writing to the database.
    if document["filename"] != pdf_path.name:
        raise ValueError(
            "The PDF filename does not match the embeddings document."
        )

    chunks = document["chunks"]

    if not chunks or len(chunks) != document["chunk_count"]:
        raise ValueError("The chunk count is missing or inconsistent.")

    dimensions = document["embedding_dimensions"]

    if dimensions != 1536:
        raise ValueError("The database expects 1536-dimensional embeddings.")

    for chunk in chunks:
        if len(chunk["embedding"]) != dimensions:
            raise ValueError(
                f"Invalid embedding dimensions in chunk "
                f"{chunk['chunk_number']}."
            )

        if not chunk["page_numbers"] or any(
            page < 1 or page > document["page_count"]
            for page in chunk["page_numbers"]
        ):
            raise ValueError(
                f"Invalid pages in chunk {chunk['chunk_number']}."
            )

    file_sha256 = hashlib.sha256(pdf_path.read_bytes()).hexdigest()

    document_record = {
        "filename": document["filename"],
        "file_sha256": file_sha256,
        "page_count": document["page_count"],
        "chunking_method": document["chunking"]["method"],
        "chunk_size": document["chunking"]["chunk_size"],
        "chunk_overlap": document["chunking"]["overlap"],
        "embedding_model": document["embedding_model"],
        "embedding_dimensions": dimensions,
    }

    with engine.begin() as connection:
        result = connection.execute(
            text("""
                INSERT INTO public.documents (
                    filename,
                    file_sha256,
                    page_count,
                    chunking_method,
                    chunk_size,
                    chunk_overlap,
                    embedding_model,
                    embedding_dimensions
                )
                VALUES (
                    :filename,
                    :file_sha256,
                    :page_count,
                    :chunking_method,
                    :chunk_size,
                    :chunk_overlap,
                    :embedding_model,
                    :embedding_dimensions
                )
                ON CONFLICT (file_sha256) DO NOTHING
                RETURNING id
            """),
            document_record,
        )

        document_id = result.scalar_one_or_none()

        if document_id is None:
            print("Document already imported. No changes made.")
            return

        chunk_records = [
            {
                "document_id": document_id,
                "chunk_number": chunk["chunk_number"],
                "page_numbers": chunk["page_numbers"],
                "content": chunk["text"],
                "embedding": json.dumps(
                    chunk["embedding"],
                    allow_nan=False,
                ),
            }
            for chunk in chunks
        ]

        connection.execute(
            text("""
                INSERT INTO public.document_chunks (
                    document_id,
                    chunk_number,
                    page_numbers,
                    content,
                    embedding
                )
                VALUES (
                    :document_id,
                    :chunk_number,
                    :page_numbers,
                    :content,
                    CAST(:embedding AS extensions.vector(1536))
                )
            """),
            chunk_records,
        )

    print("Document imported:", document["filename"])
    print("Document ID:", document_id)
    print("Chunks stored:", len(chunks))


def main():
    parser = argparse.ArgumentParser(
        description="Import a PDF's existing embeddings into PostgreSQL."
    )
    parser.add_argument("pdf_path", type=Path)
    parser.add_argument("embeddings_path", type=Path)
    args = parser.parse_args()

    for path in (args.pdf_path, args.embeddings_path):
        if not path.is_file():
            parser.error(f"File not found: {path}")

    import_document(args.pdf_path, args.embeddings_path)


if __name__ == "__main__":
    main()