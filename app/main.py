# main.py

from fastapi import FastAPI, HTTPException, Path
from sqlalchemy import text
from typing import Annotated

from app.database import engine
from app.schemas import TopicCreate, TopicRead

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