import argparse
import json
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI


def main():
    parser = argparse.ArgumentParser(
        description="Generate and save embeddings for document chunks."
    )
    parser.add_argument(
        "json_path",
        type=Path,
        help="Path to the document chunks JSON.",
    )
    args = parser.parse_args()

    if not args.json_path.is_file():
        parser.error("The specified file does not exist.")

    project_root = Path(__file__).resolve().parent.parent
    load_dotenv(project_root / ".env")

    api_key = os.getenv("OPENAI_API_KEY")
    model = os.getenv("OPENAI_EMBEDDING_MODEL")

    if not api_key or not model:
        parser.error("OpenAI configuration is missing.")

    document = json.loads(
        args.json_path.read_text(encoding="utf-8")
    )
    chunks = document["chunks"]

    if not chunks:
        parser.error("The document contains no chunks.")

    if any(not chunk["text"].strip() for chunk in chunks):
        parser.error("All chunks must contain non-empty text.")

    output_directory = project_root / "data" / "embeddings"
    output_directory.mkdir(parents=True, exist_ok=True)
    output_path = output_directory / args.json_path.name

    if output_path.exists():
        parser.error(
            "The output file already exists. "
            "Move or remove it intentionally before regenerating embeddings."
        )

    texts = [chunk["text"] for chunk in chunks]

    with OpenAI(api_key=api_key, timeout=60.0) as client:
        response = client.embeddings.create(
            model=model,
            input=texts,
        )

    ordered_embeddings = sorted(
        response.data,
        key=lambda item: item.index,
    )

    if [item.index for item in ordered_embeddings] != list(
        range(len(chunks))
    ):
        raise RuntimeError(
            "The returned embeddings do not match the input chunks."
        )

    embedded_chunks = [
        {
            **chunk,
            "embedding": item.embedding,
        }
        for chunk, item in zip(
            chunks,
            ordered_embeddings,
            strict=True,
        )
    ]

    result = {
        "filename": document["filename"],
        "page_count": document["page_count"],
        "chunking": document["chunking"],
        "chunk_count": len(embedded_chunks),
        "embedding_model": response.model,
        "embedding_dimensions": len(
            ordered_embeddings[0].embedding
        ),
        "embedding_input_tokens": response.usage.total_tokens,
        "chunks": embedded_chunks,
    }

    output_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("Document:", result["filename"])
    print("Chunks embedded:", result["chunk_count"])
    print("Model:", result["embedding_model"])
    print("Vector dimensions:", result["embedding_dimensions"])
    print("Tokens used:", result["embedding_input_tokens"])
    print("Output saved to:", output_path)


if __name__ == "__main__":
    main()