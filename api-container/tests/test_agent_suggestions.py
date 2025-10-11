import pytest
from flask_jwt_extended import create_access_token

from app import create_app
from app.controllers import agent_controller
from app.services.agent_suggestion_service import AgentSuggestionService
from datetime import datetime, timedelta
from types import SimpleNamespace


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


def test_agent_suggestions_service(monkeypatch):
    now = datetime.utcnow()
    message_docs = [
        {"sender_id": "user-123", "content": "Good night ❤️", "created_at": now - timedelta(hours=20)}
    ]
    daily_docs = [
        {
            "user_id": "user-123",
            "date": now.date().isoformat(),
            "question": "What made you smile today?",
            "answered": False,
        }
    ]
    event_docs: list = []

    mongo_stub = SimpleNamespace(
        db=SimpleNamespace(
            messages=SimpleNamespace(
                find=lambda query: StubCursor(message_docs),
                find_one=lambda query, sort=None: message_docs[0],
            ),
            daily_questions=SimpleNamespace(find_one=lambda query: daily_docs[0]),
            events=SimpleNamespace(
                find=lambda query: StubCursor(event_docs),
            ),
            agent_coaching_cache=SimpleNamespace(
                find_one=lambda query: None,
                update_one=lambda query, update, upsert=False: None,
            ),
        ),
    )

    monkeypatch.setattr("app.services.agent_suggestion_service.mongo", mongo_stub)
    monkeypatch.setattr(
        "app.services.agent_suggestion_service.StyleProfileService",
        SimpleNamespace(get_style_profile=lambda user_id, **kwargs: ({"style_summary": "Warm & playful"}, None)),
    )
    monkeypatch.setattr(
        "app.services.agent_suggestion_service.AgentOrchestrator.plan_coaching",
        lambda user_id: [
            {
                "id": "llm-1",
                "type": "message_draft",
                "title": "Share appreciation",
                "summary": "Send a note thanking your partner for a recent support moment.",
                "confidence": 0.83,
                "call_to_action": "Draft a heartfelt message now.",
            }
        ],
    )

    suggestions, error = AgentSuggestionService.get_suggestions("user-123")
    assert error is None
    types = {s["type"] for s in suggestions}
    assert "message_draft" in types
    assert "daily_question" in types
    assert "calendar" in types


def test_agent_actions_endpoint(client, auth_headers, monkeypatch):
    sample_suggestions = [{"id": "1", "type": "message_draft"}]

    monkeypatch.setattr(
        agent_controller.AgentSuggestionService,
        "get_suggestions",
        staticmethod(lambda user_id: (sample_suggestions, None)),
    )

    response = client.get("/api/agent/actions", headers=auth_headers)
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["suggestions"] == sample_suggestions
