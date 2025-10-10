import pytest
from flask_jwt_extended import create_access_token

from app import create_app
from app.controllers import quiz_controller


@pytest.fixture
def app():
    app = create_app()
    app.config.update(
        {
            "TESTING": True,
            "JWT_SECRET_KEY": "test-jwt-key",
        }
    )
    return app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def auth_headers(app):
    with app.app_context():
        token = create_access_token(identity="user-123")
    return {"Authorization": f"Bearer {token}"}


def test_get_quiz_status_success(client, auth_headers, monkeypatch):
    expected_status = {
        "has_taken_quiz": True,
        "quiz_count": 3,
        "latest_quiz_date": "2024-05-17T12:00:00",
        "available_questions": 10,
    }

    monkeypatch.setattr(
        quiz_controller.QuizService,
        "get_user_quiz_status",
        staticmethod(lambda user_id: (expected_status, None)),
    )

    response = client.get("/api/quiz/status", headers=auth_headers)

    assert response.status_code == 200
    assert response.get_json() == expected_status


def test_get_quiz_status_not_found(client, auth_headers, monkeypatch):
    monkeypatch.setattr(
        quiz_controller.QuizService,
        "get_user_quiz_status",
        staticmethod(lambda user_id: (None, "No quiz data")),
    )

    response = client.get("/api/quiz/status", headers=auth_headers)

    assert response.status_code == 404
    assert response.get_json() == {"message": "No quiz data"}


def test_get_quiz_questions_success(client, auth_headers, monkeypatch):
    expected_questions = {
        "questions": [{"id": 1, "question": "Q1", "type": "text"}],
        "total_questions": 1,
    }

    monkeypatch.setattr(
        quiz_controller.QuizService,
        "get_quiz_questions",
        staticmethod(lambda user_id: (expected_questions, None)),
    )

    response = client.get("/api/quiz/questions", headers=auth_headers)

    assert response.status_code == 200
    assert response.get_json() == expected_questions


def test_get_quiz_questions_error(client, auth_headers, monkeypatch):
    monkeypatch.setattr(
        quiz_controller.QuizService,
        "get_quiz_questions",
        staticmethod(lambda user_id: (None, "Failed to fetch questions")),
    )

    response = client.get("/api/quiz/questions", headers=auth_headers)

    assert response.status_code == 404
    assert response.get_json() == {"message": "Failed to fetch questions"}


def test_submit_quiz_success(client, auth_headers, monkeypatch):
    payload = [{"question_id": 1, "answer": "Yes"}]
    expected_result = {
        "message": "Quiz submitted successfully",
        "quiz_id": "abc123",
        "score": 1,
        "total_questions": 10,
    }

    def mock_submit(user_id, answers):
        assert answers == payload
        return expected_result, None

    monkeypatch.setattr(
        quiz_controller.QuizService,
        "submit_quiz_answers",
        staticmethod(mock_submit),
    )

    response = client.post(
        "/api/quiz/submit", headers=auth_headers, json={"answers": payload}
    )

    assert response.status_code == 200
    assert response.get_json() == expected_result


def test_submit_quiz_missing_answers(client, auth_headers):
    response = client.post("/api/quiz/submit", headers=auth_headers, json={})

    assert response.status_code == 400
    assert response.get_json() == {"message": "Answers are required"}


def test_submit_quiz_service_error(client, auth_headers, monkeypatch):
    monkeypatch.setattr(
        quiz_controller.QuizService,
        "submit_quiz_answers",
        staticmethod(lambda user_id, answers: (None, "Bad data")),
    )

    response = client.post(
        "/api/quiz/submit",
        headers=auth_headers,
        json={"answers": [{"question_id": 1, "answer": "Yes"}]},
    )

    assert response.status_code == 400
    assert response.get_json() == {"message": "Bad data"}
