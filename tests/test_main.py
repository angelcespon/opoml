from fastapi.testclient import TestClient
from app.main import app

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