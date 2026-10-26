from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
import pytest

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


@pytest.fixture
def question_payload():
    return {
        "topic_id": 1,
        "statement": "¿Cuál es la capital de España?",
        "explanation": "Madrid es la capital de España.",
        "options": [
            {"content": "Barcelona", "is_correct": False},
            {"content": "Madrid", "is_correct": True},
            {"content": "Sevilla", "is_correct": False},
        ],
    }


@pytest.mark.parametrize("option_count", [3, 4, 5])
def test_create_question_returns_created_question(
    question_payload,
    option_count,
):
    question_payload["options"] = [
        {
            "content": f"Opción {position}",
            "is_correct": position == 2,
        }
        for position in range(1, option_count + 1)
    ]

    stored_question = {
        "id": 20,
        "topic_id": question_payload["topic_id"],
        "statement": question_payload["statement"],
        "explanation": question_payload["explanation"],
    }

    stored_options = [
        {
            "id": 100 + position,
            "position": position,
            "content": option["content"],
            "is_correct": option["is_correct"],
        }
        for position, option in enumerate(
            question_payload["options"],
            start=1,
        )
    ]

    topic_result = MagicMock()
    topic_result.mappings.return_value.one_or_none.return_value = {
        "id": 1
    }

    question_result = MagicMock()
    question_result.mappings.return_value.one.return_value = (
        stored_question
    )

    option_results = []

    for option in stored_options:
        option_result = MagicMock()
        option_result.mappings.return_value.one.return_value = option
        option_results.append(option_result)

    with patch("app.main.engine.begin") as mock_begin:
        connection = mock_begin.return_value.__enter__.return_value
        connection.execute.side_effect = [
            topic_result,
            question_result,
            *option_results,
        ]

        with TestClient(app) as client:
            response = client.post(
                "/questions",
                json=question_payload,
            )

    assert response.status_code == 201
    assert response.json() == {
        **stored_question,
        "options": stored_options,
    }

    assert connection.execute.call_count == 2 + option_count

    calls = connection.execute.call_args_list

    assert calls[0].args[1] == {"topic_id": 1}

    assert calls[1].args[1] == {
        "topic_id": question_payload["topic_id"],
        "statement": question_payload["statement"],
        "explanation": question_payload["explanation"],
    }

    for position, option in enumerate(
        question_payload["options"],
        start=1,
    ):
        assert calls[position + 1].args[1] == {
            "question_id": 20,
            "position": position,
            "content": option["content"],
            "is_correct": option["is_correct"],
        }


def test_create_question_rejects_missing_topic(question_payload):
    with patch("app.main.engine.begin") as mock_begin:
        connection = mock_begin.return_value.__enter__.return_value
        result = connection.execute.return_value
        result.mappings.return_value.one_or_none.return_value = None

        with TestClient(app) as client:
            response = client.post(
                "/questions",
                json=question_payload,
            )

    assert response.status_code == 404
    assert response.json() == {"detail": "Tema no encontrado"}
    connection.execute.assert_called_once()


def test_create_question_rejects_no_correct_option(question_payload):
    for option in question_payload["options"]:
        option["is_correct"] = False

    with patch("app.main.engine.begin") as mock_begin:
        with TestClient(app) as client:
            response = client.post(
                "/questions",
                json=question_payload,
            )

    assert response.status_code == 422
    mock_begin.assert_not_called()
