# main.py

from fastapi import FastAPI, HTTPException, Path
from sqlalchemy import text
from typing import Annotated

from app.database import engine
from app.schemas import (
    QuestionCreate,
    QuestionCreated,
    QuestionRead,
    TopicCreate,
    TopicRead
)
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