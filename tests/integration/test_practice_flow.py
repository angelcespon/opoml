import importlib

from fastapi.testclient import TestClient
from sqlalchemy import text


main_module = importlib.import_module("app.main")


def test_complete_practice_flow(database_engine, monkeypatch):
    # Durante este test, la API utiliza PostgreSQL local.
    monkeypatch.setattr(main_module, "engine", database_engine)

    topic_id = None
    attempt_id = None

    try:
        with TestClient(main_module.app) as client:
            # 1. Crear un tema.
            response = client.post(
                "/topics",
                json={"name": "Tema de prueba de integración"},
            )

            assert response.status_code == 201
            topic_id = response.json()["id"]

            # 2. Crear una pregunta con tres opciones.
            response = client.post(
                "/questions",
                json={
                    "topic_id": topic_id,
                    "statement": "¿Cuánto es 2 + 2?",
                    "explanation": "Dos más dos son cuatro.",
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

            correct_option = next(
                option
                for option in question["options"]
                if option["is_correct"]
            )

            # 3. Consultar la pregunta sin revelar la solución.
            response = client.get(f"/questions/{question_id}")

            assert response.status_code == 200
            public_question = response.json()

            assert "explanation" not in public_question
            assert len(public_question["options"]) == 3
            assert all(
                "is_correct" not in option
                for option in public_question["options"]
            )

            # 4. Entregar una práctica con una respuesta correcta.
            response = client.post(
                "/attempts",
                json={
                    "answers": [
                        {
                            "question_id": question_id,
                            "selected_option_id": correct_option["id"],
                        }
                    ]
                },
            )

            assert response.status_code == 201
            created_attempt = response.json()
            attempt_id = created_attempt["id"]

            assert created_attempt["total_questions"] == 1
            assert created_attempt["correct_answers"] == 1
            assert created_attempt["incorrect_answers"] == 0
            assert created_attempt["unanswered_questions"] == 0
            assert created_attempt["accuracy_percentage"] == 100.0

            # 5. Recuperar el resultado guardado.
            response = client.get(f"/attempts/{attempt_id}")

            assert response.status_code == 200
            assert response.json() == created_attempt

            # 6. Consultar la revisión de la práctica.
            response = client.get(f"/attempts/{attempt_id}/review")

            assert response.status_code == 200
            review = response.json()

            for field, value in created_attempt.items():
                assert review[field] == value

            assert review["answers"] == [
                {
                    "question_id": question_id,
                    "statement": "¿Cuánto es 2 + 2?",
                    "selected_option_id": correct_option["id"],
                    "selected_option_content": "4",
                    "is_correct": True,
                    "correct_option_id": correct_option["id"],
                    "correct_option_content": "4",
                    "explanation": "Dos más dos son cuatro.",
                    "sources": [],
                }
            ]

            # 7. Comprobar el rendimiento acumulado del tema.
            response = client.get(f"/topics/{topic_id}/performance")

            assert response.status_code == 200
            assert response.json() == {
                "topic_id": topic_id,
                "attempt_count": 1,
                "total_questions": 1,
                "correct_answers": 1,
                "incorrect_answers": 0,
                "unanswered_questions": 0,
                "accuracy_percentage": 100.0,
            }

    finally:
        # Eliminar los datos creados por esta prueba.
        with database_engine.begin() as connection:
            if attempt_id is not None:
                connection.execute(
                    text(
                        """
                        DELETE FROM public.attempt_answers
                        WHERE attempt_id = :attempt_id
                        """
                    ),
                    {"attempt_id": attempt_id},
                )

                connection.execute(
                    text(
                        """
                        DELETE FROM public.practice_attempts
                        WHERE id = :attempt_id
                        """
                    ),
                    {"attempt_id": attempt_id},
                )

            if topic_id is not None:
                connection.execute(
                    text(
                        """
                        DELETE FROM public.question_options
                        WHERE question_id IN (
                            SELECT id
                            FROM public.questions
                            WHERE topic_id = :topic_id
                        )
                        """
                    ),
                    {"topic_id": topic_id},
                )

                connection.execute(
                    text(
                        """
                        DELETE FROM public.questions
                        WHERE topic_id = :topic_id
                        """
                    ),
                    {"topic_id": topic_id},
                )

                connection.execute(
                    text(
                        """
                        DELETE FROM public.topics
                        WHERE id = :topic_id
                        """
                    ),
                    {"topic_id": topic_id},
                )