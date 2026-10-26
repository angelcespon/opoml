# OpoML

A platform for competitive exam preparation, designed to guide study through student performance analysis. Planned capabilities include AI-powered queries over study materials, question generation, and Machine Learning to personalize practice.

## Roadmap

- **V0:** backend, PostgreSQL database, automated tests, and performance tracking.
- **V1:** RAG-based queries and question generation from study materials, with source citations.
- **V2:** web interface and user pilot.
- **V3:** evaluation of retrieval, answers, citations, and generated questions.
- **V4:** ML-based personalization.

## Current status

The V0 backend supports:

- Topic creation and retrieval.
- Questions with three to five options and exactly one correct answer.
- Practice submission with correct, incorrect, and unanswered responses.
- Stored attempt summaries and detailed answer review.
- Cumulative performance by topic.

Application data is stored in PostgreSQL hosted on Supabase.

The test suite includes validation tests, endpoint tests with mocked database access, and integration tests against a separate local PostgreSQL database. Integration tests cover schema availability, the complete practice flow, and transaction rollback when saving answers fails.

## Current limitations

- Intended for a single student; authentication and a web interface are not implemented.
- AI features and ML personalization are planned.
- Accuracy is the percentage of correct answers out of all submitted questions, including unanswered ones. It is not an exam-specific score with penalties.
- Attempt summaries and answer correctness are stored at submission time. Review text and correct-option details are retrieved from the current question data. Historical content versioning is not implemented.
- Question editing and deletion are not exposed by the API.

## Local setup

Requires Python 3.12 and a Supabase PostgreSQL database. The commands below target Ubuntu or WSL.

Run from the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Copy the application configuration template:

```bash
cp .env.example .env
```

Fill in `.env` with your Supabase PostgreSQL **Session pooler** connection parameters:

```dotenv
DB_HOST=your-session-pooler-host
DB_PORT=5432
DB_NAME=postgres
DB_USER=your-database-user
DB_PASSWORD='your-database-password'
```

Use the database password configured for the Supabase project, not your Supabase account password.

In the Supabase SQL Editor, execute `sql/schema.sql` once against a database where the application tables do not already exist. This file creates the schema; it is not a migration script for an existing installation.

Do not commit `.env` or `.env.test`. The corresponding `.example` files contain placeholders only.

## Run the API

With the virtual environment active:

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
| GET | `/topics/{topic_id}` | Retrieve a topic. |
| GET | `/questions/{question_id}` | Retrieve a question without its solution. |
| GET | `/attempts/{attempt_id}` | Retrieve a stored attempt summary. |
| GET | `/attempts/{attempt_id}/review` | Retrieve the summary, submitted answers, solutions, and explanations. |
| GET | `/topics/{topic_id}/performance` | Retrieve cumulative performance for a topic. |
| POST | `/topics/validate` | Validate and normalize topic data without saving it. |
| POST | `/topics` | Create a topic. |
| POST | `/questions` | Create a question and its options. |
| POST | `/attempts` | Submit a practice attempt and store its results. |

## Run tests

### Tests without a database connection

```bash
python -m pytest tests/ --ignore=tests/integration/ -v
```

Application configuration in `.env` is required because the application engine is constructed during import. These tests mock database access and do not connect to Supabase.

### Set up the integration test database

Integration tests use a separate local PostgreSQL database named `opoml_test`.

On Ubuntu or WSL, install PostgreSQL if necessary:

```bash
sudo apt update
sudo apt install postgresql
```

Check that the local PostgreSQL cluster is running:

```bash
pg_lsclusters
```

Open the PostgreSQL administration console:

```bash
sudo -u postgres psql
```

Create a dedicated role and database once:

```sql
CREATE ROLE opoml_test_user LOGIN;
\password opoml_test_user
CREATE DATABASE opoml_test OWNER opoml_test_user;
\q
```

The `\password` command prompts for a password without placing it directly in a SQL statement.

Load the schema into the empty test database:

```bash
psql -h 127.0.0.1 -p 5432 -U opoml_test_user -d opoml_test -W -v ON_ERROR_STOP=1 --single-transaction -f sql/schema.sql
```

Copy the test configuration template:

```bash
cp .env.test.example .env.test
```

Fill in the local test credentials:

```dotenv
TEST_DB_HOST=127.0.0.1
TEST_DB_PORT=5432
TEST_DB_NAME=opoml_test
TEST_DB_USER=opoml_test_user
TEST_DB_PASSWORD='your-local-test-password'
```

Integration tests require the application configuration in `.env` as well. During API integration tests, the application engine is temporarily replaced with the local test engine.

Run integration tests:

```bash
python -m pytest tests/integration/ -v
```

These tests execute real SQL. The practice-flow and rollback tests create their own data and include cleanup.

### Run the complete suite

With both configuration files prepared and local PostgreSQL running:

```bash
python -m pytest tests/ -v
```

Uvicorn does not need to be running: endpoint tests use FastAPI's `TestClient`.