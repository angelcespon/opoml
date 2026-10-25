# schemas.py
from pydantic import BaseModel, ConfigDict, Field, model_validator
from typing import Self

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