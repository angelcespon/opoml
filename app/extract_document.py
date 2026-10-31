# extract_document.py

import argparse
import json
import re
from pathlib import Path

from pypdf import PdfReader

def normalize_page_text(text: str) -> str:
    lines = [
        re.sub(r"[ \t]+", " ", line).strip()
        for line in text.splitlines()
    ]

    return "\n".join(lines).strip()


def extract_document(pdf_path: Path) -> dict:
    reader = PdfReader(pdf_path)
    pages = []

    for page_number, page in enumerate(reader.pages, start=1):
        raw_text = page.extract_text() or ""

        pages.append(
            {
                "page_number": page_number,
                "raw_text": raw_text,
                "text": normalize_page_text(raw_text),
            }
        )

    return {
        "filename": pdf_path.name,
        "page_count": len(pages),
        "pages": pages,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Extract PDF text while preserving page boundaries."
    )
    parser.add_argument(
        "pdf_path",
        type=Path,
        help="Path to the PDF document.",
    )
    args = parser.parse_args()

    if not args.pdf_path.is_file():
        parser.error("The specified file does not exist.")

    document = extract_document(args.pdf_path)

    project_root = Path(__file__).resolve().parent.parent
    output_directory = project_root / "data" / "extracted"
    output_directory.mkdir(parents=True, exist_ok=True)

    output_path = output_directory / f"{args.pdf_path.stem}.json"
    output_path.write_text(
        json.dumps(document, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    empty_pages = [
        page["page_number"]
        for page in document["pages"]
        if not page["text"].strip()
    ]

    print("Document:", document["filename"])
    print("Pages processed:", document["page_count"])
    print("Pages without text:", empty_pages)
    print("Output saved to:", output_path)


if __name__ == "__main__":
    main()