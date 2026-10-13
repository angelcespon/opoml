# OpoML

A platform for exam preparation, designed to guide study through student performance analysis. Planned capabilities include AI-powered queries over study materials and Machine Learning to personalize practice.

## Planned development

- **V0:** backend, database, automated tests, and performance tracking.
- **V1:** RAG-based queries over study materials with source citations.
- **V2:** evaluation of retrieval, answers, and citations.
- **V3:** ML-based personalization.

## Current status

The API provides a basic `GET /` endpoint, covered by an automated test.
Database integration and the remaining features are not implemented yet.

## Local setup

Requires Python 3.12. Run these commands from the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## Run the API

```bash
python -m uvicorn app.main:app --reload
```

- API: http://127.0.0.1:8000/
- Interactive documentation: http://127.0.0.1:8000/docs

## Run tests

```bash
python -m pytest -v
```
