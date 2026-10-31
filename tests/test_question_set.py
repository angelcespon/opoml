from unittest.mock import patch

import pytest

from app.generate_question_set import generate_question_set


def make_context(chunk_id):
    return {
        "document": {"id": 1, "filename": "example.pdf"},
        "sources": [
            {
                "source_id": "S1",
                "chunk_id": chunk_id,
                "chunk_number": chunk_id,
                "page_numbers": [1],
                "text": "Contenido de prueba.",
            }
        ],
    }


def make_batch(statements, chunk_id):
    return {
        "document_id": 1,
        "questions": [
            {
                "statement": statement,
                "explanation": "Explicación de prueba.",
                "options": [
                    {"content": "A", "is_correct": True},
                    {"content": "B", "is_correct": False},
                    {"content": "C", "is_correct": False},
                ],
                "source_ids": ["S1"],
            }
            for statement in statements
        ],
        "sources": [
            {
                "source_id": "S1",
                "document_id": 1,
                "filename": "example.pdf",
                "chunk_id": chunk_id,
                "chunk_number": chunk_id,
                "page_numbers": [1],
            }
        ],
        "reason": None if statements else "Información insuficiente.",
        "generation_model": "test-model",
        "usage": {"input_tokens": 10, "output_tokens": 10},
    }


def make_review(verdicts):
    return {
        "reviews": [
            {
                "question_number": number,
                "accepted": accepted,
            }
            for number, accepted in enumerate(verdicts, start=1)
        ],
        "review_model": "test-review-model",
        "usage": {"input_tokens": 10, "output_tokens": 5},
    }


@pytest.fixture
def dependencies():
    with (
        patch(
            "app.generate_question_set.get_generation_contexts"
        ) as contexts,
        patch(
            "app.generate_question_set.generate_questions_from_context"
        ) as generate,
        patch(
            "app.generate_question_set.review_questions"
        ) as review,
    ):
        yield contexts, generate, review


def test_set_stops_at_target_and_preserves_sources(dependencies, tmp_path):
    contexts, generate, review = dependencies
    contexts.return_value = [
        make_context(10),
        make_context(20),
        make_context(30),
    ]
    generate.side_effect = [
        make_batch([f"Pregunta {number}" for number in range(5)], 10),
        make_batch(["Pregunta final"], 20),
    ]
    review.side_effect = [
        make_review([True] * 5),
        make_review([True]),
    ]

    result = generate_question_set(1, 6, 3, 3, tmp_path)

    assert result["status"] == "complete"
    assert result["accepted_count"] == 6
    assert result["processed_batches"] == 2
    assert generate.call_count == 2
    assert review.call_count == 2

    assert [
        call.kwargs["question_count"]
        for call in generate.call_args_list
    ] == [5, 1]

    # Both original contexts used S1, but refer to different chunks.
    sources_by_id = {
        source["source_id"]: source["chunk_id"]
        for source in result["sources"]
    }

    assert len(sources_by_id) == 2

    for question in result["questions"][:5]:
        assert [
            sources_by_id[source_id]
            for source_id in question["source_ids"]
        ] == [10]

    final_question = result["questions"][5]
    assert [
        sources_by_id[source_id]
        for source_id in final_question["source_ids"]
    ] == [20]

    assert (tmp_path / "result.json").is_file()


def test_set_compensates_for_rejections(dependencies, tmp_path):
    contexts, generate, review = dependencies
    contexts.return_value = [make_context(10), make_context(20)]
    generate.side_effect = [
        make_batch(["Pregunta aceptada", "Pregunta rechazada"], 10),
        make_batch(["Pregunta sustituta"], 20),
    ]
    review.side_effect = [
        make_review([True, False]),
        make_review([True]),
    ]

    result = generate_question_set(1, 2, 3, 2, tmp_path)

    assert result["status"] == "complete"
    assert result["generated_count"] == 3
    assert result["accepted_count"] == 2
    assert result["rejected_count"] == 1
    assert [
        question["statement"]
        for question in result["questions"]
    ] == ["Pregunta aceptada", "Pregunta sustituta"]
    assert generate.call_args_list[1].kwargs["question_count"] == 1


def test_set_discards_duplicates_and_returns_partial(dependencies, tmp_path):
    contexts, generate, review = dependencies
    contexts.return_value = [make_context(10), make_context(20)]
    generate.side_effect = [
        make_batch(["Pregunta repetida"], 10),
        make_batch(["  PREGUNTA   REPETIDA  "], 20),
    ]
    review.side_effect = [
        make_review([True]),
        make_review([True]),
    ]

    result = generate_question_set(1, 2, 3, 2, tmp_path)

    assert result["status"] == "partial"
    assert result["accepted_count"] == 1
    assert result["duplicate_count"] == 1
    assert result["processed_batches"] == 2
    assert result["reason"]
    assert generate.call_count == 2
    assert [source["chunk_id"] for source in result["sources"]] == [10]


def test_set_skips_review_when_generation_is_empty(dependencies, tmp_path):
    contexts, generate, review = dependencies
    contexts.return_value = [make_context(10)]
    generate.return_value = make_batch([], 10)

    result = generate_question_set(1, 2, 3, 1, tmp_path)

    assert result["status"] == "partial"
    assert result["accepted_count"] == 0
    assert result["questions"] == []
    assert result["sources"] == []
    review.assert_not_called()