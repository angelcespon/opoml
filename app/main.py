# main.py
from fastapi import FastAPI
from app.schemas import TopicCreate

# Crear aplicación web
app = FastAPI(title="OpoML")

# GET
@app.get("/")
def root():
    return {"status": "ok", "service": "OpoML"}

# POST
@app.post("/topics/validate")
def inspect_topic(topic: TopicCreate):
    return topic.model_dump()