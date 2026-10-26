from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def attempt_connection():
    with patch("app.main.engine.begin") as mock_begin:
        connection = mock_begin.return_value.__enter__.return_value
        yield connection


def make_rows_result(rows):
    result = MagicMock()
    result.mappings.return_value = rows
    return result


def test_create_attempt_scores_and_saves_mixed_answers(
    attempt_connection,
):
    questions_result = make_rows_result([
        {"id": 1},
        {"id": 2},
        {"id": 3},
    ])

    options_result = make_rows_result([
        {"id": 11, "question_id": 1, "is_correct": True},
        {"id": 22, "question_id": 2, "is_correct": False},
    ])

    attempt_result = MagicMock()
    attempt_result.mappings.return_value.one.return_value = {
        "id": 42,
        "submitted_at": datetime(
            2026, 10, 26, 8, 0, tzinfo=timezone.utc
        ),
        "total_questions": 3,
        "correct_answers": 1,
        "incorrect_answers": 1,
        "unanswered_questions": 1,
        "accuracy_percentage": 33.33,
    }

    attempt_connection.execute.side_effect = [
        questions_result,
        options_result,
        attempt_result,
        MagicMock(),
    ]

    with TestClient(app) as client:
        response = client.post(
            "/attempts",
            json={
                "answers": [
                    {"question_id": 1, "selected_option_id": 11},
                    {"question_id": 2, "selected_option_id": 22},
                    {"question_id": 3, "selected_option_id": None},
                ]
            },
        )

    assert response.status_code == 201

    data = response.json()

    assert data["id"] == 42
    assert data["total_questions"] == 3
    assert data["correct_answers"] == 1
    assert data["incorrect_answers"] == 1
    assert data["unanswered_questions"] == 1
    assert data["accuracy_percentage"] == 33.33

    assert attempt_connection.execute.call_count == 4

    saved_answers = (
        attempt_connection.execute.call_args_list[3].args[1]
    )

    assert saved_answers == [
        {
            "attempt_id": 42,
            "question_id": 1,
            "selected_option_id": 11,
            "is_correct": True,
        },
        {
            "attempt_id": 42,
            "question_id": 2,
            "selected_option_id": 22,
            "is_correct": False,
        },
        {
            "attempt_id": 42,
            "question_id": 3,
            "selected_option_id": None,
            "is_correct": False,
        },
    ]


def test_create_attempt_rejects_missing_question(
    attempt_connection,
):
    attempt_connection.execute.side_effect = [
        make_rows_result([]),
    ]

    with TestClient(app) as client:
        response = client.post(
            "/attempts",
            json={
                "answers": [
                    {"question_id": 999999}
                ]
            },
        )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Pregunta 999999 no encontrada"
    }

    attempt_connection.execute.assert_called_once()


@pytest.mark.parametrize(
    "option_rows",
    [
        [],
        [{"id": 11, "question_id": 2, "is_correct": True}],
    ],
)
def test_create_attempt_rejects_invalid_option(
    attempt_connection,
    option_rows,
):
    attempt_connection.execute.side_effect = [
        make_rows_result([{"id": 1}]),
        make_rows_result(option_rows),
    ]

    with TestClient(app) as client:
        response = client.post(
            "/attempts",
            json={
                "answers": [
                    {"question_id": 1, "selected_option_id": 11}
                ]
            },
        )

    assert response.status_code == 422
    assert response.json() == {
        "detail": (
            "La opción seleccionada no pertenece a la pregunta 1"
        )
    }

    assert attempt_connection.execute.call_count == 2

def test_read_attempt_returns_stored_summary():
    stored_attempt = {
        "id": 1,
        "submitted_at": datetime(
            2026, 10, 26, 10, 0, tzinfo=timezone.utc
        ),
        "total_questions": 2,
        "correct_answers": 1,
        "incorrect_answers": 0,
        "unanswered_questions": 1,
        "accuracy_percentage": 50.0,
    }

    with patch("app.main.engine.connect") as mock_connect:
        connection = mock_connect.return_value.__enter__.return_value
        result = connection.execute.return_value
        result.mappings.return_value.one_or_none.return_value = (
            stored_attempt
        )

        with TestClient(app) as client:
            response = client.get("/attempts/1")

    assert response.status_code == 200
    assert response.json() == {
        "id": 1,
        "submitted_at": "2026-10-26T10:00:00Z",
        "total_questions": 2,
        "correct_answers": 1,
        "incorrect_answers": 0,
        "unanswered_questions": 1,
        "accuracy_percentage": 50.0,
    }

    connection.execute.assert_called_once()
    assert connection.execute.call_args.args[1] == {"attempt_id": 1}


def test_read_attempt_returns_404_for_missing_attempt():
    with patch("app.main.engine.connect") as mock_connect:
        connection = mock_connect.return_value.__enter__.return_value
        result = connection.execute.return_value
        result.mappings.return_value.one_or_none.return_value = None

        with TestClient(app) as client:
            response = client.get("/attempts/999999")

    assert response.status_code == 404
    assert response.json() == {"detail": "Práctica no encontrada"}


def test_read_attempt_rejects_zero_id():
    with patch("app.main.engine.connect") as mock_connect:
        with TestClient(app) as client:
            response = client.get("/attempts/0")

    assert response.status_code == 422
    mock_connect.assert_not_called()


def test_attempt_review_returns_summary_and_answers():
    summary = {
        "id": 1,
        "submitted_at": datetime(
            2026, 10, 26, 10, 0, tzinfo=timezone.utc
        ),
        "total_questions": 2,
        "correct_answers": 1,
        "incorrect_answers": 0,
        "unanswered_questions": 1,
        "accuracy_percentage": 50.0,
    }

    answers = [
        {
            "question_id": 1,
            "statement": "¿Cuál es la capital de España?",
            "selected_option_id": 2,
            "selected_option_content": "Madrid",
            "is_correct": True,
            "correct_option_id": 2,
            "correct_option_content": "Madrid",
            "explanation": "Madrid es la capital de España.",
        },
        {
            "question_id": 2,
            "statement": "¿Cuánto es 2 + 2?",
            "selected_option_id": None,
            "selected_option_content": None,
            "is_correct": False,
            "correct_option_id": 5,
            "correct_option_content": "4",
            "explanation": "La suma de dos y dos es cuatro.",
        },
    ]

    attempt_result = MagicMock()
    attempt_result.mappings.return_value.one_or_none.return_value = (
        summary
    )

    answers_result = make_rows_result(answers)

    with patch("app.main.engine.connect") as mock_connect:
        connection = mock_connect.return_value.__enter__.return_value
        connection.execute.side_effect = [
            attempt_result,
            answers_result,
        ]

        with TestClient(app) as client:
            response = client.get("/attempts/1/review")

    assert response.status_code == 200
    assert response.json() == {
        **summary,
        "submitted_at": "2026-10-26T10:00:00Z",
        "answers": answers,
    }

    assert connection.execute.call_count == 2

    for call in connection.execute.call_args_list:
        assert call.args[1] == {"attempt_id": 1}


def test_attempt_review_returns_404_for_missing_attempt():
    with patch("app.main.engine.connect") as mock_connect:
        connection = mock_connect.return_value.__enter__.return_value
        result = connection.execute.return_value
        result.mappings.return_value.one_or_none.return_value = None

        with TestClient(app) as client:
            response = client.get("/attempts/999999/review")

    assert response.status_code == 404
    assert response.json() == {"detail": "Práctica no encontrada"}
    connection.execute.assert_called_once()


def test_attempt_review_rejects_zero_id():
    with patch("app.main.engine.connect") as mock_connect:
        with TestClient(app) as client:
            response = client.get("/attempts/0/review")

    assert response.status_code == 422
    mock_connect.assert_not_called()