from copy import deepcopy
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

from app.main import app
from app.retrieval import DocumentEmptyError, DocumentNotFoundError


@pytest.fixture
def generation_dependencies():
    sources = [
        {
            "source_id": f"S{number}",
            "document_id": 1,
            "filename": "example.pdf",
            "chunk_id": number * 10,
            "chunk_number": number,
            "page_numbers": [number],
        }
        for number in (1, 2)
    ]

    questions = [
        {
            "statement": f"Pregunta de prueba {number}",
            "explanation": "Explicación de prueba.",
            "options": [
                {"content": "Opción A", "is_correct": True},
                {"content": "Opción B", "is_correct": False},
                {"content": "Opción C", "is_correct": False},
            ],
            "source_ids": [f"S{number}"],
        }
        for number in (1, 2)
    ]

    batch = {
        "document_id": 1,
        "questions": questions,
        "sources": sources,
        "reason": None,
        "usage": {"input_tokens": 100, "output_tokens": 50},
    }

    review = {
        "reviews": [
            {"question_number": 1, "accepted": True},
            {"question_number": 2, "accepted": True},
        ],
        "usage": {"input_tokens": 200, "output_tokens": 30},
    }

    context = {"document": {"id": 1}, "sources": []}

    with (
        patch("app.main.engine.connect") as connect,
        patch(
            "app.main.get_generation_context",
            return_value=context,
        ) as get_context,
        patch(
            "app.main.generate_questions_from_context",
            return_value=batch,
        ) as generate,
        patch(
            "app.main.review_questions",
            return_value=review,
        ) as reviewer,
        patch(
            "app.main.import_questions",
            return_value={
                "status": "imported",
                "inserted_count": 2,
                "question_ids": [101, 102],
            },
        ) as importer,
    ):
        connection = connect.return_value.__enter__.return_value
        connection.execute.return_value.scalar_one_or_none.return_value = 2

        yield {
            "connect": connect,
            "connection": connection,
            "get_context": get_context,
            "generate": generate,
            "reviewer": reviewer,
            "importer": importer,
            "context": context,
            "batch": batch,
            "review": review,
        }


def test_generation_saves_accepted_questions(generation_dependencies):
    deps = generation_dependencies

    with TestClient(app) as client:
        response = client.post(
            "/documents/1/generate-questions",
            json={"topic_id": 2, "question_count": 2, "option_count": 3},
        )

    assert response.status_code == 200
    assert response.json() == {
        "status": "imported",
        "document_id": 1,
        "topic_id": 2,
        "requested_count": 2,
        "generated_count": 2,
        "accepted_count": 2,
        "rejected_count": 0,
        "inserted_count": 2,
        "question_ids": [101, 102],
        "generation_reason": None,
        "usage": {
            "generation": deps["batch"]["usage"],
            "review": deps["review"]["usage"],
        },
    }

    deps["get_context"].assert_called_once_with(1)
    deps["generate"].assert_called_once_with(
        context=deps["context"],
        question_count=2,
        option_count=3,
        reasoning_effort="none",
    )
    deps["reviewer"].assert_called_once_with(
        deps["context"],
        deps["batch"],
    )
    deps["importer"].assert_called_once()

    arguments = deps["importer"].call_args.kwargs
    assert arguments["topic_id"] == 2
    assert arguments["batch"].accepted_count == 2
    assert [
        question.model_dump()
        for question in arguments["batch"].questions
    ] == deps["batch"]["questions"]


@pytest.mark.parametrize("accepted_numbers", [[2], []])
def test_generation_filters_rejected_questions(
    generation_dependencies,
    accepted_numbers,
):
    deps = generation_dependencies

    for item in deps["review"]["reviews"]:
        item["accepted"] = item["question_number"] in accepted_numbers

    deps["importer"].return_value = {
        "status": "imported",
        "inserted_count": 1,
        "question_ids": [102],
    }

    with TestClient(app) as client:
        response = client.post(
            "/documents/1/generate-questions",
            json={"topic_id": 2, "question_count": 2},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["accepted_count"] == len(accepted_numbers)
    assert data["rejected_count"] == 2 - len(accepted_numbers)

    if accepted_numbers:
        deps["importer"].assert_called_once()
        saved_batch = deps["importer"].call_args.kwargs["batch"]

        assert len(saved_batch.questions) == 1
        assert saved_batch.questions[0].model_dump() == (
            deps["batch"]["questions"][1]
        )
        assert [
            source.model_dump()
            for source in saved_batch.sources
        ] == [deps["batch"]["sources"][1]]
        assert data["question_ids"] == [102]
    else:
        deps["importer"].assert_not_called()
        assert data["status"] == "no_questions_accepted"
        assert data["inserted_count"] == 0
        assert data["question_ids"] == []


def test_generation_skips_review_for_empty_batch(generation_dependencies):
    deps = generation_dependencies
    empty_batch = deepcopy(deps["batch"])
    empty_batch.update({
        "questions": [],
        "sources": [],
        "reason": "Información insuficiente.",
    })
    deps["generate"].return_value = empty_batch

    with TestClient(app) as client:
        response = client.post(
            "/documents/1/generate-questions",
            json={"topic_id": 2},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["generated_count"] == 0
    assert data["inserted_count"] == 0
    assert data["generation_reason"] == "Información insuficiente."
    assert data["usage"]["review"] is None
    deps["reviewer"].assert_not_called()
    deps["importer"].assert_not_called()


def test_generation_rejects_missing_topic(generation_dependencies):
    deps = generation_dependencies
    deps["connection"].execute.return_value.scalar_one_or_none.return_value = (
        None
    )

    with TestClient(app) as client:
        response = client.post(
            "/documents/1/generate-questions",
            json={"topic_id": 999999},
        )

    assert response.status_code == 404
    assert response.json() == {"detail": "Tema no encontrado."}
    deps["get_context"].assert_not_called()
    deps["generate"].assert_not_called()
    deps["reviewer"].assert_not_called()
    deps["importer"].assert_not_called()


@pytest.mark.parametrize(
    "document_id, payload",
    [
        (0, {"topic_id": 2}),
        (1, {}),
        (1, {"topic_id": 0}),
        (1, {"topic_id": 2, "question_count": 0}),
        (1, {"topic_id": 2, "question_count": 6}),
        (1, {"topic_id": 2, "option_count": 2}),
        (1, {"topic_id": 2, "option_count": 6}),
        (1, {"topic_id": 2, "unexpected": True}),
    ],
)
def test_generation_rejects_invalid_input(
    generation_dependencies,
    document_id,
    payload,
):
    deps = generation_dependencies

    with TestClient(app) as client:
        response = client.post(
            f"/documents/{document_id}/generate-questions",
            json=payload,
        )

    assert response.status_code == 422
    deps["connect"].assert_not_called()
    deps["get_context"].assert_not_called()
    deps["generate"].assert_not_called()
    deps["importer"].assert_not_called()


@pytest.mark.parametrize(
    "dependency, error, status, detail",
    [
        (
            "get_context",
            DocumentNotFoundError("Internal diagnostic"),
            404,
            "Documento no encontrado.",
        ),
        (
            "get_context",
            DocumentEmptyError("Internal diagnostic"),
            409,
            "El documento no tiene fragmentos disponibles.",
        ),
        (
            "get_context",
            SQLAlchemyError("Internal diagnostic"),
            503,
            "No se ha podido acceder a la base de datos.",
        ),
        (
            "generate",
            RuntimeError("Internal diagnostic"),
            500,
            "No se ha podido completar la generación de preguntas.",
        ),
        (
            "reviewer",
            RuntimeError("Internal diagnostic"),
            500,
            "No se ha podido completar la generación de preguntas.",
        ),
    ],
)
def test_generation_handles_errors(
    generation_dependencies,
    dependency,
    error,
    status,
    detail,
):
    deps = generation_dependencies
    deps[dependency].side_effect = error

    with TestClient(app) as client:
        response = client.post(
            "/documents/1/generate-questions",
            json={"topic_id": 2, "question_count": 2},
        )

    assert response.status_code == status
    assert response.json() == {"detail": detail}
    deps["importer"].assert_not_called()