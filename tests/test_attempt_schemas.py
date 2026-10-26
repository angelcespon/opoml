import pytest
from pydantic import ValidationError

from app.schemas import AttemptCreate


def test_attempt_create_accepts_valid_answers():
    attempt = AttemptCreate(
        answers=[
            {"question_id": 1, "selected_option_id": 2},
            {"question_id": 2, "selected_option_id": 5},
        ]
    )

    assert len(attempt.answers) == 2
    assert attempt.answers[0].question_id == 1
    assert attempt.answers[0].selected_option_id == 2
    assert attempt.answers[1].question_id == 2
    assert attempt.answers[1].selected_option_id == 5


def test_attempt_create_accepts_unanswered_question():
    attempt = AttemptCreate(
        answers=[
            {"question_id": 1},
        ]
    )

    assert attempt.answers[0].question_id == 1
    assert attempt.answers[0].selected_option_id is None


def test_attempt_create_rejects_empty_answers():
    with pytest.raises(ValidationError):
        AttemptCreate(answers=[])


def test_attempt_create_rejects_duplicate_questions():
    with pytest.raises(
        ValidationError,
        match="Una pregunta no puede aparecer varias veces",
    ):
        AttemptCreate(
            answers=[
                {"question_id": 1, "selected_option_id": 2},
                {"question_id": 1, "selected_option_id": 3},
            ]
        )