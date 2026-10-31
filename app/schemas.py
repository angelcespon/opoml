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


class QuestionContent(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    statement: str = Field(min_length=1, max_length=5000)
    explanation: str | None = Field(default=None, max_length=10000)
    options: list[QuestionOptionCreate] = Field(
        min_length=3,
        max_length=5,
    )

    @model_validator(mode="after")
    def require_one_correct_option(self) -> Self:
        correct_count = sum(
            option.is_correct
            for option in self.options
        )

        if correct_count != 1:
            raise ValueError(
                "La pregunta debe tener exactamente una opción correcta."
            )

        return self


class QuestionCreate(QuestionContent):
    topic_id: int = Field(gt=0)
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


class QuestionSourceRead(BaseModel):
    document_id: int
    filename: str
    chunk_id: int
    chunk_number: int
    page_numbers: list[int]


class AttemptAnswerRead(BaseModel):
    question_id: int
    statement: str
    selected_option_id: int | None
    selected_option_content: str | None
    is_correct: bool
    correct_option_id: int | None
    correct_option_content: str | None
    explanation: str | None
    sources: list[QuestionSourceRead] = Field(default_factory=list)


class AttemptReviewRead(AttemptRead):
    answers: list[AttemptAnswerRead]


class DocumentAsk(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    question: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=20)


class DocumentSource(BaseModel):
    source_id: str
    document_id: int
    filename: str
    chunk_id: int
    chunk_number: int
    page_numbers: list[int]


class GenerationUsage(BaseModel):
    input_tokens: int
    cached_input_tokens: int
    uncached_input_tokens: int
    output_tokens: int


class DocumentAnswerUsage(BaseModel):
    embedding_model: str
    embedding_input_tokens: int
    generation_model: str
    generation: GenerationUsage | None


class DocumentAnswer(BaseModel):
    document_id: int
    question: str
    answer: str
    sources: list[DocumentSource]
    usage: DocumentAnswerUsage

class QuestionGenerateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question_count: int = Field(default=1, ge=1, le=100)
    option_count: int = Field(default=3, ge=3, le=5)


class GeneratedQuestion(QuestionContent):
    explanation: str = Field(min_length=1, max_length=10000)
    source_ids: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def require_valid_source_ids(self) -> Self:
        if any(
            not source_id.startswith("S")
            or not source_id[1:].isascii()
            or not source_id[1:].isdigit()
            or int(source_id[1:]) < 1
            for source_id in self.source_ids
        ):
            raise ValueError(
                "Source identifiers must use the format S1, S2, etc."
            )

        if len(self.source_ids) != len(set(self.source_ids)):
            raise ValueError("Source identifiers must be unique.")

        return self


class QuestionGenerationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: GeneratedQuestion | None
    reason: str | None

    @model_validator(mode="after")
    def require_consistent_result(self) -> Self:
        if self.question is None:
            if self.reason is None or not self.reason.strip():
                raise ValueError(
                    "A reason is required when no question is generated."
                )
        elif self.reason is not None:
            raise ValueError(
                "reason must be null when a question is generated."
            )

        return self

class QuestionBatchResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    questions: list[GeneratedQuestion] = Field(max_length=5)
    reason: str | None

    @model_validator(mode="after")
    def require_reason_for_empty_batch(self) -> Self:
        if not self.questions:
            if self.reason is None or not self.reason.strip():
                raise ValueError(
                    "A reason is required when no questions are generated."
                )

        return self


class QuestionReview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question_number: int = Field(ge=1)

    correct_option_number: int | None = Field(
        ge=1,
        le=5,
    )

    evidence_source_id: str | None
    evidence_quote: str | None

    accepted: bool
    issues: list[str]

    @model_validator(mode="after")
    def require_consistent_verdict(self) -> Self:
        if self.accepted:
            if self.issues:
                raise ValueError(
                    "Accepted questions cannot contain issues."
                )

            if (
                self.correct_option_number is None
                or not self.evidence_source_id
                or not self.evidence_quote
                or not self.evidence_quote.strip()
            ):
                raise ValueError(
                    "Accepted questions require an answer and evidence."
                )

        elif not self.issues:
            raise ValueError(
                "Rejected questions must include an issue."
            )

        return self


class QuestionBatchReview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reviews: list[QuestionReview]