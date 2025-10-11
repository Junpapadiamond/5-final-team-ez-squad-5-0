from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from .. import mongo
from .agent_orchestrator import AgentOrchestrator
from .style_profile_service import StyleProfileService


class AgentSuggestionService:
    """Generates coaching suggestions blending LLM insights with deterministic reminders."""

    @staticmethod
    def get_suggestions(user_id: str) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        try:
            cached = AgentSuggestionService._get_cached_suggestions(user_id)
            if cached:
                return cached, None

            suggestions: List[Dict[str, Any]] = []
            llm_cards = AgentOrchestrator.plan_coaching(user_id) or []
            now = datetime.utcnow().isoformat() + "Z"

            for card in llm_cards:
                suggestion = {
                    "id": card.get("id", str(uuid.uuid4())),
                    "type": card.get("type", "custom"),
                    "title": card.get("title", "Agent insight"),
                    "summary": card.get("summary", ""),
                    "confidence": card.get("confidence"),
                    "generated_at": now,
                    "payload": {
                        "call_to_action": card.get("call_to_action"),
                        "suggested_message": card.get("suggested_message"),
                    },
                    "ai_source": "openai",
                }
                suggestions.append(suggestion)

            legacy_cards = AgentSuggestionService._legacy_suggestions(user_id)
            merged = AgentSuggestionService._merge_suggestions(suggestions, legacy_cards)

            AgentSuggestionService._store_cache(user_id, merged)
            return merged, None
        except Exception as exc:  # pragma: no cover - defensive
            return [], f"Failed to generate suggestions: {str(exc)}"

    @staticmethod
    def _legacy_suggestions(user_id: str) -> List[Dict[str, Any]]:
        now = datetime.utcnow()
        suggestions: List[Dict[str, Any]] = []

        style_profile, _ = StyleProfileService.get_style_profile(user_id, cache_ttl_hours=6)
        style_summary = (style_profile or {}).get("style_summary")
        last_message = AgentSuggestionService._get_last_message(user_id)
        if AgentSuggestionService._needs_connection_ping(last_message, now):
            suggestions.append(
                AgentSuggestionService._build_message_prompt(
                    user_id=user_id,
                    style_summary=style_summary,
                    last_message=last_message,
                    now=now,
                )
            )

        daily_prompt = AgentSuggestionService._get_daily_question_prompt(user_id)
        if daily_prompt:
            suggestions.append(daily_prompt)

        calendar_prompt = AgentSuggestionService._get_calendar_prompt(user_id, now)
        if calendar_prompt:
            suggestions.append(calendar_prompt)

        for item in suggestions:
            item.setdefault("ai_source", "legacy")

        return suggestions

    @staticmethod
    def _merge_suggestions(
        primary: List[Dict[str, Any]],
        secondary: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        seen_types = {item["type"] for item in primary}
        merged = list(primary)

        for card in secondary:
            if card["type"] not in seen_types:
                merged.append(card)
        return merged

    @staticmethod
    def _get_last_message(user_id: str) -> Optional[Dict[str, Any]]:
        return mongo.db.messages.find_one(
            {
                "$or": [
                    {"sender_id": user_id},
                    {"receiver_id": user_id},
                ]
            },
            sort=[("created_at", -1)],
        )

    @staticmethod
    def _needs_connection_ping(last_message: Optional[Dict[str, Any]], now: datetime) -> bool:
        if not last_message:
            return True

        created_at = last_message.get("created_at")
        if isinstance(created_at, datetime):
            return (now - created_at) > timedelta(hours=18)

        return True

    @staticmethod
    def _build_message_prompt(
        *,
        user_id: str,
        style_summary: Optional[str],
        last_message: Optional[Dict[str, Any]],
        now: datetime,
    ) -> Dict[str, Any]:
        tone_hint = style_summary or "Keep it warm and genuine."

        if last_message and last_message.get("content"):
            recent_snippet = last_message["content"][:120]
            secondary_text = f'Last exchange: "{recent_snippet}"'
        else:
            secondary_text = "No recent messages detected."

        return {
            "id": str(uuid.uuid4()),
            "type": "message_draft",
            "title": "Send a quick note",
            "summary": "Start a conversation to keep the connection strong.",
            "confidence": 0.7,
            "generated_at": now.isoformat() + "Z",
            "payload": {
                "tone_hint": tone_hint,
                "secondary_text": secondary_text,
            },
        }

    @staticmethod
    def _get_daily_question_prompt(user_id: str) -> Optional[Dict[str, Any]]:
        today = datetime.utcnow().date().isoformat()
        record = mongo.db.daily_questions.find_one({"user_id": user_id, "date": today})

        if not record or record.get("answered"):
            return None

        question = record.get("question")
        if not question:
            return None

        return {
            "id": str(uuid.uuid4()),
            "type": "daily_question",
            "title": "Answer today’s reflection",
            "summary": question,
            "confidence": 0.6,
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "payload": {"question": question},
        }

    @staticmethod
    def _get_calendar_prompt(user_id: str, now: datetime) -> Optional[Dict[str, Any]]:
        upcoming = list(
            mongo.db.events.find(
                {
                    "user_id": user_id,
                    "start_time": {"$gte": now, "$lt": now + timedelta(days=7)},
                }
            ).sort("start_time", 1)
        )

        if upcoming:
            return None

        return {
            "id": str(uuid.uuid4()),
            "type": "calendar",
            "title": "Plan something together",
            "summary": "No shared plans in the next week. Consider scheduling a small event.",
            "confidence": 0.4,
            "generated_at": now.isoformat() + "Z",
            "payload": {"suggested_window": "next_7_days"},
        }

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
    def _get_cached_suggestions(user_id: str) -> Optional[List[Dict[str, Any]]]:
        collection = AgentSuggestionService._cache_collection()
        ttl = AgentSuggestionService._cache_ttl_hours()
        if collection is None or ttl <= 0:
            return None
        cutoff = datetime.utcnow() - timedelta(hours=ttl)
        doc = collection.find_one({"user_id": user_id, "created_at": {"$gte": cutoff}})
        if doc and isinstance(doc.get("suggestions"), list):
            return doc["suggestions"]
        return None

    @staticmethod
    def _store_cache(user_id: str, suggestions: List[Dict[str, Any]]) -> None:
        collection = AgentSuggestionService._cache_collection()
        if collection is None:
            return
        collection.update_one(
            {"user_id": user_id},
            {"$set": {"suggestions": suggestions, "created_at": datetime.utcnow()}},
            upsert=True,
        )
