# OpoML

A platform for exam preparation, designed to guide study through student performance analysis. Planned capabilities include AI-powered queries over study materials and Machine Learning to personalize practice.

## Planned development

- **V0:** backend, database, automated tests, and performance tracking.
- **V1:** RAG-based queries over study materials with source citations.
- **V2:** evaluation of retrieval, answers, and citations.
- **V3:** ML-based personalization.

## Current status

The API supports topic management, question creation and retrieval,
practice submission, stored attempt summaries, and cumulative performance
by topic.

Questions support three to five options with exactly one correct answer.
Practice submissions record correct, incorrect, and unanswered questions.

Data is stored in PostgreSQL hosted on Supabase. Automated tests cover
input validation and endpoint behavior with mocked database access.

Detailed attempt review and PostgreSQL integration tests are pending.
The current version is intended for a single student without authentication.

## Local setup

Requires Python 3.12 and a Supabase project with a PostgreSQL database.

Run these commands from the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Copy the environment configuration template:

```bash
cp .env.example .env
```

Fill in `.env` with your Supabase PostgreSQL **Session pooler** connection parameters and database password:

```dotenv
DB_HOST=your-session-pooler-host
DB_PORT=5432
DB_NAME=postgres
DB_USER=your-database-user
DB_PASSWORD='your-database-password'
```

The database password is the one configured for your Supabase project, not your Supabase account password.

Never commit `.env` or share its credentials.

Before running the topic endpoints, open the Supabase SQL Editor and execute the contents of `sql/schema.sql` once, in a database where `public.topics`does not already exist.

## Run the API

```bash
python -m uvicorn app.main:app --reload
```

- API: http://127.0.0.1:8000/
- Interactive documentation: http://127.0.0.1:8000/docs

### Available endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/` | Return basic service information. |
| GET | `/topics` | List stored topics. |
| GET | `/topics/{topic_id}` | Retrieve a topic by its identifier. |
| GET | `/questions/{question_id}` | Retrieve a question without revealing its solution. |
| GET | `/attempts/{attempt_id}` | Retrieve a stored attempt summary. |
| GET | `/topics/{topic_id}/performance` | Retrieve cumulative performance for a topic. |
| POST | `/topics/validate` | Validate and normalize topic data without saving it. |
| POST | `/topics` | Create and store a topic. |
| POST | `/questions` | Create a question with its answer options. |
| POST | `/attempts` | Submit a practice attempt and store its results. |


## Run tests

```bash
python -m pytest tests/ -v
```

Tests require the environment variables above to be configured, but do not connect to Supabase. They do not verify SQL execution or database constraints.