# check_embeddings.py

import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI


def main():
    project_root = Path(__file__).resolve().parent.parent
    load_dotenv(project_root / ".env")

    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is missing.")

    model = os.environ["OPENAI_EMBEDDING_MODEL"]

    with OpenAI(api_key=api_key, timeout=30.0) as client:
        response = client.embeddings.create(
            model=model,
            input="La víctima puede estar acompañada de una persona de su elección.",
        )

    embedding = response.data[0].embedding

    print("Model:", response.model)
    print("Vector dimensions:", len(embedding))
    print("First five values:", embedding[:5])
    print("Tokens used:", response.usage.total_tokens)


if __name__ == "__main__":
    main()