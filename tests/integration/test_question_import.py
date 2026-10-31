import importlib
import json
from contextlib import contextmanager
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError


import_module = importlib.import_module("app.import_questions")


@pytest.fixture
def import_case(database_engine, monkeypatch):
    with database_engine.connect() as connection:
        outer_transaction = connection.begin()

        # The importer uses a savepoint inside this test transaction.
        @contextmanager
        def begin():
            with connection.begin_nested():
                yield connection

        monkeypatch.setattr(
            import_module,
            "engine",
            SimpleNamespace(begin=begin),
        )

        try:
            topic_id = connection.execute(
                text(
                    """
                    INSERT INTO public.topics (name)
                    VALUES ('Import integration test')
                    RETURNING id
                    """
                )
            ).scalar_one()

            document_id = connection.execute(
                text(
                    """
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
                        'integration.pdf',
                        :file_sha256,
                        1,
                        'word_window',
                        300,
                        50,
                        'test-model',
                        1536
                    )
                    RETURNING id
                    """
                ),
                {"file_sha256": uuid4().hex + uuid4().hex},
            ).scalar_one()

            chunk_id = connection.execute(
                text(
                    """
                    INSERT INTO public.document_chunks (
                        document_id,
                        chunk_number,
                        page_numbers,
                        content,
                        embedding
                    )
                    VALUES (
                        :document_id,
                        1,
                        ARRAY[1],
                        'Dos más dos son cuatro.',
                        CAST(:embedding AS extensions.vector)
                    )
                    RETURNING id
                    """
                ),
                {
                    "document_id": document_id,
                    "embedding": json.dumps([0.0] * 1536),
                },
            ).scalar_one()

            batch = import_module.ReviewedBatch(
                document_id=document_id,
                accepted_count=1,
                questions=[
                    {
                        "statement": "¿Cuánto es dos más dos?",
                        "explanation": "Dos más dos son cuatro.",
                        "options": [
                            {"content": "3", "is_correct": False},
                            {"content": "4", "is_correct": True},
                            {"content": "5", "is_correct": False},
                        ],
                        "source_ids": ["S1"],
                    }
                ],
                sources=[
                    {
                        "source_id": "S1",
                        "document_id": document_id,
                        "filename": "integration.pdf",
                        "chunk_id": chunk_id,
                        "chunk_number": 1,
                        "page_numbers": [1],
                    }
                ],
            )

            yield {
                "connection": connection,
                "topic_id": topic_id,
                "document_id": document_id,
                "chunk_id": chunk_id,
                "batch": batch,
            }

        finally:
            outer_transaction.rollback()


def test_import_saves_question_options_and_sources(import_case):
    case = import_case
    connection = case["connection"]

    result = import_module.import_questions(
        case["batch"],
        case["topic_id"],
    )

    assert result["status"] == "imported"
    assert result["inserted_count"] == 1
    question_id = result["question_ids"][0]

    question = connection.execute(
        text(
            """
            SELECT topic_id, statement, explanation
            FROM public.questions
            WHERE id = :id
            """
        ),
        {"id": question_id},
    ).mappings().one()

    assert dict(question) == {
        "topic_id": case["topic_id"],
        "statement": "¿Cuánto es dos más dos?",
        "explanation": "Dos más dos son cuatro.",
    }

    options = connection.execute(
        text(
            """
            SELECT position, content, is_correct
            FROM public.question_options
            WHERE question_id = :id
            ORDER BY position
            """
        ),
        {"id": question_id},
    ).mappings().all()

    assert [dict(option) for option in options] == [
        {"position": 1, "content": "3", "is_correct": False},
        {"position": 2, "content": "4", "is_correct": True},
        {"position": 3, "content": "5", "is_correct": False},
    ]

    chunk_ids = connection.execute(
        text(
            """
            SELECT chunk_id
            FROM public.question_sources
            WHERE question_id = :id
            """
        ),
        {"id": question_id},
    ).scalars().all()

    assert chunk_ids == [case["chunk_id"]]

    # Importing the same batch again must not create another question.
    repeated = import_module.import_questions(
        case["batch"],
        case["topic_id"],
    )

    assert repeated["status"] == "already_imported"
    assert repeated["inserted_count"] == 0

    count = connection.execute(
        text(
            """
            SELECT COUNT(*)
            FROM public.questions
            WHERE topic_id = :topic_id
            """
        ),
        {"topic_id": case["topic_id"]},
    ).scalar_one()

    assert count == 1


def test_import_rolls_back_when_saving_sources_fails(
    import_case,
    monkeypatch,
):
    case = import_case
    connection = case["connection"]
    original_insert = import_module.insert_question
    inserted_ids = []

    def insert_with_invalid_returned_id(connection, question):
        created = original_insert(connection, question)
        inserted_ids.append(created["id"])

        # Force a real foreign-key failure when saving the source.
        return {**created, "id": -1}

    monkeypatch.setattr(
        import_module,
        "insert_question",
        insert_with_invalid_returned_id,
    )

    with pytest.raises(IntegrityError):
        import_module.import_questions(
            case["batch"],
            case["topic_id"],
        )

    question_id = inserted_ids[0]

    for table, column in (
        ("questions", "id"),
        ("question_options", "question_id"),
        ("question_sources", "question_id"),
    ):
        # Table and column names come only from this fixed list.
        count = connection.execute(
            text(
                f"SELECT COUNT(*) FROM public.{table} "
                f"WHERE {column} = :id"
            ),
            {"id": question_id},
        ).scalar_one()

        assert count == 0

    import_count = connection.execute(
        text(
            """
            SELECT COUNT(*)
            FROM public.question_imports
            WHERE document_id = :document_id
            """
        ),
        {"document_id": case["document_id"]},
    ).scalar_one()

    assert import_count == 0

    # A failed import must not prevent a subsequent successful retry.
    monkeypatch.setattr(
        import_module,
        "insert_question",
        original_insert,
    )

    retry = import_module.import_questions(
        case["batch"],
        case["topic_id"],
    )

    assert retry["status"] == "imported"
    assert retry["inserted_count"] == 1