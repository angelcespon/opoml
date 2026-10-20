from fastapi.testclient import TestClient
from app.main import app
from unittest.mock import patch

def test_root():
    with TestClient(app) as client:
        response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "OpoML",
    }

def test_validate_topic_normalizes_name():
    with TestClient(app) as client:
        response = client.post(
            "/topics/validate",
            json={"name": " Constitución "},
        )

    assert response.status_code == 200
    assert response.json() == {
        "name": "Constitución",
        "description": None
    }

def test_validate_topic_rejects_blank_name():
    with TestClient(app) as client:
        response = client.post(
            "/topics/validate",
            json={"name": " "},
        )

    assert response.status_code == 422
    assert response.json()["detail"]

def test_validate_topic_rejects_extra_field():
    with TestClient(app) as client:
        response = client.post(
            "/topics/validate",
            json={"name": " Constitución ", "difficulty": 3},
        )

    assert response.status_code == 422
    assert response.json()["detail"]

def test_list_topics_returns_topics():
    expected_topics = [
        {
            "id": 1,
            "name": "Constitución",
            "description": "Principios generales.",
        },
        {
            "id": 2,
            "name": "Derecho penal",
            "description": None,
        },
    ]

    with patch("app.main.engine.connect") as mock_connect:
        connection = mock_connect.return_value.__enter__.return_value
        result = connection.execute.return_value
        result.mappings.return_value = expected_topics

        with TestClient(app) as client:
            response = client.get("/topics")

    assert response.status_code == 200
    assert response.json() == expected_topics


def test_list_topics_returns_empty_list():
    with patch("app.main.engine.connect") as mock_connect:
        connection = mock_connect.return_value.__enter__.return_value
        result = connection.execute.return_value
        result.mappings.return_value = []

        with TestClient(app) as client:
            response = client.get("/topics")

    assert response.status_code == 200
    assert response.json() == []

def test_create_topic_normalizes_name():
    expected_topic = {
        "id": 10,
        "name": "Constitución",
        "description": None,
    }

    with patch("app.main.engine.begin") as mock_begin:
        connection = mock_begin.return_value.__enter__.return_value
        result = connection.execute.return_value
        result.mappings.return_value.one.return_value = expected_topic

        with TestClient(app) as client:
            response = client.post(
                "/topics",
                json={"name": " Constitución "},
            )

    assert response.status_code == 201
    assert response.json() == expected_topic

    connection.execute.assert_called_once()
    assert connection.execute.call_args.args[1] == {
        "name": "Constitución",
        "description": None,
    }


def test_create_topic_rejects_blank_name():
    with patch("app.main.engine.begin") as mock_begin:
        with TestClient(app) as client:
            response = client.post(
                "/topics",
                json={"name": " "},
            )

    assert response.status_code == 422
    mock_begin.assert_not_called()


def test_create_topic_rejects_extra_field():
    with patch("app.main.engine.begin") as mock_begin:
        with TestClient(app) as client:
            response = client.post(
                "/topics",
                json={
                    "name": "Constitución",
                    "difficulty": 3,
                },
            )

    assert response.status_code == 422
    mock_begin.assert_not_called()