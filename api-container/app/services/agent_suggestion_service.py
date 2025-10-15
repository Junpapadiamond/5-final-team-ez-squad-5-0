from __future__ import annotations

import os
import uuid
import logging
import threading
from concurrent.futures import ThreadPoolExecutor, Future, TimeoutError as FuturesTimeout
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from .. import mongo
from .agent_orchestrator import AgentOrchestrator


logger = logging.getLogger(__name__)

_refresh_executor: Optional[ThreadPoolExecutor] = None
_refresh_lock = threading.Lock()
_refresh_inflight: Dict[str, Future] = {}


class AgentSuggestionService:
    """Generates AI-powered coaching suggestions and caches them for reuse."""

    @staticmethod
    def get_suggestions(user_id: str) -> Tuple[Dict[str, Any], Optional[str]]:
        try:
            cached = AgentSuggestionService._get_cached_suggestions(user_id)
            if cached:
                return cached, None

            future = AgentSuggestionService._schedule_async_refresh(user_id)
            if future is not None:
                timeout = AgentSuggestionService._llm_sync_timeout()
                try:
                    payload = future.result(timeout=timeout)
                    if payload:
                        return payload, None
                except FuturesTimeout:
                    logger.warning(
                        "Agent suggestion LLM call exceeded %.1fs for user %s; returning fallback and continuing async",
                        timeout,
                        user_id,
                    )
                except Exception as exc:  # pragma: no cover - defensive guard
                    logger.warning(
                        "Agent suggestion LLM call failed for user %s: %s",
                        user_id,
                        exc,
                    )

            fallback_payload = AgentSuggestionService._build_fallback_payload(user_id)
            if future is not None:
                fallback_payload.setdefault("metadata", {})
                fallback_payload["metadata"]["async_refresh"] = True
            return fallback_payload, None
        except Exception as exc:  # pragma: no cover - defensive guard
            logger.exception("Agent suggestion retrieval failed for user %s", user_id)
            return {"suggestions": [], "metadata": None}, f"Failed to generate suggestions: {str(exc)}"

    @staticmethod
    def _cache_collection():
        return getattr(mongo.db, "agent_coaching_cache", None)

    @staticmethod
    def _cache_ttl_hours() -> int:
        try:
            return max(0, int(os.getenv("AGENT_COACHING_CACHE_HOURS", "6")))
        except ValueError:
            return 0

    @staticmethod
    def _get_cached_suggestions(user_id: str) -> Optional[Dict[str, Any]]:
        collection = AgentSuggestionService._cache_collection()
        ttl = AgentSuggestionService._cache_ttl_hours()
        if collection is None or ttl <= 0:
            return None

        cutoff = datetime.now(timezone.utc) - timedelta(hours=ttl)
        doc = collection.find_one({"user_id": user_id, "created_at": {"$gte": cutoff}})
        if not doc:
            return None

        payload = doc.get("payload")
        if isinstance(payload, dict):
            return payload

        # Backwards compatibility with legacy cache shape
        suggestions = doc.get("suggestions")
        if isinstance(suggestions, list):
            return {"suggestions": suggestions, "metadata": doc.get("metadata")}

        return None

    @staticmethod
    def _store_cache(user_id: str, payload: Dict[str, Any]) -> None:
        collection = AgentSuggestionService._cache_collection()
        if collection is None:
            return

        collection.update_one(
            {"user_id": user_id},
            {"$set": {"payload": payload, "created_at": datetime.now(timezone.utc)}},
            upsert=True,
        )

    @staticmethod
    def _build_fallback_payload(user_id: str) -> Dict[str, Any]:
        context = AgentOrchestrator.build_context(user_id)
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        suggestions: List[Dict[str, Any]] = []

        daily_question = (context or {}).get("daily_question") or {}
        if daily_question and not daily_question.get("answered"):
            question = daily_question.get("question") or "today's daily question"
            suggestions.append(
                {
                    "id": f"{user_id}-fallback-daily",
                    "type": "daily_question",
                    "title": "Check in on today's reflection",
                    "summary": "Answer the daily prompt and share it with your partner to keep the conversation flowing.",
                    "confidence": 0.55,
                    "generated_at": now,
                    "payload": {
                        "call_to_action": f"Take a minute to answer {question}.",
                        "suggested_message": "Just answered today's question - want to trade thoughts later tonight?",
                    },
                    "ai_source": "logic",
                    "llm_metadata": None,
                }
            )

        recent_messages = (context or {}).get("recent_messages") or []
        if recent_messages:
            latest = recent_messages[0]
            preview = (latest or {}).get("content") or ""
            if len(preview) > 60:
                preview = preview[:57] + "..."
            preview = preview or "their last note"
            suggestions.append(
                {
                    "id": f"{user_id}-fallback-reply",
                    "type": "message_draft",
                    "title": "Send a quick reply",
                    "summary": "Follow up on the latest note so the conversation stays active.",
                    "confidence": 0.5,
                    "generated_at": now,
                    "payload": {
                        "call_to_action": "Send a warm reply that references their latest note.",
                        "suggested_message": f"Loved your message about \"{preview}\" - want to chat more about it later?",
                    },
                    "ai_source": "logic",
                    "llm_metadata": None,
                }
            )

        upcoming_events = (context or {}).get("upcoming_events") or []
        if not upcoming_events:
            suggestions.append(
                {
                    "id": f"{user_id}-fallback-calendar",
                    "type": "calendar",
                    "title": "Plan a shared moment",
                    "summary": "Add something small to the calendar so you both have a moment to look forward to.",
                    "confidence": 0.45,
                    "generated_at": now,
                    "payload": {
                        "call_to_action": "Block a short check-in or date on the calendar for this week.",
                        "suggested_message": "Let's pencil in a 20-minute catch-up this week - any evening work for you?",
                    },
                    "ai_source": "logic",
                    "llm_metadata": None,
                }
            )

        if not suggestions:
            suggestions.append(
                {
                    "id": f"{user_id}-fallback-default",
                    "type": "message_draft",
                    "title": "Share a win",
                    "summary": "Send an appreciation note to keep momentum.",
                    "confidence": 0.4,
                    "generated_at": now,
                    "payload": {
                        "call_to_action": "Send a short message thanking them for something this week.",
                        "suggested_message": "Wanted to say thanks for being there today - it really meant a lot <3",
                    },
                    "ai_source": "logic",
                    "llm_metadata": None,
                }
            )

        metadata = {
            "model": None,
            "generated_at": now,
            "strategy": "deterministic-fallback",
            "explanation": "Returning cached heuristics while AI refresh completes.",
        }
        return {"suggestions": suggestions, "metadata": metadata}

    @staticmethod
    def _llm_sync_timeout() -> float:
        try:
            return max(0.5, float(os.getenv("AGENT_COACHING_SYNC_TIMEOUT", "2.5")))
        except ValueError:
            return 2.5

    @staticmethod
    def _schedule_async_refresh(user_id: str) -> Optional[Future]:
        executor = AgentSuggestionService._get_executor()
        if executor is None:
            return None

        with _refresh_lock:
            future = _refresh_inflight.get(user_id)
            if future is not None and not future.done():
                return future

            def _task():
                try:
                    package = AgentOrchestrator.plan_coaching(user_id) or {}
                    if not package:
                        return None
                    payload = AgentSuggestionService._format_llm_payload(user_id, package)
                    AgentSuggestionService._store_cache(user_id, payload)
                    logger.info("Agent suggestions refreshed via LLM for user %s", user_id)
                    return payload
                except Exception as exc:  # pragma: no cover - defensive guard
                    logger.warning("Async agent suggestion refresh failed for user %s: %s", user_id, exc)
                    return None
                finally:
                    with _refresh_lock:
                        _refresh_inflight.pop(user_id, None)

            future = executor.submit(_task)
            _refresh_inflight[user_id] = future
            return future

    @staticmethod
    def _get_executor() -> Optional[ThreadPoolExecutor]:
        global _refresh_executor
        if _refresh_executor is not None:
            return _refresh_executor
        try:
            workers = max(1, int(os.getenv("AGENT_SUGGESTION_WORKERS", "2")))
        except ValueError:
            workers = 2
        _refresh_executor = ThreadPoolExecutor(
            max_workers=workers,
            thread_name_prefix="agent-suggestion",
        )
        return _refresh_executor

    @staticmethod
    def _format_llm_payload(user_id: str, package: Dict[str, Any]) -> Dict[str, Any]:
        cards = package.get("cards") or []
        generated_at = package.get("generated_at") or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        metadata = {
            "model": package.get("model"),
            "generated_at": generated_at,
            "strategy": package.get("strategy"),
            "explanation": package.get("explanation"),
        }
        if package.get("retrieval_sources"):
            metadata["retrieval_sources"] = package.get("retrieval_sources")

        suggestions: List[Dict[str, Any]] = []
        for card in cards:
            if not isinstance(card, dict):
                continue
            suggestion_id = card.get("id") or f"{user_id}-suggestion-{uuid.uuid4()}"
            payload: Dict[str, Any] = {}
            for key in ("call_to_action", "suggested_message"):
                value = card.get(key)
                if value:
                    payload[key] = str(value)
            card_metadata = dict(metadata)
            suggestions.append(
                {
                    "id": suggestion_id,
                    "type": card.get("type", "custom"),
                    "title": card.get("title", "Agent insight"),
                    "summary": card.get("summary", ""),
                    "confidence": card.get("confidence"),
                    "generated_at": generated_at,
                    "payload": payload,
                    "ai_source": "openai",
                    "llm_metadata": card_metadata,
                }
            )

        return {"suggestions": suggestions, "metadata": metadata}


__all__ = ["AgentSuggestionService"]
