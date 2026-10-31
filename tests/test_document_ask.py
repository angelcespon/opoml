from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.retrieval import DocumentEmptyError, DocumentNotFoundError


@pytest.fixture
def answer_result():
    return {
        "document_id": 1,
        "question": "¿Puedo ir acompañado?",
        "answer": "La documentación reconoce ese derecho. [S1]",
        "sources": [
            {
                "source_id": "S1",
                "document_id": 1,
                "filename": "example.pdf",
                "chunk_id": 10,
                "chunk_number": 1,
                "page_numbers": [2],
            }
        ],
        "usage": {
            "embedding_model": "test-embedding-model",
            "embedding_input_tokens": 6,
            "generation_model": "test-generation-model",
            "generation": {
                "input_tokens": 100,
                "cached_input_tokens": 0,
                "uncached_input_tokens": 100,
                "output_tokens": 20,
            },
        },
    }


def test_ask_document_returns_answer(answer_result):
    with patch(
        "app.main.answer_document",
        return_value=answer_result,
    ) as mock_answer:
        with TestClient(app) as client:
            response = client.post(
                "/documents/1/ask",
                json={"question": "  ¿Puedo ir acompañado?  "},
            )

    assert response.status_code == 200
    assert response.json() == answer_result
    mock_answer.assert_called_once_with(
        document_id=1,
        question="¿Puedo ir acompañado?",
        top_k=5,
    )


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"question": "   "},
        {"question": "a" * 2001},
        {"question": "Pregunta", "top_k": 0},
        {"question": "Pregunta", "top_k": 21},
        {"question": "Pregunta", "unexpected": True},
    ],
)
def test_ask_document_rejects_invalid_payload(payload):
    with patch("app.main.answer_document") as mock_answer:
        with TestClient(app) as client:
            response = client.post(
                "/documents/1/ask",
                json=payload,
            )

    assert response.status_code == 422
    mock_answer.assert_not_called()


def test_ask_document_rejects_zero_id():
    with patch("app.main.answer_document") as mock_answer:
        with TestClient(app) as client:
            response = client.post(
                "/documents/0/ask",
                json={"question": "¿Puedo ir acompañado?"},
            )

    assert response.status_code == 422
    mock_answer.assert_not_called()


@pytest.mark.parametrize(
    "error, expected_status, expected_detail",
    [
        (
            DocumentNotFoundError("Missing document"),
            404,
            "Documento no encontrado.",
        ),
        (
            DocumentEmptyError("Missing chunks"),
            409,
            "El documento no tiene fragmentos disponibles.",
        ),
        (
            RuntimeError("Internal diagnostic information"),
            500,
            "No se ha podido generar una respuesta válida.",
        ),
    ],
)
def test_ask_document_handles_errors(
    error,
    expected_status,
    expected_detail,
):
    with patch(
        "app.main.answer_document",
        side_effect=error,
    ):
        with TestClient(app) as client:
            response = client.post(
                "/documents/1/ask",
                json={"question": "¿Puedo ir acompañado?"},
            )

    assert response.status_code == expected_status
    assert response.json() == {"detail": expected_detail}