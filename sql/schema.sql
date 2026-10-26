CREATE TABLE public.topics (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    name TEXT NOT NULL
        CONSTRAINT topics_name_check CHECK (
            char_length(btrim(name)) >= 1
            AND char_length(name) <= 100
        ),

    description TEXT
        CONSTRAINT topics_description_check CHECK (
            char_length(description) <= 500
        )
);

CREATE TABLE public.questions (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    topic_id INTEGER NOT NULL
        CONSTRAINT questions_topic_id_fkey
        REFERENCES public.topics (id),

    statement TEXT NOT NULL
        CONSTRAINT questions_statement_check CHECK (
            char_length(btrim(statement)) >= 1
            AND char_length(statement) <= 5000
        ),

    explanation TEXT
        CONSTRAINT questions_explanation_check CHECK (
            char_length(explanation) <= 10000
        )
);

CREATE TABLE public.question_options (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    question_id INTEGER NOT NULL
        CONSTRAINT question_options_question_id_fkey
        REFERENCES public.questions (id),

    position SMALLINT NOT NULL
        CONSTRAINT question_options_position_check CHECK (
            position > 0
        ),

    content TEXT NOT NULL
        CONSTRAINT question_options_content_check CHECK (
            char_length(btrim(content)) >= 1
            AND char_length(content) <= 2000
        ),

    is_correct BOOLEAN NOT NULL DEFAULT FALSE,

    CONSTRAINT question_options_question_position_key
        UNIQUE (question_id, position)
);

CREATE UNIQUE INDEX question_options_one_correct_idx
    ON public.question_options (question_id)
    WHERE is_correct = TRUE;

CREATE TABLE public.practice_attempts (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    submitted_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    total_questions INTEGER NOT NULL,
    correct_answers INTEGER NOT NULL,
    incorrect_answers INTEGER NOT NULL,
    unanswered_questions INTEGER NOT NULL,
    accuracy_percentage NUMERIC(5, 2) NOT NULL,

    CONSTRAINT practice_attempts_counts_check CHECK (
        total_questions > 0
        AND correct_answers >= 0
        AND incorrect_answers >= 0
        AND unanswered_questions >= 0
        AND total_questions = (
            correct_answers
            + incorrect_answers
            + unanswered_questions
        )
    ),

    CONSTRAINT practice_attempts_accuracy_check CHECK (
        accuracy_percentage BETWEEN 0 AND 100
    )
);

CREATE TABLE public.attempt_answers (
    attempt_id INTEGER NOT NULL
        REFERENCES public.practice_attempts (id),

    question_id INTEGER NOT NULL
        REFERENCES public.questions (id),

    selected_option_id INTEGER
        REFERENCES public.question_options (id),

    is_correct BOOLEAN NOT NULL,

    CONSTRAINT attempt_answers_pkey
        PRIMARY KEY (attempt_id, question_id),

    CONSTRAINT attempt_answers_unanswered_check CHECK (
        selected_option_id IS NOT NULL
        OR is_correct = FALSE
    )
);