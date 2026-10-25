from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.main import app


def test_read_question_returns_question_without_solution():
    question_result = MagicMock()
    question_result.mappings.return_value.one_or_none.return_value = {
        "id": 1,
        "topic_id": 1,
        "statement": "¿Cuál es la capital de España?",
        "explanation": "Madrid es la capital.",
    }

    options_result = MagicMock()
    options_result.mappings.return_value = [
        {
            "id": 10,
            "position": 1,
            "content": "Barcelona",
            "is_correct": False,
        },
        {
            "id": 11,
            "position": 2,
            "content": "Madrid",
            "is_correct": True,
        },
        {
            "id": 12,
            "position": 3,
            "content": "Sevilla",
            "is_correct": False,
        },
    ]

    with patch("app.main.engine.connect") as mock_connect:
        connection = mock_connect.return_value.__enter__.return_value
        connection.execute.side_effect = [
            question_result,
            options_result,
        ]

        with TestClient(app) as client:
            response = client.get("/questions/1")

    assert response.status_code == 200
    assert response.json() == {
        "id": 1,
        "topic_id": 1,
        "statement": "¿Cuál es la capital de España?",
        "options": [
            {"id": 10, "position": 1, "content": "Barcelona"},
            {"id": 11, "position": 2, "content": "Madrid"},
            {"id": 12, "position": 3, "content": "Sevilla"},
        ],
    }


def test_read_question_returns_404_for_missing_question():
    with patch("app.main.engine.connect") as mock_connect:
        connection = mock_connect.return_value.__enter__.return_value
        result = connection.execute.return_value
        result.mappings.return_value.one_or_none.return_value = None

        with TestClient(app) as client:
            response = client.get("/questions/999999")

    assert response.status_code == 404
    assert response.json() == {"detail": "Pregunta no encontrada"}
    connection.execute.assert_called_once()


def test_read_question_rejects_zero_id():
    with patch("app.main.engine.connect") as mock_connect:
        with TestClient(app) as client:
            response = client.get("/questions/0")

    assert response.status_code == 422
    mock_connect.assert_not_called()