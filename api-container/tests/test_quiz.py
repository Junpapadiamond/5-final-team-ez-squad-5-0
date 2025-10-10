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
        "total_sessions": 2,
        "completed_sessions": 1,
        "active_session_id": "session-123",
        "last_score": 90,
        "last_completed_at": "2024-06-01T12:00:00",
        "average_score": 85.5,
        "question_bank_size": 40,
        "default_batch_sizes": [10, 15, 20],
    }

    monkeypatch.setattr(
        quiz_controller.QuizService,
        "get_user_quiz_status",
        staticmethod(lambda user_id: (expected_status, None)),
    )

    response = client.get("/api/quiz/status", headers=auth_headers)

    assert response.status_code == 200
    assert response.get_json() == expected_status


def test_get_quiz_status_error(client, auth_headers, monkeypatch):
    monkeypatch.setattr(
        quiz_controller.QuizService,
        "get_user_quiz_status",
        staticmethod(lambda user_id: (None, "Unable to load status")),
    )

    response = client.get("/api/quiz/status", headers=auth_headers)

    assert response.status_code == 404
    assert response.get_json() == {"message": "Unable to load status"}


def test_get_question_bank_success(client, auth_headers, monkeypatch):
    expected_bank = {
        "questions": [{"id": 101, "question": "Coffee or tea?", "options": ["Coffee", "Tea"]}],
        "total_questions": 1,
        "default_batch_sizes": [10, 15, 20],
    }

    monkeypatch.setattr(
        quiz_controller.QuizService,
        "get_question_bank",
        staticmethod(lambda: (expected_bank, None)),
    )

    response = client.get("/api/quiz/questions", headers=auth_headers)

    assert response.status_code == 200
    assert response.get_json() == expected_bank


def test_get_question_bank_failure(client, auth_headers, monkeypatch):
    monkeypatch.setattr(
        quiz_controller.QuizService,
        "get_question_bank",
        staticmethod(lambda: (None, "Boom")),
    )

    response = client.get("/api/quiz/questions", headers=auth_headers)

    assert response.status_code == 400
    assert response.get_json() == {"message": "Boom"}


def test_start_session_created(client, auth_headers, monkeypatch):
    session_payload = {
        "id": "session-1",
        "status": "in_progress",
        "question_count": 10,
        "questions": [],
        "created": True,
    }

    monkeypatch.setattr(
        quiz_controller.QuizService,
        "start_session",
        staticmethod(lambda user_id, question_count=None, question_ids=None: (session_payload, None)),
    )

    response = client.post(
        "/api/quiz/session/start",
        headers=auth_headers,
        json={"question_count": 10},
    )

    assert response.status_code == 201
    assert response.get_json() == session_payload


def test_start_session_existing(client, auth_headers, monkeypatch):
    session_payload = {
        "id": "session-1",
        "status": "in_progress",
        "question_count": 10,
        "questions": [],
        "created": False,
    }

    monkeypatch.setattr(
        quiz_controller.QuizService,
        "start_session",
        staticmethod(lambda user_id, question_count=None, question_ids=None: (session_payload, None)),
    )

    response = client.post(
        "/api/quiz/session/start",
        headers=auth_headers,
        json={"question_count": 10},
    )

    assert response.status_code == 200
    assert response.get_json() == session_payload


def test_start_session_error(client, auth_headers, monkeypatch):
    monkeypatch.setattr(
        quiz_controller.QuizService,
        "start_session",
        staticmethod(lambda user_id, question_count=None, question_ids=None: (None, "No partner")),
    )

    response = client.post(
        "/api/quiz/session/start",
        headers=auth_headers,
        json={"question_count": 10},
    )

    assert response.status_code == 400
    assert response.get_json() == {"message": "No partner"}


def test_get_active_session_success(client, auth_headers, monkeypatch):
    payload = {"session": {"id": "session-1"}}

    monkeypatch.setattr(
        quiz_controller.QuizService,
        "get_active_session",
        staticmethod(lambda user_id: (payload, None)),
    )

    response = client.get("/api/quiz/session/current", headers=auth_headers)

    assert response.status_code == 200
    assert response.get_json() == payload


def test_get_active_session_error(client, auth_headers, monkeypatch):
    monkeypatch.setattr(
        quiz_controller.QuizService,
        "get_active_session",
        staticmethod(lambda user_id: (None, "Failure")),
    )

    response = client.get("/api/quiz/session/current", headers=auth_headers)

    assert response.status_code == 400
    assert response.get_json() == {"message": "Failure"}


def test_get_session_not_found(client, auth_headers, monkeypatch):
    monkeypatch.setattr(
        quiz_controller.QuizService,
        "get_session",
        staticmethod(lambda user_id, session_id: (None, "Session not found")),
    )

    response = client.get("/api/quiz/session/abc123", headers=auth_headers)

    assert response.status_code == 404
    assert response.get_json() == {"message": "Session not found"}


def test_submit_answer_success(client, auth_headers, monkeypatch):
    payload = {"session": {"id": "session-1"}}

    def mock_submit(user_id, session_id, question_id, answer):
        assert session_id == "session-1"
        assert question_id == 101
        assert answer == "Coffee"
        return payload, None

    monkeypatch.setattr(
        quiz_controller.QuizService,
        "submit_session_answer",
        staticmethod(mock_submit),
    )

    response = client.post(
        "/api/quiz/session/session-1/answer",
        headers=auth_headers,
        json={"question_id": 101, "answer": "Coffee"},
    )

    assert response.status_code == 200
    assert response.get_json() == payload


def test_submit_answer_missing_question(client, auth_headers):
    response = client.post(
        "/api/quiz/session/session-1/answer",
        headers=auth_headers,
        json={"answer": "Coffee"},
    )

    assert response.status_code == 400
    assert response.get_json() == {"message": "question_id is required"}


def test_submit_answer_error(client, auth_headers, monkeypatch):
    monkeypatch.setattr(
        quiz_controller.QuizService,
        "submit_session_answer",
        staticmethod(lambda user_id, session_id, question_id, answer: (None, "Bad answer")),
    )

    response = client.post(
        "/api/quiz/session/session-1/answer",
        headers=auth_headers,
        json={"question_id": 101, "answer": "Coffee"},
    )

    assert response.status_code == 400
    assert response.get_json() == {"message": "Bad answer"}
