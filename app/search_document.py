#search_document.py

import argparse
import math
import os

from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
from app.retrieval import get_document, search_chunks


def cosine_similarity(
    first: list[float],
    second: list[float],
) -> float:
    if len(first) != len(second):
        raise ValueError("Vectors must have the same dimensions.")

    dot_product = sum(
        a * b
        for a, b in zip(first, second, strict=True)
    )

    first_norm = math.sqrt(sum(value**2 for value in first))
    second_norm = math.sqrt(sum(value**2 for value in second))

    if first_norm == 0 or second_norm == 0:
        raise ValueError("Vectors must have non-zero length.")

    return dot_product / (first_norm * second_norm)


def main():
    parser = argparse.ArgumentParser(
        description="Search document chunks stored in PostgreSQL."
    )
    parser.add_argument(
        "document_id",
        type=int,
        help="Identifier of the document stored in PostgreSQL.",
    )
    parser.add_argument(
        "--query",
        required=True,
        help="Question or search text.",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Maximum number of chunks to return.",
    )
    args = parser.parse_args()

    if args.document_id <= 0:
        parser.error("document_id must be greater than zero.")

    query = args.query.strip()

    if not query:
        parser.error("The query must not be empty.")

    if args.top_k <= 0:
        parser.error("top-k must be greater than zero.")

    project_root = Path(__file__).resolve().parent.parent
    load_dotenv(project_root / ".env")

    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        parser.error("OPENAI_API_KEY is missing.")

    try:
        document = get_document(args.document_id)
    except ValueError as error:
        parser.error(str(error))

    # Use the same model and dimensions as the stored embeddings.
    with OpenAI(api_key=api_key, timeout=30.0) as client:
        response = client.embeddings.create(
            model=document["embedding_model"],
            dimensions=document["embedding_dimensions"],
            input=query,
        )

    query_embedding = response.data[0].embedding

    results = search_chunks(
        document_id=args.document_id,
        query_embedding=query_embedding,
        top_k=args.top_k,
    )

    print("Query:", query)
    print("Document:", document["filename"])
    print("Document ID:", document["id"])
    print("Query tokens used:", response.usage.total_tokens)

    if not results:
        print("No chunks found for this document.")
        return

    for position, result in enumerate(results, start=1):
        pages = ", ".join(
            str(page)
            for page in result["page_numbers"]
        )
        similarity = 1 - result["distance"]

        print()
        print(f"Result {position}")
        print("Chunk:", result["chunk_number"])
        print("Pages:", pages)
        print(f"Similarity: {similarity:.4f}")
        print(result["text"])


if __name__ == "__main__":
    main()