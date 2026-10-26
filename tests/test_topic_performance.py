from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.mark.parametrize(
    (
        "attempt_count",
        "total_questions",
        "correct_answers",
        "incorrect_answers",
        "unanswered_questions",
        "expected_accuracy",
    ),
    [
        (1, 2, 1, 0, 1, 50.0),
        (0, 0, 0, 0, 0, None),
        (1, 2, 0, 1, 1, 0.0),
    ],
)
def test_topic_performance_returns_summary(
    attempt_count,
    total_questions,
    correct_answers,
    incorrect_answers,
    unanswered_questions,
    expected_accuracy,
):
    summary = {
        "attempt_count": attempt_count,
        "total_questions": total_questions,
        "correct_answers": correct_answers,
        "incorrect_answers": incorrect_answers,
        "unanswered_questions": unanswered_questions,
    }

    topic_result = MagicMock()
    topic_result.mappings.return_value.one_or_none.return_value = {
        "id": 1
    }

    performance_result = MagicMock()
    performance_result.mappings.return_value.one.return_value = summary

    with patch("app.main.engine.connect") as mock_connect:
        connection = mock_connect.return_value.__enter__.return_value
        connection.execute.side_effect = [
            topic_result,
            performance_result,
        ]

        with TestClient(app) as client:
            response = client.get("/topics/1/performance")

    assert response.status_code == 200
    assert response.json() == {
        "topic_id": 1,
        **summary,
        "accuracy_percentage": expected_accuracy,
    }

    assert connection.execute.call_count == 2

    for call in connection.execute.call_args_list:
        assert call.args[1] == {"topic_id": 1}


def test_topic_performance_rejects_missing_topic():
    with patch("app.main.engine.connect") as mock_connect:
        connection = mock_connect.return_value.__enter__.return_value
        result = connection.execute.return_value
        result.mappings.return_value.one_or_none.return_value = None

        with TestClient(app) as client:
            response = client.get("/topics/999999/performance")

    assert response.status_code == 404
    assert response.json() == {"detail": "Tema no encontrado"}
    connection.execute.assert_called_once()


def test_topic_performance_rejects_zero_id():
    with patch("app.main.engine.connect") as mock_connect:
        with TestClient(app) as client:
            response = client.get("/topics/0/performance")

    assert response.status_code == 422
    mock_connect.assert_not_called()