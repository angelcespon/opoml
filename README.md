# OpoML

OpoML is a backend for competitive exam preparation. Students can ask questions about their study materials, generate multiple-choice questions, submit practice attempts, and review their results with explanations and source references.

The project uses Python, FastAPI, PostgreSQL, pgvector, and the OpenAI API.

## Roadmap

- **V0:** backend, database, automated tests, and performance tracking.
- **V1:** document-based answers and question generation with source references.
- **V2:** web interface and user pilot.
- **V3:** systematic evaluation of retrieval, answers, citations, and generated questions.
- **V4:** ML-based personalization.

## Current features

### Practice and performance

- Create and retrieve topics.
- Create questions with three to five options and one correct answer.
- Retrieve questions without revealing their solutions.
- Submit practice attempts, including unanswered questions.
- Review results, explanations, and available document references.
- Track cumulative performance by topic.

### Study materials and AI

- Extract text from PDFs while retaining page references.
- Split text into overlapping chunks and generate embeddings.
- Store documents, chunks, and embeddings in PostgreSQL.
- Answer questions using semantic retrieval and source citations.
- Generate question batches and review them with a separate model call.
- Generate sets of up to 100 questions through the CLI, subject to available content and a batch limit.
- Import accepted questions into a topic and retain their source references.
- Prevent repeated imports of the same batch.

The API supports generation of up to five questions per request. Larger sets currently use the CLI.

## Limitations

- The application is intended for a single student. Authentication and a web interface are not implemented.
- PDF ingestion currently uses command-line scripts. OCR and reliable extraction from complex layouts are not implemented.
- Document queries use semantic search. Hybrid search and conversation history are not implemented.
- Generated content can contain mistakes. Automated review checks questions and options against the sources but does not currently review explanations.
- A generation request may return fewer questions than requested. Rejected questions are not automatically repaired.
- Multi-batch generation runs sequentially. Progress is printed in the terminal; background jobs and automatic resume are not implemented.
- Duplicate detection within a generated set compares normalized statements. It does not detect paraphrases.
- Import protection identifies repeated batch content, not semantically equivalent questions. Reordering questions or options can change the batch fingerprint.
- Repeating a generation request can incur additional API charges and produce another batch.
- Accuracy is the percentage of correct answers out of all submitted questions, including unanswered ones. Exam-specific penalties are not applied.
- Attempt summaries and answer correctness are stored at submission time. Review text, solution details, and source content are read from the current database records. Historical content versioning is not implemented.
- Question editing and deletion are not exposed by the API.

Source citations identify the material used to generate an answer. They do not establish that the material is accurate or up to date.

## Local setup

The commands below target Ubuntu or WSL and require Python 3.12.

From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

### Application configuration

Copy the template:

```bash
cp .env.example .env
```

Configure your Supabase PostgreSQL Session pooler connection and OpenAI credentials:

```dotenv
DB_HOST=your-session-pooler-host
DB_PORT=5432
DB_NAME=postgres
DB_USER=your-database-user
DB_PASSWORD='your-database-password'

OPENAI_API_KEY=your-openai-api-key
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
OPENAI_GENERATION_MODEL=your-generation-model
OPENAI_REVIEW_MODEL=your-review-model
```

Use the database password configured for the Supabase project, not your Supabase account password.

`OPENAI_REVIEW_MODEL` is optional. If omitted, the reviewer uses `OPENAI_GENERATION_MODEL`.

Choose models compatible with the structured-output and reasoning settings used by the scripts. The current database schema stores embeddings with 1536 dimensions.

AI operations incur OpenAI API usage charges.

Do not commit `.env`, `.env.test`, or files under `data/`. Configuration templates must contain placeholders only.

### Application database

For a new installation, execute these files in order in the Supabase SQL Editor:

1. `sql/schema.sql`
2. `sql/rag_schema.sql`

The second file enables pgvector and creates the document, source-reference, and import-tracking tables.

These files initialize an empty application schema. They are not migration scripts and should not be rerun in full against an existing installation.

## Run the API

With the virtual environment active:

```bash
python -m uvicorn app.main:app --reload
```

- API: http://127.0.0.1:8000/
- Interactive documentation: http://127.0.0.1:8000/docs

### Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/` | Return service information. |
| GET | `/topics` | List topics. |
| GET | `/topics/{topic_id}` | Retrieve a topic. |
| GET | `/questions/{question_id}` | Retrieve a question without its solution. |
| GET | `/attempts/{attempt_id}` | Retrieve a stored attempt summary. |
| GET | `/attempts/{attempt_id}/review` | Retrieve answers, solutions, explanations, and source references. |
| GET | `/topics/{topic_id}/performance` | Retrieve cumulative performance for a topic. |
| POST | `/topics/validate` | Validate topic data without saving it. |
| POST | `/topics` | Create a topic. |
| POST | `/questions` | Create a question and its options. |
| POST | `/attempts` | Submit and score a practice attempt. |
| POST | `/documents/{document_id}/ask` | Answer a question using document sources. |
| POST | `/documents/{document_id}/generate-questions` | Generate, review, and save up to five questions. |

For example, the generation endpoint accepts:

```json
{
  "topic_id": 2,
  "question_count": 3,
  "option_count": 3
}
```

Use an existing topic identifier. The response includes the number of accepted and inserted questions and their database identifiers.

When submitting an attempt, `selected_option_id` must be the option's database identifier returned by the question endpoint, not its display position.

## Import a study document

Place a text-based PDF in `data/documents/`. The example below uses `study_material.pdf`; replace it with your filename.

Run each step separately:

```bash
python -m app.extract_document "data/documents/study_material.pdf"
python -m app.chunk_document "data/extracted/study_material.json"
python -m app.embed_document "data/chunks/study_material.json"
python -m app.import_document \
  "data/documents/study_material.pdf" \
  "data/embeddings/study_material.json"
```

Inspect the extracted text before generating embeddings. A successful extraction does not guarantee correct reading order or complete text.

The import command prints the document identifier used by subsequent commands and API requests. Embedding generation calls OpenAI; importing saved embeddings does not.

## Ask a document

Replace `1` with an imported document identifier:

```bash
python -m app.ask_document 1 \
  --query "¿Qué derechos reconoce el documento a las víctimas?"
```

The result includes the answer, cited sources, page references, and token usage.

## Generate and import questions

### Generate a reviewed batch

```bash
python -m app.generate_reviewed_questions 1 \
  --question-count 3 \
  --option-count 3
```

The command saves the context, generated batch, review, and final result under a separate directory in `data/generation_runs/`.

### Generate a larger set

```bash
python -m app.generate_question_set 1 \
  --question-count 6 \
  --option-count 3 \
  --max-batches 3
```

Each generation call requests at most five questions. Accepted questions accumulate until the requested count is reached or the available contexts or batch budget are exhausted.

Without `--max-batches`, the limit is `ceil(question_count / 5) + 2`.

Results are saved under `data/question_sets/`. A `partial` result means the requested count was not reached within the available budget and contexts. It can still contain usable questions.

These commands generate and review questions but do not save them to the question tables.

### Import accepted questions

Replace the path and topic identifier with your own:

```bash
python -m app.import_questions \
  data/question_sets/RUN_ID/result.json \
  --topic-id 2
```

The importer saves questions, options, source references, and the import record in one transaction. If a write fails, the transaction is rolled back.

Importing the same batch again returns `already_imported`. The importer is intended for trusted local output files; it does not independently prove that their contents passed automated review.

## Tests

### Tests without external service calls

```bash
python -m pytest tests/ --ignore=tests/integration/ -v
```

These tests use simulated database and AI responses. They check validation, endpoint behavior, and multi-batch coordination without calling OpenAI or connecting to Supabase.

Application database configuration in `.env` is still required because the application engine is constructed during import.

### Local integration database

Integration tests use a separate PostgreSQL database named `opoml_test` on `127.0.0.1`.

For PostgreSQL 16 on Ubuntu or WSL:

```bash
sudo apt update
sudo apt install postgresql-16 postgresql-16-pgvector
pg_lsclusters
```

The cluster must be running. If using another PostgreSQL major version, install its matching pgvector package.

Open the administration console:

```bash
sudo -u postgres psql
```

Create the role and database once:

```sql
CREATE ROLE opoml_test_user LOGIN;
\password opoml_test_user
CREATE DATABASE opoml_test OWNER opoml_test_user;
\q
```

Enable pgvector in the test database:

```bash
sudo -u postgres psql -p 5432 -d opoml_test -v ON_ERROR_STOP=1 -c "
CREATE SCHEMA IF NOT EXISTS extensions AUTHORIZATION opoml_test_user;
CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA extensions;
GRANT USAGE ON SCHEMA extensions TO opoml_test_user;
"
```

Load both schemas into the fresh test database:

```bash
psql -h 127.0.0.1 -p 5432 \
  -U opoml_test_user -d opoml_test \
  -W -v ON_ERROR_STOP=1 --single-transaction \
  -f sql/schema.sql

psql -h 127.0.0.1 -p 5432 \
  -U opoml_test_user -d opoml_test \
  -W -v ON_ERROR_STOP=1 \
  -f sql/rag_schema.sql
```

Copy the test configuration template:

```bash
cp .env.test.example .env.test
```

Set the local credentials:

```dotenv
TEST_DB_HOST=127.0.0.1
TEST_DB_PORT=5432
TEST_DB_NAME=opoml_test
TEST_DB_USER=opoml_test_user
TEST_DB_PASSWORD='your-local-test-password'
```

Integration tests also require the application configuration in `.env`. Database access is redirected to the local test engine.

Run them with:

```bash
python -m pytest tests/integration/ -v
```

They execute real SQL and cover the practice flow, question imports, duplicate-import protection, source references, and transaction rollback. Test data is cleaned up or rolled back.

### Complete test suite

With both configuration files prepared and local PostgreSQL running:

```bash
python -m pytest tests/ -v
```

Uvicorn does not need to be running. Endpoint tests use FastAPI's `TestClient`.

Passing tests verify the covered software behavior; they do not establish the factual quality of generated content.