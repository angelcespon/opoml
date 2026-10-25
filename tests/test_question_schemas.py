import pytest
from pydantic import ValidationError

from app.schemas import QuestionCreate


@pytest.fixture
def question_data():
    return {
        "topic_id": 1,
        "statement": " ¿Cuál es la opción correcta? ",
        "options": [
            {"content": "Opción A", "is_correct": False},
            {"content": " Opción B ", "is_correct": True},
            {"content": "Opción C", "is_correct": False},
        ],
    }


def test_question_create_accepts_valid_data(question_data):
    question = QuestionCreate(**question_data)

    assert question.topic_id == 1
    assert question.statement == "¿Cuál es la opción correcta?"
    assert question.explanation is None

    assert len(question.options) == 3
    assert question.options[1].content == "Opción B"
    assert question.options[1].is_correct is True


@pytest.mark.parametrize("option_count", [3, 4, 5])
def test_question_create_accepts_valid_option_count(
    question_data,
    option_count,
):
    question_data["options"] = [
        {
            "content": f"Opción {position}",
            "is_correct": position == 1,
        }
        for position in range(1, option_count + 1)
    ]

    question = QuestionCreate(**question_data)

    assert len(question.options) == option_count


@pytest.mark.parametrize("option_count", [2, 6])
def test_question_create_rejects_invalid_option_count(
    question_data,
    option_count,
):
    question_data["options"] = [
        {
            "content": f"Opción {position}",
            "is_correct": position == 1,
        }
        for position in range(1, option_count + 1)
    ]

    with pytest.raises(ValidationError):
        QuestionCreate(**question_data)


@pytest.mark.parametrize("correct_count", [0, 2, 3])
def test_question_create_rejects_invalid_correct_count(
    question_data,
    correct_count,
):
    for index, option in enumerate(question_data["options"]):
        option["is_correct"] = index < correct_count

    with pytest.raises(
        ValidationError,
        match="exactamente una opción correcta",
    ):
        QuestionCreate(**question_data)