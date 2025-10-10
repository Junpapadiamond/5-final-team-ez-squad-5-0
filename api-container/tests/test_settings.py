import pytest

pytest.skip(
    "Legacy settings route tests pending rewrite for consolidated controller architecture.",
    allow_module_level=True,
)

from unittest.mock import patch, MagicMock
from bson.objectid import ObjectId
import json


@pytest.fixture
def app():
    from flask import Flask

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = "test_secret_key"
    app.config["JWT_SECRET_KEY"] = "test_jwt_secret_key"

    app.register_blueprint(settings_bp, url_prefix="/api/settings")

    from flask_jwt_extended import JWTManager

    jwt = JWTManager(app)

    return app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def valid_object_id():
    """Create a valid MongoDB ObjectId for testing"""
    return str(ObjectId())


@pytest.fixture
def auth_headers(app, valid_object_id):
    with app.app_context():
        from flask_jwt_extended import create_access_token

        token = create_access_token(identity=valid_object_id)
    return {"Authorization": f"Bearer {token}"}


def test_get_profile_success(client, app, auth_headers, valid_object_id):
    """Test successful profile retrieval"""
    mock_user = {
        "_id": valid_object_id,
        "email": "test@example.com",
        "username": "testuser",
        "password_hash": "hashed_password",
        "profile": {"name": "Test User"},
    }

    with app.app_context():
        with patch(
            "app.routes.settings.get_jwt_identity", return_value=valid_object_id
        ), patch("app.routes.settings.get_user_by_id", return_value=mock_user):
            response = client.get("/api/settings/profile", headers=auth_headers)

            assert response.status_code == 200
            data = json.loads(response.data)
            assert "user" in data
            assert data["user"]["email"] == "test@example.com"
            assert "password_hash" not in data["user"]


def test_get_profile_user_not_found(client, app, auth_headers, valid_object_id):
    """Test profile retrieval when user is not found"""
    with app.app_context():
        with patch(
            "app.routes.settings.get_jwt_identity", return_value=valid_object_id
        ), patch("app.routes.settings.get_user_by_id", return_value=None):
            response = client.get("/api/settings/profile", headers=auth_headers)

            assert response.status_code == 404
            data = json.loads(response.data)
            assert data["message"] == "User not found"


def test_get_profile_no_password_hash(client, app, auth_headers, valid_object_id):
    """Test profile retrieval when user has no password hash field"""
    mock_user = {
        "_id": valid_object_id,
        "email": "test@example.com",
        "username": "testuser",
        # No password_hash field
        "profile": {"name": "Test User"},
    }

    with app.app_context():
        with patch(
            "app.routes.settings.get_jwt_identity", return_value=valid_object_id
        ), patch("app.routes.settings.get_user_by_id", return_value=mock_user):
            response = client.get("/api/settings/profile", headers=auth_headers)

            assert response.status_code == 200
            data = json.loads(response.data)
            assert "user" in data
            assert data["user"]["email"] == "test@example.com"


def test_update_email_notifications_enabled(client, app, auth_headers, valid_object_id):
    """Test updating email notifications to enabled"""
    mock_update_result = MagicMock()
    mock_update_result.modified_count = 1

    with app.app_context():
        with patch(
            "app.routes.settings.get_jwt_identity", return_value=valid_object_id
        ), patch(
            "app.routes.settings.mongo.db.users.update_one",
            return_value=mock_update_result,
        ) as mock_update:
            response = client.put(
                "/api/settings/email-notifications",
                headers={**auth_headers, "Content-Type": "application/json"},
                data=json.dumps({"enabled": True}),
            )

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["message"] == "Email notification settings updated successfully"

            # Verify correct parameters were passed to update_one
            mock_update.assert_called_once()
            call_args = mock_update.call_args
            assert call_args[0][0] == {"_id": ObjectId(valid_object_id)}
            assert call_args[0][1] == {"$set": {"email_notifications": True}}


def test_update_email_notifications_disabled(
    client, app, auth_headers, valid_object_id
):
    """Test updating email notifications to disabled"""
    mock_update_result = MagicMock()
    mock_update_result.modified_count = 1

    with app.app_context():
        with patch(
            "app.routes.settings.get_jwt_identity", return_value=valid_object_id
        ), patch(
            "app.routes.settings.mongo.db.users.update_one",
            return_value=mock_update_result,
        ) as mock_update:
            response = client.put(
                "/api/settings/email-notifications",
                headers={**auth_headers, "Content-Type": "application/json"},
                data=json.dumps({"enabled": False}),
            )

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["message"] == "Email notification settings updated successfully"

            # Verify correct parameters were passed to update_one
            mock_update.assert_called_once()
            call_args = mock_update.call_args
            assert call_args[0][0] == {"_id": ObjectId(valid_object_id)}
            assert call_args[0][1] == {"$set": {"email_notifications": False}}


def test_update_email_notifications_no_changes(
    client, app, auth_headers, valid_object_id
):
    """Test updating email notifications when no changes are made"""
    mock_update_result = MagicMock()
    mock_update_result.modified_count = 0

    with app.app_context():
        with patch(
            "app.routes.settings.get_jwt_identity", return_value=valid_object_id
        ), patch(
            "app.routes.settings.mongo.db.users.update_one",
            return_value=mock_update_result,
        ):
            response = client.put(
                "/api/settings/email-notifications",
                headers={**auth_headers, "Content-Type": "application/json"},
                data=json.dumps({"enabled": True}),
            )

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["message"] == "No changes made"


def test_update_email_notifications_default_value(
    client, app, auth_headers, valid_object_id
):
    """Test updating email notifications with no enabled parameter (should default to True)"""
    mock_update_result = MagicMock()
    mock_update_result.modified_count = 1

    with app.app_context():
        with patch(
            "app.routes.settings.get_jwt_identity", return_value=valid_object_id
        ), patch(
            "app.routes.settings.mongo.db.users.update_one",
            return_value=mock_update_result,
        ) as mock_update:
            response = client.put(
                "/api/settings/email-notifications",
                headers={**auth_headers, "Content-Type": "application/json"},
                data=json.dumps({}),  # No enabled parameter
            )

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["message"] == "Email notification settings updated successfully"

            # Verify correct parameters were passed to update_one
            mock_update.assert_called_once()
            call_args = mock_update.call_args
            assert call_args[0][0] == {"_id": ObjectId(valid_object_id)}
            assert call_args[0][1] == {"$set": {"email_notifications": True}}


def test_route_auth_required(client, app):
    """Test that routes require authentication"""
    with app.app_context():
        # Test without authorization header
        profile_response = client.get("/api/settings/profile")
        assert profile_response.status_code == 401

        notifications_response = client.put(
            "/api/settings/email-notifications",
            headers={"Content-Type": "application/json"},
            data=json.dumps({"enabled": True}),
        )
        assert notifications_response.status_code == 401
