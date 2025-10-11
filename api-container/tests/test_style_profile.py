from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest
from flask_jwt_extended import create_access_token

from app import create_app
from app.controllers import agent_controller
from app.services.style_profile_service import StyleProfileService


class StubCursor:
    def __init__(self, docs):
        self._docs = docs

    def sort(self, *_args, **_kwargs):
        return self

    def limit(self, _n):
        return self

    def __iter__(self):
        return iter(self._docs)


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


def test_style_profile_computation(monkeypatch):
    now = datetime.utcnow()
    messages = [
        {"sender_id": "user-1", "content": "Good morning!!! ☀️😊", "created_at": now},
        {"sender_id": "user-1", "content": "Lunch later? 😋", "created_at": now - timedelta(minutes=5)},
        {"sender_id": "user-1", "content": "I miss you... ❤️", "created_at": now - timedelta(minutes=10)},
    ]

    style_profiles_store = {}

    mongo_stub = SimpleNamespace(
        db=SimpleNamespace(
            messages=SimpleNamespace(find=lambda query: StubCursor(messages)),
            style_profiles=SimpleNamespace(
                find_one=lambda query: None,
                update_one=lambda filter, update, upsert=False: style_profiles_store.update(
                    {filter["user_id"]: update["$set"]}
                ),
            ),
            style_samples=SimpleNamespace(
                insert_one=lambda doc: None,
                find=lambda query: StubCursor([]),
                delete_many=lambda query: None,
            ),
        )
    )

    monkeypatch.setattr("app.services.style_profile_service.mongo", mongo_stub)
    monkeypatch.setattr(
        "app.services.style_profile_service.AgentLLMClient.summarize_style",
        lambda context: {"style_summary": "LLM-enhanced summary", "signature_examples": ["Example line"]},
    )

    profile, error = StyleProfileService.get_style_profile("user-1", force_refresh=True)

    assert error is None
    assert profile["message_count"] == 3
    assert profile["emoji_frequency"]
    assert profile["signature_examples"]
    assert profile["style_summary"]
    assert profile["cached"] is False


def test_style_profile_cached(monkeypatch):
    recent_doc = {
        "user_id": "user-2",
        "data": {"message_count": 5, "style_summary": "cached summary"},
        "message_count": 5,
        "updated_at": datetime.utcnow(),
    }

    mongo_stub = SimpleNamespace(
        db=SimpleNamespace(
            messages=SimpleNamespace(find=lambda query: StubCursor([])),
            style_profiles=SimpleNamespace(
                find_one=lambda query: recent_doc,
                update_one=lambda *args, **kwargs: None,
            ),
            style_samples=SimpleNamespace(
                insert_one=lambda doc: None,
                find=lambda query: StubCursor([]),
                delete_many=lambda query: None,
            ),
        )
    )

    monkeypatch.setattr("app.services.style_profile_service.mongo", mongo_stub)
    monkeypatch.setattr(
        "app.services.style_profile_service.AgentLLMClient.summarize_style",
        lambda context: None,
    )

    profile, error = StyleProfileService.get_style_profile("user-2")
    assert error is None
    assert profile["cached"] is True
    assert profile["style_summary"] == "cached summary"


def test_agent_style_profile_endpoint(client, auth_headers, monkeypatch):
    sample_profile = {"message_count": 10, "style_summary": "Sample summary"}

    monkeypatch.setattr(
        agent_controller.StyleProfileService,
        "get_style_profile",
        staticmethod(lambda user_id, force_refresh=False: (sample_profile, None)),
    )

    response = client.get("/api/agent/style-profile", headers=auth_headers)
    assert response.status_code == 200
    assert response.get_json()["style_summary"] == "Sample summary"
