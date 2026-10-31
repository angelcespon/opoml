import argparse
import hashlib
import json
from pathlib import Path

from pydantic import BaseModel, Field
from sqlalchemy import bindparam, text

from app.database import engine
from app.question_repository import insert_question
from app.schemas import DocumentSource, GeneratedQuestion, QuestionCreate


class ReviewedBatch(BaseModel):
    document_id: int = Field(gt=0)
    accepted_count: int = Field(ge=0)
    questions: list[GeneratedQuestion] = Field(
        min_length=1,
        max_length=100,
    )
    sources: list[DocumentSource] = Field(min_length=1)


def import_questions(batch: ReviewedBatch, topic_id: int) -> dict:
    if topic_id <= 0:
        raise ValueError("topic_id must be greater than zero.")

    if batch.accepted_count != len(batch.questions):
        raise ValueError("accepted_count does not match the questions.")

    sources_by_id = {
        source.source_id: source
        for source in batch.sources
    }

    if len(sources_by_id) != len(batch.sources):
        raise ValueError("Duplicate source identifiers.")

    if any(
        source.document_id != batch.document_id
        for source in batch.sources
    ):
        raise ValueError("Sources belong to a different document.")

    prepared_questions = []

    for question in batch.questions:
        if not set(question.source_ids).issubset(sources_by_id):
            raise ValueError("A question cites an unknown source.")

        chunk_ids = sorted({
            sources_by_id[source_id].chunk_id
            for source_id in question.source_ids
        })

        content = question.model_dump(exclude={"source_ids"})

        # Validate using the same schema as the manual endpoint.
        validated = QuestionCreate(
            topic_id=topic_id,
            **content,
        )

        normalized_options = [
            " ".join(option.content.casefold().split())
            for option in validated.options
        ]

        if len(normalized_options) != len(set(normalized_options)):
            raise ValueError("A question contains duplicate options.")

        prepared_questions.append({
            "content": content,
            "chunk_ids": chunk_ids,
        })

    # Exclude usage, timestamps, and temporary source labels.
    fingerprint_payload = {
        "document_id": batch.document_id,
        "questions": prepared_questions,
    }

    serialized = json.dumps(
        fingerprint_payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )

    batch_sha256 = hashlib.sha256(
        serialized.encode("utf-8")
    ).hexdigest()

    all_chunk_ids = sorted({
        chunk_id
        for question in prepared_questions
        for chunk_id in question["chunk_ids"]
    })

    created_ids = []

    with engine.begin() as connection:
        topic = connection.execute(
            text("SELECT id FROM public.topics WHERE id = :topic_id"),
            {"topic_id": topic_id},
        ).scalar_one_or_none()

        if topic is None:
            raise ValueError("The destination topic does not exist.")

        chunks = connection.execute(
            text(
                """
                SELECT id
                FROM public.document_chunks
                WHERE document_id = :document_id
                  AND id IN :chunk_ids
                """
            ).bindparams(
                bindparam("chunk_ids", expanding=True)
            ),
            {
                "document_id": batch.document_id,
                "chunk_ids": all_chunk_ids,
            },
        )

        if set(chunks.scalars()) != set(all_chunk_ids):
            raise ValueError(
                "Some chunks do not exist or belong to another document."
            )

        registration = connection.execute(
            text(
                """
                INSERT INTO public.question_imports (
                    batch_sha256,
                    document_id,
                    topic_id,
                    question_count
                )
                VALUES (
                    :batch_sha256,
                    :document_id,
                    :topic_id,
                    :question_count
                )
                ON CONFLICT (batch_sha256) DO NOTHING
                RETURNING batch_sha256
                """
            ),
            {
                "batch_sha256": batch_sha256,
                "document_id": batch.document_id,
                "topic_id": topic_id,
                "question_count": len(prepared_questions),
            },
        ).scalar_one_or_none()

        if registration is None:
            existing_topic_id = connection.execute(
                text(
                    """
                    SELECT topic_id
                    FROM public.question_imports
                    WHERE batch_sha256 = :batch_sha256
                    """
                ),
                {"batch_sha256": batch_sha256},
            ).scalar_one()

            return {
                "status": "already_imported",
                "topic_id": existing_topic_id,
                "inserted_count": 0,
            }

        for prepared in prepared_questions:
            question = QuestionCreate(
                topic_id=topic_id,
                **prepared["content"],
            )

            created = insert_question(connection, question)
            created_ids.append(created["id"])

            connection.execute(
                text(
                    """
                    INSERT INTO public.question_sources (
                        question_id, chunk_id
                    )
                    VALUES (:question_id, :chunk_id)
                    """
                ),
                [
                    {
                        "question_id": created["id"],
                        "chunk_id": chunk_id,
                    }
                    for chunk_id in prepared["chunk_ids"]
                ],
            )

    return {
        "status": "imported",
        "document_id": batch.document_id,
        "topic_id": topic_id,
        "inserted_count": len(created_ids),
        "question_ids": created_ids,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Import an accepted question batch with its sources."
    )
    parser.add_argument("result_path", type=Path)
    parser.add_argument("--topic-id", type=int, required=True)
    args = parser.parse_args()

    if not args.result_path.is_file():
        parser.error("The result file does not exist.")

    if args.topic_id <= 0:
        parser.error("topic-id must be greater than zero.")

    data = json.loads(
        args.result_path.read_text(encoding="utf-8")
    )
    batch = ReviewedBatch.model_validate(data)
    result = import_questions(batch, args.topic_id)

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()