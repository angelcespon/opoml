from sqlalchemy import text


def test_database_has_expected_tables(database_engine):
    with database_engine.connect() as connection:
        database_name = connection.execute(
            text("SELECT current_database()")
        ).scalar_one()

        tables = connection.execute(
            text(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_type = 'BASE TABLE'
                """
            )
        ).scalars().all()

    assert database_name == "opoml_test"

    expected_tables = {
        "topics",
        "questions",
        "question_options",
        "practice_attempts",
        "attempt_answers",
    }

    assert expected_tables.issubset(set(tables))