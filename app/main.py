# main.py

from fastapi import FastAPI, HTTPException, Path
from openai import APIError
from sqlalchemy import bindparam, text
from sqlalchemy.exc import SQLAlchemyError
from typing import Annotated
import logging

from app.database import engine
from app.ask_document import answer_document
from app.retrieval import DocumentEmptyError, DocumentNotFoundError
from app.schemas import (
    AttemptCreate,
    AttemptRead,
    QuestionCreate,
    QuestionCreated,
    QuestionRead,
    TopicCreate,
    TopicRead,
    TopicPerformanceRead,
    AttemptReviewRead,
    DocumentAsk,
    DocumentAnswer
)

logger = logging.getLogger(__name__)

# Crear aplicación web
app = FastAPI(title="OpoML")

# GET
@app.get("/")
def root():
    return {"status": "ok", "service": "OpoML"}

@app.get("/topics", response_model=list[TopicRead])
def list_topics():
    with engine.connect() as connection:
        result = connection.execute(
            text(
                """
                SELECT id, name, description
                FROM public.topics
                ORDER BY id
                """
            )
        )

        topics = [
            dict(topic)
            for topic in result.mappings()
        ]

    return topics

@app.get("/topics/{topic_id}", response_model=TopicRead)
def read_topic(topic_id: Annotated[int, Path(gt=0)]):
    with engine.connect() as connection:
        result = connection.execute(
            text(
                """
                SELECT id, name, description
                FROM public.topics
                WHERE id = :topic_id
                """
            ),
            {"topic_id": topic_id},
        )

        topic = result.mappings().one_or_none()

    if topic is None:
        raise HTTPException(
            status_code=404,
            detail="Tema no encontrado",
        )

    return dict(topic)

@app.get("/questions/{question_id}", response_model=QuestionRead)
def read_question(question_id: Annotated[int, Path(gt=0)]):
    with engine.connect() as connection:
        question_result = connection.execute(
            text(
                """
                SELECT id, topic_id, statement
                FROM public.questions
                WHERE id = :question_id
                """
            ),
            {"question_id": question_id},
        )

        question = question_result.mappings().one_or_none()

        if question is None:
            raise HTTPException(
                status_code=404,
                detail="Pregunta no encontrada",
            )

        options_result = connection.execute(
            text(
                """
                SELECT id, position, content
                FROM public.question_options
                WHERE question_id = :question_id
                ORDER BY position
                """
            ),
            {"question_id": question_id},
        )

        response = dict(question)
        response["options"] = [
            dict(option)
            for option in options_result.mappings()
        ]

    return response

@app.get("/attempts/{attempt_id}", response_model=AttemptRead)
def read_attempt(attempt_id: Annotated[int, Path(gt=0)]):
    with engine.connect() as connection:
        result = connection.execute(
            text(
                """
                SELECT
                    id,
                    submitted_at,
                    total_questions,
                    correct_answers,
                    incorrect_answers,
                    unanswered_questions,
                    accuracy_percentage
                FROM public.practice_attempts
                WHERE id = :attempt_id
                """
            ),
            {"attempt_id": attempt_id},
        )

        attempt = result.mappings().one_or_none()

        if attempt is None:
            raise HTTPException(
                status_code=404,
                detail="Práctica no encontrada",
            )

        response = dict(attempt)

    return response

@app.get(
    "/topics/{topic_id}/performance",
    response_model=TopicPerformanceRead,
)
def read_topic_performance(
    topic_id: Annotated[int, Path(gt=0)],
):
    with engine.connect() as connection:
        topic_result = connection.execute(
            text(
                """
                SELECT id
                FROM public.topics
                WHERE id = :topic_id
                """
            ),
            {"topic_id": topic_id},
        )

        if topic_result.mappings().one_or_none() is None:
            raise HTTPException(
                status_code=404,
                detail="Tema no encontrado",
            )

        performance_result = connection.execute(
            text(
                """
                SELECT
                    COUNT(DISTINCT a.attempt_id) AS attempt_count,
                    COUNT(*) AS total_questions,

                    COUNT(*) FILTER (
                        WHERE a.is_correct = TRUE
                    ) AS correct_answers,

                    COUNT(*) FILTER (
                        WHERE a.is_correct = FALSE
                          AND a.selected_option_id IS NOT NULL
                    ) AS incorrect_answers,

                    COUNT(*) FILTER (
                        WHERE a.selected_option_id IS NULL
                    ) AS unanswered_questions

                FROM public.attempt_answers AS a

                JOIN public.questions AS q
                    ON q.id = a.question_id

                WHERE q.topic_id = :topic_id
                """
            ),
            {"topic_id": topic_id},
        )

        response = dict(performance_result.mappings().one())

    response["topic_id"] = topic_id
    total_questions = response["total_questions"]

    response["accuracy_percentage"] = (
        round(
            response["correct_answers"] / total_questions * 100,
            2,
        )
        if total_questions > 0
        else None
    )

    return response

@app.get(
    "/attempts/{attempt_id}/review",
    response_model=AttemptReviewRead,
)
def read_attempt_review(
    attempt_id: Annotated[int, Path(gt=0)],
):
    with engine.connect() as connection:
        attempt_result = connection.execute(
            text(
                """
                SELECT
                    id,
                    submitted_at,
                    total_questions,
                    correct_answers,
                    incorrect_answers,
                    unanswered_questions,
                    accuracy_percentage
                FROM public.practice_attempts
                WHERE id = :attempt_id
                """
            ),
            {"attempt_id": attempt_id},
        )

        attempt = attempt_result.mappings().one_or_none()

        if attempt is None:
            raise HTTPException(
                status_code=404,
                detail="Práctica no encontrada",
            )

        answers_result = connection.execute(
            text(
                """
                SELECT
                    a.question_id,
                    q.statement,
                    a.selected_option_id,
                    s.content AS selected_option_content,
                    a.is_correct,
                    c.id AS correct_option_id,
                    c.content AS correct_option_content,
                    q.explanation

                FROM public.attempt_answers AS a

                JOIN public.questions AS q
                    ON q.id = a.question_id

                LEFT JOIN public.question_options AS s
                    ON s.id = a.selected_option_id
                    AND s.question_id = a.question_id

                LEFT JOIN public.question_options AS c
                    ON c.question_id = a.question_id
                    AND c.is_correct = TRUE

                WHERE a.attempt_id = :attempt_id

                ORDER BY a.question_id
                """
            ),
            {"attempt_id": attempt_id},
        )

        response = dict(attempt)

        response["answers"] = [
            dict(answer)
            for answer in answers_result.mappings()
        ]

    return response


# POST
@app.post("/topics/validate")
def validate_topic(topic: TopicCreate):
    return topic.model_dump()

@app.post("/topics", response_model=TopicRead, status_code=201)
def create_topic(topic: TopicCreate):
    with engine.begin() as connection:
        result = connection.execute(
            text(
                """
                INSERT INTO public.topics (name, description)
                VALUES (:name, :description)
                RETURNING id, name, description
                """
            ),
            topic.model_dump(),
        )

        created_topic = dict(result.mappings().one())

    return created_topic

@app.post("/questions", response_model=QuestionCreated, status_code=201)
def create_question(question: QuestionCreate):
    with engine.begin() as connection:
        topic_result = connection.execute(
            text("SELECT id FROM public.topics WHERE id = :topic_id"),
            {"topic_id": question.topic_id},
        )

        if topic_result.mappings().one_or_none() is None:
            raise HTTPException(
                status_code=404,
                detail="Tema no encontrado",
            )

        question_result = connection.execute(
            text(
                """
                INSERT INTO public.questions (
                    topic_id, statement, explanation
                )
                VALUES (:topic_id, :statement, :explanation)
                RETURNING id, topic_id, statement, explanation
                """
            ),
            {
                "topic_id": question.topic_id,
                "statement": question.statement,
                "explanation": question.explanation,
            },
        )

        created_question = dict(question_result.mappings().one())
        created_options = []

        for position, option in enumerate(question.options, start=1):
            option_result = connection.execute(
                text(
                    """
                    INSERT INTO public.question_options (
                        question_id, position, content, is_correct
                    )
                    VALUES (
                        :question_id, :position, :content, :is_correct
                    )
                    RETURNING id, position, content, is_correct
                    """
                ),
                {
                    "question_id": created_question["id"],
                    "position": position,
                    "content": option.content,
                    "is_correct": option.is_correct,
                },
            )

            created_options.append(
                dict(option_result.mappings().one())
            )

        created_question["options"] = created_options

    return created_question

@app.post("/attempts", response_model=AttemptRead, status_code=201)
def create_attempt(attempt: AttemptCreate):
    question_ids = [
        answer.question_id
        for answer in attempt.answers
    ]

    selected_option_ids = [
        answer.selected_option_id
        for answer in attempt.answers
        if answer.selected_option_id is not None
    ]

    correct_answers = 0
    unanswered_questions = 0
    answer_records = []

    with engine.begin() as connection:
        # Recuperar todas las preguntas solicitadas.
        questions_result = connection.execute(
            text(
                """
                SELECT id
                FROM public.questions
                WHERE id IN :question_ids
                """
            ).bindparams(
                bindparam("question_ids", expanding=True)
            ),
            {"question_ids": question_ids},
        )

        existing_question_ids = {
            question["id"]
            for question in questions_result.mappings()
        }

        # Recuperar todas las opciones seleccionadas.
        options_by_id = {}

        if selected_option_ids:
            options_result = connection.execute(
                text(
                    """
                    SELECT id, question_id, is_correct
                    FROM public.question_options
                    WHERE id IN :option_ids
                    """
                ).bindparams(
                    bindparam("option_ids", expanding=True)
                ),
                {"option_ids": selected_option_ids},
            )

            options_by_id = {
                option["id"]: dict(option)
                for option in options_result.mappings()
            }

        # Validar y corregir utilizando los datos recuperados.
        for answer in attempt.answers:
            if answer.question_id not in existing_question_ids:
                raise HTTPException(
                    status_code=404,
                    detail=f"Pregunta {answer.question_id} no encontrada",
                )

            if answer.selected_option_id is None:
                is_correct = False
                unanswered_questions += 1
            else:
                option = options_by_id.get(answer.selected_option_id)

                if (
                    option is None
                    or option["question_id"] != answer.question_id
                ):
                    raise HTTPException(
                        status_code=422,
                        detail=(
                            "La opción seleccionada no pertenece "
                            f"a la pregunta {answer.question_id}"
                        ),
                    )

                is_correct = option["is_correct"]

                if is_correct:
                    correct_answers += 1

            answer_records.append(
                {
                    "question_id": answer.question_id,
                    "selected_option_id": answer.selected_option_id,
                    "is_correct": is_correct,
                }
            )

        # Calcular el resumen definitivo.
        total_questions = len(attempt.answers)

        incorrect_answers = (
            total_questions - correct_answers - unanswered_questions
        )

        accuracy_percentage = round(
            correct_answers / total_questions * 100,
            2,
        )

        # Guardar la práctica y su resumen.
        attempt_result = connection.execute(
            text(
                """
                INSERT INTO public.practice_attempts (
                    total_questions,
                    correct_answers,
                    incorrect_answers,
                    unanswered_questions,
                    accuracy_percentage
                )
                VALUES (
                    :total_questions,
                    :correct_answers,
                    :incorrect_answers,
                    :unanswered_questions,
                    :accuracy_percentage
                )
                RETURNING
                    id,
                    submitted_at,
                    total_questions,
                    correct_answers,
                    incorrect_answers,
                    unanswered_questions,
                    accuracy_percentage
                """
            ),
            {
                "total_questions": total_questions,
                "correct_answers": correct_answers,
                "incorrect_answers": incorrect_answers,
                "unanswered_questions": unanswered_questions,
                "accuracy_percentage": accuracy_percentage,
            },
        )

        created_attempt = dict(attempt_result.mappings().one())

        for record in answer_records:
            record["attempt_id"] = created_attempt["id"]

        # Guardar todas las respuestas por lotes.
        connection.execute(
            text(
                """
                INSERT INTO public.attempt_answers (
                    attempt_id,
                    question_id,
                    selected_option_id,
                    is_correct
                )
                VALUES (
                    :attempt_id,
                    :question_id,
                    :selected_option_id,
                    :is_correct
                )
                """
            ),
            answer_records,
        )

        response = AttemptRead(**created_attempt)

    return response

@app.post(
    "/documents/{document_id}/ask",
    response_model=DocumentAnswer,
)
def ask_document_endpoint(
    document_id: Annotated[int, Path(gt=0)],
    request: DocumentAsk,
):
    try:
        return answer_document(
            document_id=document_id,
            question=request.question,
            top_k=request.top_k,
        )

    except DocumentNotFoundError as error:
        raise HTTPException(
            status_code=404,
            detail="Documento no encontrado.",
        ) from error

    except DocumentEmptyError as error:
        raise HTTPException(
            status_code=409,
            detail="El documento no tiene fragmentos disponibles.",
        ) from error

    except SQLAlchemyError as error:
        logger.exception("Database failure while answering a question.")
        raise HTTPException(
            status_code=503,
            detail="No se ha podido consultar la base de datos.",
        ) from error

    except APIError as error:
        logger.exception("OpenAI request failed.")
        raise HTTPException(
            status_code=503,
            detail="El servicio de IA no está disponible en este momento.",
        ) from error

    except RuntimeError as error:
        logger.exception("Document answer generation failed.")
        raise HTTPException(
            status_code=500,
            detail="No se ha podido generar una respuesta válida.",
        ) from error