# schemas.py
from pydantic import BaseModel, ConfigDict, Field, model_validator
from typing import Self
from datetime import datetime

class TopicCreate(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True
    )
    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)

class TopicRead(BaseModel):
    id: int
    name: str
    description: str | None

class QuestionOptionCreate(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True
    )

    content: str = Field(min_length=1, max_length=2000)
    is_correct: bool = False


class QuestionCreate(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True
    )

    topic_id: int = Field(gt=0)
    statement: str = Field(min_length=1, max_length=5000)
    explanation: str | None = Field(default=None, max_length=10000)
    options: list[QuestionOptionCreate] = Field(
        min_length=3,
        max_length=5
    )

    @model_validator(mode="after")
    def require_one_correct_option(self) -> Self:
        correct_count = 0

        for option in self.options:
            if option.is_correct:
                correct_count += 1

        if correct_count != 1:
            raise ValueError(
                "La pregunta debe tener exactamente una opción correcta."
            )

        return self

class QuestionOptionCreated(BaseModel):
    id: int
    position: int
    content: str
    is_correct: bool


class QuestionCreated(BaseModel):
    id: int
    topic_id: int
    statement: str
    explanation: str | None
    options: list[QuestionOptionCreated]

class QuestionOptionRead(BaseModel):
    id: int
    position: int
    content: str


class QuestionRead(BaseModel):
    id: int
    topic_id: int
    statement: str
    options: list[QuestionOptionRead]

class AttemptAnswerCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question_id: int = Field(gt=0)
    selected_option_id: int | None = Field(
        default=None,
        gt=0,
    )


class AttemptCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    answers: list[AttemptAnswerCreate] = Field(
        min_length=1,
        max_length=100,
    )

    @model_validator(mode="after")
    def require_unique_questions(self) -> Self:
        question_ids = [
            answer.question_id
            for answer in self.answers
        ]

        if len(question_ids) != len(set(question_ids)):
            raise ValueError(
                "Una pregunta no puede aparecer varias veces "
                "en la misma práctica."
            )

        return self

class AttemptRead(BaseModel):
    id: int
    submitted_at: datetime
    total_questions: int
    correct_answers: int
    incorrect_answers: int
    unanswered_questions: int
    accuracy_percentage: float

class TopicPerformanceRead(BaseModel):
    topic_id: int
    attempt_count: int
    total_questions: int
    correct_answers: int
    incorrect_answers: int
    unanswered_questions: int
    accuracy_percentage: float | None

class AttemptAnswerRead(BaseModel):
    question_id: int
    statement: str
    selected_option_id: int | None
    selected_option_content: str | None
    is_correct: bool
    correct_option_id: int | None
    correct_option_content: str | None
    explanation: str | None


class AttemptReviewRead(AttemptRead):
    answers: list[AttemptAnswerRead]