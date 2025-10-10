from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from .. import mongo
from .style_profile_service import StyleProfileService


class AgentSuggestionService:
    """Generates lightweight, rule-based suggestions pending full agent automation."""

    @staticmethod
    def get_suggestions(user_id: str) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        try:
            now = datetime.utcnow()
            suggestions: List[Dict[str, Any]] = []

            style_profile, _ = StyleProfileService.get_style_profile(
                user_id, cache_ttl_hours=6
            )
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

            return suggestions, None
        except Exception as exc:  # pragma: no cover - defensive
            return [], f"Failed to generate suggestions: {str(exc)}"

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
        record = mongo.db.daily_questions.find_one(
            {"user_id": user_id, "date": today}
        )

        if not record:
            return None

        if record.get("answered"):
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
