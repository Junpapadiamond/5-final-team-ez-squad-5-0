import pytest
from flask_jwt_extended import create_access_token

from app import create_app
from app.controllers import agent_controller
from app.services.agent_suggestion_service import AgentSuggestionService
from types import SimpleNamespace


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
    mongo_stub = SimpleNamespace(
        db=SimpleNamespace(
            agent_coaching_cache=SimpleNamespace(
                find_one=lambda query: None,
                update_one=lambda query, update, upsert=False: None,
            ),
        ),
    )

    monkeypatch.setattr("app.services.agent_suggestion_service.mongo", mongo_stub)
    monkeypatch.setattr(
        "app.services.agent_suggestion_service.AgentOrchestrator.plan_coaching",
        lambda user_id: {
            "model": "gpt-test",
            "cards": [
                {
                    "id": "llm-1",
                    "type": "message_draft",
                    "title": "Share appreciation",
                    "summary": "Send a note thanking your partner for support.",
                    "confidence": 0.83,
                    "call_to_action": "Draft a heartfelt message now.",
                }
            ],
        },
    )

    payload, error = AgentSuggestionService.get_suggestions("user-123")
    assert error is None
    suggestions = payload["suggestions"]
    assert len(suggestions) == 1
    assert suggestions[0]["type"] == "message_draft"
    assert payload["metadata"]["model"] == "gpt-test"


def test_agent_actions_endpoint(client, auth_headers, monkeypatch):
    sample_payload = {
        "suggestions": [{"id": "1", "type": "message_draft"}],
        "metadata": {"model": "gpt-test"},
    }

    monkeypatch.setattr(
        agent_controller.AgentSuggestionService,
        "get_suggestions",
        staticmethod(lambda user_id: (sample_payload, None)),
    )
    monkeypatch.setattr(
        agent_controller.AgentActionQueueService,
        "list_pending",
        staticmethod(lambda user_id, limit, include_completed=False: []),
    )
    monkeypatch.setattr(
        agent_controller.AgentDecisionService,
        "process_pending_events",
        staticmethod(lambda batch_size=25: {"events_processed": 0, "plans_generated": 0}),
    )

    response = client.get("/api/agent/actions", headers=auth_headers)
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["suggestions"] == sample_payload["suggestions"]
    assert payload["llm"] == sample_payload["metadata"]
