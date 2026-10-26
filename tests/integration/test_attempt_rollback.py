import importlib

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event, text


main_module = importlib.import_module("app.main")


def test_failed_answer_insert_rolls_back_attempt(
    database_engine,
    monkeypatch,
):
    monkeypatch.setattr(main_module, "engine", database_engine)

    topic_id = None
    question_id = None
    created_attempt_id = None
    failure_triggered = False

    def fail_before_answer_insert(
        connection,
        cursor,
        statement,
        parameters,
        context,
        executemany,
    ):
        nonlocal created_attempt_id, failure_triggered

        normalized_statement = " ".join(statement.lower().split())

        if normalized_statement.startswith(
            "insert into public.attempt_answers"
        ):
            # La práctica ya se ha insertado en esta transacción.
            created_attempt_id = connection.execute(
                text(
                    """
                    SELECT currval(
                        pg_get_serial_sequence(
                            'public.practice_attempts',
                            'id'
                        )
                    )
                    """
                )
            ).scalar_one()

            failure_triggered = True
            raise RuntimeError("Fallo simulado al guardar respuestas")

    try:
        with TestClient(main_module.app) as client:
            # Preparar un tema y una pregunta reales.
            response = client.post(
                "/topics",
                json={"name": "Tema para comprobar rollback"},
            )
            assert response.status_code == 201
            topic_id = response.json()["id"]

            response = client.post(
                "/questions",
                json={
                    "topic_id": topic_id,
                    "statement": "¿Cuánto es 2 + 2?",
                    "options": [
                        {"content": "3", "is_correct": False},
                        {"content": "4", "is_correct": True},
                        {"content": "5", "is_correct": False},
                    ],
                },
            )
            assert response.status_code == 201

            question = response.json()
            question_id = question["id"]

            correct_option_id = next(
                option["id"]
                for option in question["options"]
                if option["is_correct"]
            )

            # Activar el fallo solo durante la entrega.
            event.listen(
                database_engine,
                "before_cursor_execute",
                fail_before_answer_insert,
            )

            try:
                with pytest.raises(
                    RuntimeError,
                    match="Fallo simulado al guardar respuestas",
                ):
                    client.post(
                        "/attempts",
                        json={
                            "answers": [
                                {
                                    "question_id": question_id,
                                    "selected_option_id": correct_option_id,
                                }
                            ]
                        },
                    )
            finally:
                event.remove(
                    database_engine,
                    "before_cursor_execute",
                    fail_before_answer_insert,
                )

        assert failure_triggered is True
        assert created_attempt_id is not None

        # Consultar después del fallo, desde otra conexión.
        with database_engine.connect() as connection:
            stored_attempt_count = connection.execute(
                text(
                    """
                    SELECT COUNT(*)
                    FROM public.practice_attempts
                    WHERE id = :attempt_id
                    """
                ),
                {"attempt_id": created_attempt_id},
            ).scalar_one()

            stored_answer_count = connection.execute(
                text(
                    """
                    SELECT COUNT(*)
                    FROM public.attempt_answers
                    WHERE attempt_id = :attempt_id
                    """
                ),
                {"attempt_id": created_attempt_id},
            ).scalar_one()

        assert stored_attempt_count == 0
        assert stored_answer_count == 0

    finally:
        # Limpiar también si la prueba detecta un fallo.
        with database_engine.begin() as connection:
            if created_attempt_id is not None:
                connection.execute(
                    text(
                        """
                        DELETE FROM public.attempt_answers
                        WHERE attempt_id = :attempt_id
                        """
                    ),
                    {"attempt_id": created_attempt_id},
                )

                connection.execute(
                    text(
                        """
                        DELETE FROM public.practice_attempts
                        WHERE id = :attempt_id
                        """
                    ),
                    {"attempt_id": created_attempt_id},
                )

            if question_id is not None:
                connection.execute(
                    text(
                        """
                        DELETE FROM public.question_options
                        WHERE question_id = :question_id
                        """
                    ),
                    {"question_id": question_id},
                )

                connection.execute(
                    text(
                        """
                        DELETE FROM public.questions
                        WHERE id = :question_id
                        """
                    ),
                    {"question_id": question_id},
                )

            if topic_id is not None:
                connection.execute(
                    text(
                        """
                        DELETE FROM public.topics
                        WHERE id = :topic_id
                        """
                    ),
                    {"topic_id": topic_id},
                )