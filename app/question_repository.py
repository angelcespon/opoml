from sqlalchemy import text

from app.schemas import QuestionCreate


def insert_question(connection, question: QuestionCreate) -> dict:
    question_result = connection.execute(
        text(
            """
            INSERT INTO public.questions (
                topic_id, statement, explanation
            )
            VALUES (:topic_id, :statement, :explanation)
            RETURNING id, topic_id, statement, explanation
            """
        ),
        {
            "topic_id": question.topic_id,
            "statement": question.statement,
            "explanation": question.explanation,
        },
    )

    created_question = dict(question_result.mappings().one())
    created_options = []

    for position, option in enumerate(question.options, start=1):
        option_result = connection.execute(
            text(
                """
                INSERT INTO public.question_options (
                    question_id, position, content, is_correct
                )
                VALUES (
                    :question_id, :position, :content, :is_correct
                )
                RETURNING id, position, content, is_correct
                """
            ),
            {
                "question_id": created_question["id"],
                "position": position,
                "content": option.content,
                "is_correct": option.is_correct,
            },
        )

        created_options.append(
            dict(option_result.mappings().one())
        )

    created_question["options"] = created_options

    return created_question