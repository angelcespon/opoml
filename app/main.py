# main.py
from fastapi import FastAPI

app = FastAPI(title="OpoML")


@app.get("/")
def root():
    return {"status": "ok", "service": "OpoML"}