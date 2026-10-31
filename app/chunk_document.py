# chunk_document.py

import argparse
import json
from pathlib import Path


def create_chunks(
    pages: list[dict],
    chunk_size: int = 300,
    overlap: int = 50,
) -> list[dict]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than zero.")

    if not 0 <= overlap < chunk_size:
        raise ValueError(
            "overlap must be greater than or equal to zero "
            "and smaller than chunk_size."
        )

    words = []
    word_pages = []

    for page in pages:
        page_words = page["text"].split()

        words.extend(page_words)
        word_pages.extend(
            [page["page_number"]] * len(page_words)
        )

    chunks = []
    start = 0

    while start < len(words):
        end = min(start + chunk_size, len(words))

        source_pages = sorted(set(word_pages[start:end]))

        chunks.append(
            {
                "chunk_number": len(chunks) + 1,
                "page_numbers": source_pages,
                "word_count": end - start,
                "text": " ".join(words[start:end]),
            }
        )

        if end == len(words):
            break

        start = end - overlap

    return chunks


def main():
    parser = argparse.ArgumentParser(
        description="Split extracted PDF text into overlapping chunks."
    )
    parser.add_argument(
        "json_path",
        type=Path,
        help="Path to the extracted document JSON.",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=300,
        help="Maximum number of words per chunk.",
    )
    parser.add_argument(
        "--overlap",
        type=int,
        default=50,
        help="Number of words shared by consecutive chunks.",
    )
    args = parser.parse_args()

    if not args.json_path.is_file():
        parser.error("The specified file does not exist.")

    document = json.loads(
        args.json_path.read_text(encoding="utf-8")
    )

    try:
        chunks = create_chunks(
            document["pages"],
            chunk_size=args.chunk_size,
            overlap=args.overlap,
        )
    except ValueError as error:
        parser.error(str(error))

    result = {
        "filename": document["filename"],
        "page_count": document["page_count"],
        "chunking": {
            "method": "word_window",
            "chunk_size": args.chunk_size,
            "overlap": args.overlap,
        },
        "chunk_count": len(chunks),
        "chunks": chunks,
    }

    project_root = Path(__file__).resolve().parent.parent
    output_directory = project_root / "data" / "chunks"
    output_directory.mkdir(parents=True, exist_ok=True)

    output_path = output_directory / args.json_path.name
    output_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("Document:", result["filename"])
    print("Chunks created:", result["chunk_count"])
    print("Chunk size (words):", args.chunk_size)
    print("Overlap (words):", args.overlap)
    print("Output saved to:", output_path)


if __name__ == "__main__":
    main()