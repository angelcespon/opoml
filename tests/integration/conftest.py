from pathlib import Path

import pytest
from dotenv import dotenv_values
from sqlalchemy import URL, create_engine


PROJECT_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def database_engine():
    config = dotenv_values(PROJECT_ROOT / ".env.test")

    required_variables = (
        "TEST_DB_HOST",
        "TEST_DB_PORT",
        "TEST_DB_NAME",
        "TEST_DB_USER",
        "TEST_DB_PASSWORD",
    )

    missing_variables = [
        name
        for name in required_variables
        if not config.get(name)
    ]

    if missing_variables:
        pytest.fail(
            "Faltan variables en .env.test: "
            + ", ".join(missing_variables)
        )

    if (
        config["TEST_DB_HOST"] != "127.0.0.1"
        or config["TEST_DB_NAME"] != "opoml_test"
    ):
        pytest.fail(
            "Los tests de integración deben utilizar "
            "la base local opoml_test."
        )

    database_url = URL.create(
        drivername="postgresql+psycopg",
        username=config["TEST_DB_USER"],
        password=config["TEST_DB_PASSWORD"],
        host=config["TEST_DB_HOST"],
        port=int(config["TEST_DB_PORT"]),
        database=config["TEST_DB_NAME"],
    )

    engine = create_engine(
        database_url,
        connect_args={"connect_timeout": 5},
    )

    try:
        yield engine
    finally:
        engine.dispose()