import os
import sys
import json
import pytest
import requests
from unittest.mock import patch, MagicMock

pytest.skip("Legacy web container archived; tests are disabled.", allow_module_level=True)

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from flask import session
from app import app as flask_app


# Setup the test client
@pytest.fixture
def app():
    flask_app.config.update(
        {
            "TESTING": True,
            "SECRET_KEY": "test_secret_key",
            "SERVER_NAME": "localhost",
        }
    )
    return flask_app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def mock_api_response():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {}
    return mock_response


# Helper function to simulate login
def login(client, email="test@example.com", password="password123"):
    mock_user = {
        "_id": "user123",
        "name": "Test User",
        "email": email,
        "email_notifications": True,
    }

    with patch("app.api_request") as mock_api:
        mock_api.return_value.status_code = 200
        mock_api.return_value.json.return_value = {
            "token": "test_token",
            "user": mock_user,
        }
        return client.post(
            "/login", data={"email": email, "password": password}, follow_redirects=True
        )


# Tests for routes
def test_index_route_without_token(client):
    response = client.get("/")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_index_route_with_token(client):
    with client.session_transaction() as sess:
        sess["token"] = "test_token"
    response = client.get("/")
    assert response.status_code == 302
    assert "/dashboard" in response.headers["Location"]


def test_login_get(client):
    response = client.get("/login")
    assert response.status_code == 200
    assert b"<form" in response.data


def test_login_post_success(client):
    with patch("app.api_request") as mock_api:
        mock_api.return_value.status_code = 200
        mock_api.return_value.json.return_value = {
            "token": "test_token",
            "user": {"name": "Test User"},
        }
        response = client.post(
            "/login",
            data={"email": "test@example.com", "password": "password123"},
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b"Dashboard" in response.data


def test_login_post_failure(client):
    with patch("app.api_request") as mock_api:
        mock_api.return_value.status_code = 401
        mock_api.return_value.json.return_value = {"message": "Invalid credentials"}
        response = client.post(
            "/login", data={"email": "wrong@example.com", "password": "wrongpassword"}
        )
        assert response.status_code == 200
        assert b"Invalid email or password" in response.data


def test_login_post_exception(client):
    with patch("app.api_request") as mock_api:
        mock_api.side_effect = Exception("Connection error")
        response = client.post(
            "/login", data={"email": "test@example.com", "password": "password123"}
        )
        assert response.status_code == 200
        assert b"Error:" in response.data


def test_logout(client):
    with client.session_transaction() as sess:
        sess["token"] = "test_token"
        sess["user"] = {"name": "Test User"}

    response = client.get("/logout", follow_redirects=True)
    assert response.status_code == 200

    with client.session_transaction() as sess:
        assert "token" not in sess
        assert "user" not in sess


def test_register_get(client):
    response = client.get("/register")
    assert response.status_code == 200
    assert b"<form" in response.data


def test_register_post_success(client):
    with patch("app.api_request") as mock_api:
        mock_api.return_value.status_code = 201
        mock_api.return_value.json.return_value = {
            "message": "User registered successfully"
        }

        response = client.post(
            "/register",
            data={
                "name": "New User",
                "email": "new@example.com",
                "password": "password123",
            },
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert b"Registration successful" in response.data


def test_register_post_with_partner(client):
    with patch("app.api_request") as mock_api:
        mock_api.return_value.status_code = 201
        mock_api.return_value.json.return_value = {
            "message": "User registered successfully"
        }

        response = client.post(
            "/register",
            data={
                "name": "New User",
                "email": "new@example.com",
                "password": "password123",
                "partner_email": "partner@example.com",
            },
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert b"Registration successful" in response.data
        assert b"Invitation email" in response.data


def test_register_post_failure(client):
    with patch("app.api_request") as mock_api:
        mock_api.return_value.status_code = 400
        mock_api.return_value.json.return_value = {
            "message": "Email already registered"
        }

        response = client.post(
            "/register",
            data={
                "name": "New User",
                "email": "existing@example.com",
                "password": "password123",
            },
        )

        assert response.status_code == 200
        assert b"Email already registered" in response.data


def test_settings_get(client):
    login(client)
    response = client.get("/settings")
    assert response.status_code == 200
    assert b"settings" in response.data.lower()


def test_settings_post(client):
    login(client)

    with patch("app.api_request") as mock_api:
        mock_api.return_value.status_code = 200
        mock_api.return_value.json.return_value = {
            "message": "Settings updated successfully"
        }

        response = client.post(
            "/settings", data={"email_notifications": "on"}, follow_redirects=True
        )

        assert response.status_code == 200
        assert b"Settings updated successfully" in response.data


def test_dashboard(client):
    login(client)

    with patch("app.api_request") as mock_api:

        def side_effect(endpoint, *args, **kwargs):
            mock_response = MagicMock()

            if endpoint == "calendar/events":
                mock_response.status_code = 200
                mock_response.json.return_value = {
                    "events": [
                        {"title": "Test Event", "start_time": "2025-04-30T10:00:00"}
                    ]
                }
            elif endpoint == "messages/messages":
                mock_response.status_code = 200
                mock_response.json.return_value = {
                    "messages": [
                        {"content": "Test message", "created_at": "2025-04-25T15:30:00"}
                    ]
                }
            elif endpoint == "daily-question":
                mock_response.status_code = 200
                mock_response.json.return_value = {
                    "question": "What made you smile today?"
                }
            elif endpoint == "daily-question/answers":
                mock_response.status_code = 200
                mock_response.json.return_value = {
                    "answers": [{"user_name": "Partner", "answer": "Good coffee!"}]
                }
            else:
                mock_response.status_code = 404

            return mock_response

        mock_api.side_effect = side_effect

        response = client.get("/dashboard")

        assert response.status_code == 200
        assert b"Test Event" in response.data
        assert b"Test message" in response.data
        assert b"What made you smile today?" in response.data
        assert b"Good coffee!" in response.data


def test_dashboard_question_submit(client):
    login(client)

    with patch("app.api_request") as mock_api:
        mock_api.return_value.status_code = 200
        mock_api.return_value.json.return_value = {
            "message": "Answer submitted successfully"
        }

        response = client.post(
            "/dashboard/question",
            data={"response": "My answer to the daily question"},
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert mock_api.called

        call_args = mock_api.call_args_list[0][0]
        call_kwargs = mock_api.call_args_list[0][1]
        assert call_args[0] == "daily-question/answer"
        assert call_kwargs["method"] == "POST"
        assert call_kwargs["data"]["answer"] == "My answer to the daily question"


def test_calendar_page(client):
    login(client)

    with patch("app.api_request") as mock_api:
        mock_api.return_value.status_code = 200
        mock_api.return_value.json.return_value = {
            "events": [
                {"title": "Event 1", "start_time": "2025-04-30T10:00:00"},
                {"title": "Event 2", "start_time": "2025-05-01T14:00:00"},
            ]
        }

        response = client.get("/calendar")

        assert response.status_code == 200
        assert b"Event 1" in response.data
        assert b"Event 2" in response.data


def test_add_event(client):
    login(client)

    with patch("app.api_request") as mock_api:
        mock_api.return_value.status_code = 201
        mock_api.return_value.json.return_value = {
            "message": "Event created successfully"
        }

        response = client.post(
            "/calendar/add",
            data={
                "title": "New Event",
                "start_time": "2025-05-15T09:00:00",
                "end_time": "2025-05-15T10:00:00",
            },
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert mock_api.called
        assert b"Event created successfully" in response.data


def test_messages_page(client):
    login(client)

    with patch("app.api_request") as mock_api:

        def side_effect(endpoint, *args, **kwargs):
            mock_response = MagicMock()

            if endpoint == "auth/partner/status":
                mock_response.status_code = 200
                mock_response.json.return_value = {
                    "status": "connected",
                    "partner": {"id": "partner123", "name": "Partner User"},
                }
            elif endpoint == "messages/messages":
                mock_response.status_code = 200
                mock_response.json.return_value = {
                    "messages": [
                        {"content": "Hello!", "created_at": "2025-04-25T12:00:00"},
                        {"content": "Hi there!", "created_at": "2025-04-25T12:05:00"},
                    ]
                }

            return mock_response

        mock_api.side_effect = side_effect

        response = client.get("/messages")

        assert response.status_code == 200
        assert b"Partner User" in response.data
        assert b"Hello!" in response.data
        assert b"Hi there!" in response.data


def test_send_message(client):
    login(client)

    with patch("app.api_request") as mock_api:
        mock_api.return_value.status_code = 201
        mock_api.return_value.json.return_value = {
            "message": "Message sent successfully"
        }

        response = client.post(
            "/messages/send",
            data={"content": "Test message content", "receiver_id": "partner123"},
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert mock_api.called
        assert b"Message sent successfully" in response.data


def test_schedule_message(client):
    login(client)

    with patch("app.api_request") as mock_api:
        mock_api.return_value.status_code = 201
        mock_api.return_value.json.return_value = {
            "message": "Message scheduled successfully"
        }

        response = client.post(
            "/messages/schedule",
            data={
                "content": "Scheduled message",
                "receiver_id": "partner123",
                "scheduled_time": "2025-05-01T08:00:00",
            },
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert mock_api.called
        assert b"Message scheduled successfully" in response.data


def test_scheduled_messages_page(client):
    login(client)

    with patch("app.api_request") as mock_api:
        mock_api.return_value.status_code = 200
        mock_api.return_value.json.return_value = {
            "scheduled_messages": [
                {
                    "content": "Scheduled msg 1",
                    "scheduled_time": "2025-05-01T08:00:00",
                    "_id": "msg1",
                },
                {
                    "content": "Scheduled msg 2",
                    "scheduled_time": "2025-05-02T09:00:00",
                    "_id": "msg2",
                },
            ]
        }

        response = client.get("/messages/scheduled")

        assert response.status_code == 200
        assert b"Scheduled msg 1" in response.data
        assert b"Scheduled msg 2" in response.data


def test_cancel_scheduled_message(client):
    login(client)

    with patch("app.api_request") as mock_api:
        mock_api.return_value.status_code = 200
        mock_api.return_value.json.return_value = {
            "message": "Scheduled message cancelled successfully"
        }

        response = client.post("/messages/scheduled/msg1/cancel", follow_redirects=True)

        assert response.status_code == 200
        assert mock_api.called
        assert b"Scheduled message cancelled successfully" in response.data


def test_partner_page(client):
    login(client)

    with patch("app.api_request") as mock_api:
        mock_api.return_value.status_code = 200
        mock_api.return_value.json.return_value = {
            "status": "connected",
            "partner": {
                "id": "partner123",
                "name": "Partner User",
                "email": "partner@example.com",
            },
        }

        response = client.get("/partner")

        assert response.status_code == 200
        assert b"Partner User" in response.data
        assert (
            b"connected" in response.data.lower() or b"partner" in response.data.lower()
        )


def test_send_partner_invite(client):
    login(client)

    with patch("app.api_request") as mock_api:
        mock_api.return_value.status_code = 200
        mock_api.return_value.json.return_value = {
            "message": "Partnership invitation sent successfully"
        }

        response = client.post(
            "/partner/send-invite",
            data={"partner_email": "newpartner@example.com"},
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert mock_api.called
        assert b"Partnership invitation sent successfully" in response.data


def test_accept_partner_invite(client):
    login(client)

    with patch("app.api_request") as mock_api:
        mock_api.return_value.status_code = 200
        mock_api.return_value.json.return_value = {
            "message": "Partnership accepted successfully"
        }

        response = client.post("/partner/accept-invite", follow_redirects=True)

        assert response.status_code == 200
        assert mock_api.called
        assert b"Partnership accepted successfully" in response.data


def test_reject_partner_invite(client):
    login(client)

    with patch("app.api_request") as mock_api:
        mock_api.return_value.status_code = 200
        mock_api.return_value.json.return_value = {
            "message": "Partnership invitation rejected"
        }

        response = client.post("/partner/reject-invite", follow_redirects=True)

        assert response.status_code == 200
        assert mock_api.called
        assert b"Partnership invitation rejected" in response.data


def test_update_profile(client):
    login(client)

    with patch("app.api_request") as mock_api:
        mock_api.return_value.status_code = 200
        mock_api.return_value.json.return_value = {
            "message": "Profile updated successfully"
        }

        response = client.post(
            "/update_profile", data={"name": "Updated Name"}, follow_redirects=True
        )

        assert response.status_code == 200
        assert mock_api.called
        assert b"Profile updated successfully" in response.data


def test_change_password(client):
    login(client)

    with patch("app.api_request") as mock_api:
        mock_api.return_value.status_code = 200
        mock_api.return_value.json.return_value = {
            "message": "Password changed successfully"
        }

        response = client.post(
            "/change_password",
            data={
                "current_password": "oldpassword",
                "new_password": "newpassword",
                "confirm_password": "newpassword",
            },
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert mock_api.called
        assert b"Password changed successfully" in response.data


def test_change_password_mismatch(client):
    login(client)

    response = client.post(
        "/change_password",
        data={
            "current_password": "oldpassword",
            "new_password": "newpassword",
            "confirm_password": "differentpassword",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"New passwords do not match" in response.data


def test_quiz_page(client):
    login(client)

    response = client.get("/quiz")

    assert response.status_code == 200
    assert b"quiz" in response.data.lower()


def test_quiz_api_proxy_get(client):
    login(client)

    with patch("app.requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = json.dumps(
            {"questions": ["Question 1", "Question 2"]}
        ).encode()
        mock_response.headers = {"Content-Type": "application/json"}
        mock_get.return_value = mock_response

        response = client.get("/api/quiz/questions?category=relationship")

        assert response.status_code == 200
        assert b"Question 1" in response.data
        assert b"Question 2" in response.data


def test_quiz_api_proxy_post(client):
    login(client)

    with patch("app.requests.post") as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = json.dumps({"score": 85}).encode()
        mock_response.headers = {"Content-Type": "application/json"}
        mock_post.return_value = mock_response

        response = client.post(
            "/api/quiz/submit",
            data=json.dumps({"answers": [1, 2, 3]}),
            content_type="application/json",
        )

        assert response.status_code == 200
        assert b'"score": 85' in response.data


def test_quiz_api_proxy_unauthorized(client):
    response = client.get("/api/quiz/questions")

    assert response.status_code == 401
    assert b"Not authorized" in response.data


def test_quiz_api_proxy_error(client):
    login(client)

    with patch("app.requests.get") as mock_get:
        mock_get.side_effect = Exception("Connection failed")

        response = client.get("/api/quiz/questions")

        assert response.status_code == 500
        assert b"API proxy error" in response.data


def test_cancel_invite_error(client):
    login(client)

    with patch("app.api_request") as mock_api:
        mock_api.side_effect = Exception("API error")

        response = client.post("/partner/cancel-invite", follow_redirects=True)

        assert response.status_code == 200
        assert b"Error" in response.data


def test_disconnect_partner(client):
    login(client)

    with patch("app.api_request") as mock_api:
        mock_api.return_value.status_code = 200
        mock_api.return_value.json.return_value = {
            "message": "Partnership disconnected successfully"
        }

        response = client.post("/partner/disconnect", follow_redirects=True)

        assert response.status_code == 200
        assert b"Partnership disconnected successfully" in response.data


def test_send_message_empty_content(client):
    login(client)

    response = client.post(
        "/messages/send",
        data={"content": "", "receiver_id": "partner123"},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Message content missing" in response.data


def test_schedule_message_missing_parameters(client):
    login(client)

    response = client.post(
        "/messages/schedule",
        data={
            "content": "Test message"
            # Missing receiver_id and scheduled_time
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Message content, recipient, or scheduled time missing" in response.data


def test_update_profile_missing_name(client):
    login(client)

    response = client.post("/update_profile", data={}, follow_redirects=True)

    assert response.status_code == 200
    assert b"Name is required" in response.data


def test_change_password_missing_fields(client):
    login(client)

    response = client.post(
        "/change_password",
        data={
            "current_password": "oldpassword",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"All password fields are required" in response.data


def test_quiz_api_proxy_exception(client):
    login(client)

    with patch("app.requests.get") as mock_get:
        mock_get.side_effect = requests.exceptions.ConnectionError("Connection refused")

        response = client.get("/api/quiz/questions")

        assert response.status_code == 500
        assert b"API proxy error" in response.data


def test_dashboard_api_errors(client):
    login(client)

    with patch("app.api_request") as mock_api:
        mock_api.side_effect = Exception("API connection error")

        response = client.get("/dashboard")

        assert response.status_code == 200
        assert b"Error fetching events" in response.data
        assert b"Error fetching messages" in response.data
        assert b"Error fetching daily question" in response.data
        assert b"Error fetching daily answers" in response.data


def test_dashboard_question_api_error(client):
    login(client)

    with patch("app.api_request") as mock_api:
        mock_api.side_effect = Exception("API error")

        response = client.post(
            "/dashboard/question",
            data={"response": "Test response"},
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert b"Error" in response.data


def test_dashboard_question_submit_api_failure(client):
    login(client)

    with patch("app.api_request") as mock_api:
        mock_api.return_value.status_code = 400
        mock_api.return_value.json.return_value = {
            "message": "Failed to submit response"
        }

        response = client.post(
            "/dashboard/question",
            data={"response": "Test response"},
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert b"Failed to submit response" in response.data


def test_calendar_api_error(client):
    login(client)

    with patch("app.api_request") as mock_api:
        mock_api.side_effect = Exception("API error")

        response = client.get("/calendar")

        assert response.status_code == 200
        assert b"Error fetching events" in response.data


def test_add_event_api_error(client):
    login(client)

    with patch("app.api_request") as mock_api:
        mock_api.side_effect = Exception("API error")

        response = client.post(
            "/calendar/add",
            data={
                "title": "Test Event",
                "start_time": "2025-05-01T09:00:00",
                "end_time": "2025-05-01T10:00:00",
            },
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert b"Error" in response.data


def test_add_event_api_failure(client):
    login(client)

    with patch("app.api_request") as mock_api:
        mock_api.return_value.status_code = 400
        mock_api.return_value.json.return_value = {"message": "Invalid event data"}

        response = client.post(
            "/calendar/add",
            data={
                "title": "Test Event",
                "start_time": "2025-05-01T09:00:00",
                "end_time": "2025-05-01T10:00:00",
            },
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert b"Invalid event data" in response.data


def test_messages_api_errors(client):
    login(client)

    with patch("app.api_request") as mock_api:
        mock_api.side_effect = Exception("API error")

        response = client.get("/messages")

        assert response.status_code == 200
        assert b"Error fetching partner info" in response.data
        assert b"Error fetching messages" in response.data


def test_send_message_api_error(client):
    login(client)

    with patch("app.api_request") as mock_api:
        mock_api.side_effect = Exception("API error")

        response = client.post(
            "/messages/send",
            data={"content": "Test message", "receiver_id": "partner123"},
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert b"Error" in response.data


def test_send_message_api_failure(client):
    login(client)

    with patch("app.api_request") as mock_api:
        mock_api.return_value.status_code = 400
        mock_api.return_value.json.return_value = {"message": "Failed to send message"}

        response = client.post(
            "/messages/send",
            data={"content": "Test message", "receiver_id": "partner123"},
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert b"Failed to send message" in response.data


def test_schedule_message_api_error(client):
    login(client)

    with patch("app.api_request") as mock_api:
        mock_api.side_effect = Exception("API error")

        response = client.post(
            "/messages/schedule",
            data={
                "content": "Test message",
                "receiver_id": "partner123",
                "scheduled_time": "2025-05-01T09:00:00",
            },
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert b"Error" in response.data


def test_scheduled_messages_api_error(client):
    login(client)

    with patch("app.api_request") as mock_api:
        mock_api.side_effect = Exception("API error")

        response = client.get("/messages/scheduled")

        assert response.status_code == 200
        assert b"Error fetching scheduled messages" in response.data


def test_cancel_scheduled_message_api_error(client):
    login(client)

    with patch("app.api_request") as mock_api:
        mock_api.side_effect = Exception("API error")

        response = client.post(
            "/messages/scheduled/msg123/cancel", follow_redirects=True
        )

        assert response.status_code == 200
        assert b"Error" in response.data


def test_cancel_scheduled_message_api_failure(client):
    login(client)

    with patch("app.api_request") as mock_api:
        mock_api.return_value.status_code = 404
        mock_api.return_value.json.return_value = {"message": "Message not found"}

        response = client.post(
            "/messages/scheduled/msg123/cancel", follow_redirects=True
        )

        assert response.status_code == 200
        assert b"Message not found" in response.data


def test_partner_api_error(client):
    login(client)

    with patch("app.api_request") as mock_api:
        mock_api.side_effect = Exception("API error")

        response = client.get("/partner")

        assert response.status_code == 200
        assert b"Error fetching partner status" in response.data


def test_accept_invite_api_error(client):
    login(client)

    with patch("app.api_request") as mock_api:
        mock_api.side_effect = Exception("API error")

        response = client.post("/partner/accept-invite", follow_redirects=True)

        assert response.status_code == 200
        assert b"Error" in response.data


def test_reject_invite_api_error(client):
    login(client)

    with patch("app.api_request") as mock_api:
        mock_api.side_effect = Exception("API error")

        response = client.post("/partner/reject-invite", follow_redirects=True)

        assert response.status_code == 200
        assert b"Error" in response.data


def test_reject_invite_api_failure(client):
    login(client)

    with patch("app.api_request") as mock_api:
        mock_api.return_value.status_code = 400
        mock_api.return_value.json.return_value = {
            "message": "Failed to reject invitation"
        }

        response = client.post("/partner/reject-invite", follow_redirects=True)

        assert response.status_code == 200
        assert b"Failed to reject invitation" in response.data


def test_update_profile_api_error(client):
    login(client)

    with patch("app.api_request") as mock_api:
        mock_api.side_effect = Exception("API error")

        response = client.post(
            "/update_profile", data={"name": "New Name"}, follow_redirects=True
        )

        assert response.status_code == 200
        assert b"Error" in response.data


def test_update_profile_api_failure(client):
    login(client)

    with patch("app.api_request") as mock_api:
        mock_api.return_value.status_code = 400
        mock_api.return_value.json.return_value = {
            "message": "Failed to update profile"
        }

        response = client.post(
            "/update_profile", data={"name": "New Name"}, follow_redirects=True
        )

        assert response.status_code == 200
        assert b"Failed to update profile" in response.data


def test_change_password_api_error(client):
    login(client)

    with patch("app.api_request") as mock_api:
        mock_api.side_effect = Exception("API error")

        response = client.post(
            "/change_password",
            data={
                "current_password": "oldpass",
                "new_password": "newpass",
                "confirm_password": "newpass",
            },
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert b"Error" in response.data


def test_quiz_api_proxy_post_error(client):
    login(client)

    with patch("app.requests.post") as mock_post:
        mock_post.side_effect = Exception("Connection error")

        response = client.post(
            "/api/quiz/submit",
            data=json.dumps({"answers": [1, 2, 3]}),
            content_type="application/json",
        )

        assert response.status_code == 500
        assert b"API proxy error" in response.data


def test_settings_api_error(client):
    login(client)

    with patch("app.api_request") as mock_api:
        mock_api.side_effect = Exception("API error")

        response = client.post(
            "/settings", data={"email_notifications": "on"}, follow_redirects=True
        )

        assert response.status_code == 200
        assert b"Error" in response.data


def test_settings_api_failure(client):
    login(client)

    with patch("app.api_request") as mock_api:
        mock_api.return_value.status_code = 400
        mock_api.return_value.json.return_value = {
            "message": "Failed to update settings"
        }

        response = client.post(
            "/settings", data={"email_notifications": "on"}, follow_redirects=True
        )

        assert response.status_code == 200
        assert b"Failed to update settings" in response.data
