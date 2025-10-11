import pytest
from flask_jwt_extended import create_access_token

from app import create_app
from app.controllers import agent_controller
from app.services.agent_analysis_service import AgentAnalysisService
from app.services.openai_client import OpenAIClient
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
        token = create_access_token(identity="user-789")
    return {"Authorization": f"Bearer {token}"}


def test_analyze_input_generates_feedback(monkeypatch):
    captured_content = {}

    monkeypatch.setattr(
        "app.services.agent_analysis_service.StyleProfileService.register_sample",
        lambda user_id, content: captured_content.setdefault(user_id, []).append(content),
    )
    monkeypatch.setattr(
        "app.services.agent_analysis_service.StyleProfileService.get_style_profile",
        lambda user_id, **kwargs: ({"style_summary": "Warm tone"}, None),
    )
    monkeypatch.setattr(
        "app.services.agent_analysis_service.AgentOrchestrator.analyze_tone",
        lambda user_id, text: {
            "sentiment": "positive",
            "confidence": 0.87,
            "tone_summary": "Warm and playful. Keep the appreciation flowing.",
            "coaching_tips": ["Mention something specific you appreciate."],
            "strengths": ["Affectionate tone."],
            "suggested_reply": "Maybe add a quick compliment before you hit send.",
        },
    )
    mongo_stub = SimpleNamespace(
        db=SimpleNamespace(
            agent_tone_cache=SimpleNamespace(
                find_one=lambda query: None,
                update_one=lambda query, update, upsert=False: None,
            )
        )
    )
    monkeypatch.setattr("app.services.agent_analysis_service.mongo", mongo_stub)

    result, error = AgentAnalysisService.analyze_input("user-789", "Hey love! Can't wait for dinner 😊")

    assert error is None
    assert result["analysis"]["sentiment"] == "positive"
    assert result["analysis"]["sentiment_probability_positive"] == 0.87
    assert result["llm_feedback"] == "Warm and playful. Keep the appreciation flowing."
    assert captured_content["user-789"][0].startswith("Hey love")
    assert result["style_profile"]["style_summary"] == "Warm tone"
    assert "tips" in result and result["tips"]
    assert result["ai_source"] == "openai"
    assert result["suggested_reply"]


def test_analyze_input_falls_back_to_legacy(monkeypatch):
    monkeypatch.setattr(
        "app.services.agent_analysis_service.StyleProfileService.register_sample",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        "app.services.agent_analysis_service.StyleProfileService.get_style_profile",
        lambda user_id, **kwargs: ({"style_summary": "Measured"}, None),
    )
    monkeypatch.setattr(
        "app.services.agent_analysis_service.AgentOrchestrator.analyze_tone",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        "app.services.agent_analysis_service.SentimentModel.predict",
        staticmethod(lambda text: SimpleNamespace(label="neutral", probability_positive=0.42)),
    )
    monkeypatch.setattr(
        "app.services.agent_analysis_service.OpenAIClient.is_available",
        staticmethod(lambda: True),
    )
    monkeypatch.setattr(
        "app.services.agent_analysis_service.OpenAIClient.summarize_tone",
        lambda text: "Legacy fallback summary.",
    )
    mongo_stub = SimpleNamespace(
        db=SimpleNamespace(
            agent_tone_cache=SimpleNamespace(
                find_one=lambda query: None,
                update_one=lambda query, update, upsert=False: None,
            )
        )
    )
    monkeypatch.setattr("app.services.agent_analysis_service.mongo", mongo_stub)

    result, error = AgentAnalysisService.analyze_input("user-123", "Short draft.")

    assert error is None
    assert result["analysis"]["sentiment"] == "neutral"
    assert result["llm_feedback"] == "Legacy fallback summary."
    assert result["ai_source"] == "legacy"


def test_agent_analyze_endpoint(client, auth_headers, monkeypatch):
    sample_result = {"analysis": {"sentiment": "neutral"}, "tips": ["Example"], "style_profile": {}, "ai_source": "legacy"}

    monkeypatch.setattr(
        agent_controller.AgentAnalysisService,
        "analyze_input",
        staticmethod(lambda user_id, content: (sample_result, None)),
    )

    response = client.post(
        "/api/agent/analyze",
        headers=auth_headers,
        json={"content": "Sample message"},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["analysis"]["sentiment"] == "neutral"
    assert payload["tips"] == ["Example"]


def test_agent_analyze_requires_content(client, auth_headers):
    response = client.post("/api/agent/analyze", headers=auth_headers, json={})
    assert response.status_code == 400


def test_openai_client_handles_init_type_error(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "fake-key")
    original_client = OpenAIClient._client
    OpenAIClient._client = None

    class BrokenOpenAI:
        def __init__(self, *args, **kwargs):
            raise TypeError("proxies")

    monkeypatch.setattr("app.services.openai_client.OpenAI", BrokenOpenAI)
    monkeypatch.setattr(
        "app.services.openai_client.OpenAIClient._get_httpx_version",
        staticmethod(lambda: "0.26.0"),
    )

    try:
        assert OpenAIClient.summarize_tone("test message") is None
        assert OpenAIClient._client is None
    finally:
        OpenAIClient._client = original_client
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
