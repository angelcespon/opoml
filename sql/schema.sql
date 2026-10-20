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