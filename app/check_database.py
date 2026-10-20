# check_database.py

from sqlalchemy import text
from app.database import engine

def main():
    with engine.connect() as connection:
        result = connection.execute(
            text(
                "SELECT id, name, description "
                "FROM public.topics "
                "ORDER BY id"
            )
        )

        for topic in result.mappings():
            print(dict(topic))

if __name__ == "__main__":
    main()