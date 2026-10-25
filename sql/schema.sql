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