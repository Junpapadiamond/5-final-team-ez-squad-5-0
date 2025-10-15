from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.services import retrieval_service
from app.services.agent_llm_client import AgentLLMClient
from app.services.retrieval_service import RetrievalService


class _FakeCursor:
    def __init__(self, documents):
        self._documents = documents

    def limit(self, _value):
        return self

    def sort(self, *args, **kwargs):  # pragma: no cover - not used in test but matches API
        return self

    def __iter__(self):
        return iter(self._documents)


class _FakeCollection:
    def __init__(self, documents):
        self._documents = documents

    def aggregate(self, _pipeline):
        raise RuntimeError("vector search unavailable")

    def find(self, _query):
        documents = self._documents
        intents_filter = _query.get("intents") if isinstance(_query, dict) else None
        if intents_filter and "$in" in intents_filter:
            allowed = set(intents_filter["$in"])
            documents = [
                doc for doc in documents if allowed.intersection(doc.get("intents", []))
            ]
        return _FakeCursor(list(documents))

    def update_one(self, *args, **kwargs):  # pragma: no cover - required by ingestion script
        pass

    def delete_many(self, *args, **kwargs):  # pragma: no cover
        return SimpleNamespace(deleted_count=0)


class _FakeDB:
    def __init__(self, agent_embeddings, agent_playbooks):
        self.agent_embeddings = agent_embeddings
        self.agent_playbooks = agent_playbooks

    def __getitem__(self, key):
        return getattr(self, key)


@pytest.fixture(autouse=True)
def enable_rag(monkeypatch):
    monkeypatch.setenv("RAG_FEATURE_FLAG", "1")
    monkeypatch.setenv("RAG_VECTOR_BACKEND", "fallback")
    monkeypatch.setenv("REDIS_URL", "")


def test_fetch_context_uses_fallback_cosine(monkeypatch):
    documents = [
        {
            "_id": "chunk-1",
            "content": "Send a warm message thanking your partner for their help.",
            "section": "Messages",
            "source_path": "docs/messages/README.md",
            "embedding": [1.0, 0.0],
            "intents": ["tone_analysis"],
            "metadata": {},
        },
        {
            "_id": "chunk-2",
            "content": "Plan a quick calendar check-in for the week ahead.",
            "section": "Calendar",
            "source_path": "docs/calendar/README.md",
            "embedding": [0.1, 0.9],
            "intents": ["calendar"],
            "metadata": {},
        },
    ]

    fake_db = _FakeDB(_FakeCollection(documents), _FakeCollection([]))
    monkeypatch.setattr(retrieval_service, "mongo", SimpleNamespace(db=fake_db))
    monkeypatch.setattr(
        RetrievalService,
        "_embed_text",
        classmethod(lambda cls, text: [1.0, 0.0] if "thank" in text else [0.0, 1.0]),
    )

    results = RetrievalService.fetch_context(
        user_id="user-1",
        intents=("tone_analysis",),
        query_text="Thanks for helping today!",
        limit=1,
    )

    assert results, "Expected at least one retrieval result"
    top = results[0]
    assert top["chunk_id"] == "chunk-1"
    assert "[Source: docs/messages/README.md" in top["citation"]
    assert "prompt_snippet" in top


def test_agent_orchestrator_passes_retrieval(monkeypatch):
    captured_retrieval = {}

    def fake_fetch_context(**kwargs):
        captured_retrieval.update(kwargs)
        return [{"chunk_id": "demo", "prompt_snippet": "Tip", "citation": "[Source: demo §Tips]"}]

    def fake_analyze_tone(message, context, retrieval):  # pragma: no cover - manual assertion
        assert retrieval and retrieval[0]["chunk_id"] == "demo"
        return {"tone_summary": "ok", "retrieval_sources": [item["chunk_id"] for item in retrieval]}

    monkeypatch.setattr(RetrievalService, "fetch_context", staticmethod(fake_fetch_context))
    monkeypatch.setattr(AgentLLMClient, "analyze_tone", staticmethod(fake_analyze_tone))

    from app.services.agent_orchestrator import AgentOrchestrator

    result = AgentOrchestrator.analyze_tone("user-123", "Hello there")

    assert captured_retrieval["intents"] == ("tone_analysis",)
    assert result["retrieval_sources"] == ["demo"]
