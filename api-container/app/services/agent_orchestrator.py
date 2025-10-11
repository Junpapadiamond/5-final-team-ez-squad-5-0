from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from bson import ObjectId

from .. import mongo
from .agent_llm_client import AgentLLMClient
from .style_profile_service import StyleProfileService


class AgentOrchestrator:
    """Central coordinator for Together Agent LLM calls and context assembly."""

    @staticmethod
    def build_context(user_id: str) -> Dict[str, Any]:
        context: Dict[str, Any] = {}
        context["partner_status"] = AgentOrchestrator._partner_status(user_id)
        context["style_profile"] = AgentOrchestrator._style_profile(user_id)
        context["daily_question"] = AgentOrchestrator._daily_question(user_id)
        context["recent_messages"] = AgentOrchestrator._recent_messages(user_id)
        context["upcoming_events"] = AgentOrchestrator._upcoming_events(user_id)
        return context

    @staticmethod
    def analyze_tone(user_id: str, message: str) -> Optional[Dict[str, Any]]:
        context = AgentOrchestrator.build_context(user_id)
        return AgentLLMClient.analyze_tone(message, context)

    @staticmethod
    def plan_coaching(user_id: str) -> Optional[List[Dict[str, Any]]]:
        context = AgentOrchestrator.build_context(user_id)
        cards = AgentLLMClient.plan_coaching(context)
        if cards is None:
            return None
        # Ensure each card has an id; fallback to generated timestamp if missing.
        now = datetime.utcnow().isoformat() + "Z"
        for idx, card in enumerate(cards):
            card.setdefault("id", f"{user_id}-llm-{idx}-{now}")
        return list(cards)

    @staticmethod
    def style_summary_from_llm(user_id: str, samples: List[str]) -> Optional[Dict[str, Any]]:
        if not samples:
            return None
        context = {"message_samples": samples}
        return AgentLLMClient.summarize_style(context)

    @staticmethod
    def _partner_status(user_id: str) -> str:
        try:
            user = mongo.db.users.find_one({"_id": ObjectId(user_id)}, {"partner_status": 1})
        except Exception:
            return "unknown"
        if not user:
            return "unknown"
        return user.get("partner_status", "unknown")

    @staticmethod
    def _style_profile(user_id: str) -> Dict[str, Any]:
        profile, _ = StyleProfileService.get_style_profile(user_id, cache_ttl_hours=6)
        return profile or {}

    @staticmethod
    def _daily_question(user_id: str) -> Optional[Dict[str, Any]]:
        try:
            today = datetime.utcnow().date().isoformat()
            record = mongo.db.daily_questions.find_one({"user_id": user_id, "date": today})
            if not record:
                return None
            partner_answer = None
            if record.get("partner_id"):
                partner_answer = record.get("partner_answer")
            return {
                "question": record.get("question"),
                "your_answer": record.get("answer"),
                "partner_answer": partner_answer,
                "answered": record.get("answered"),
            }
        except Exception:
            return None

    @staticmethod
    def _recent_messages(user_id: str) -> List[Dict[str, Any]]:
        try:
            cursor = mongo.db.messages.find(
                {
                    "$or": [
                        {"sender_id": user_id},
                        {"receiver_id": user_id},
                    ]
                }
            ).sort("created_at", -1).limit(10)
            messages: List[Dict[str, Any]] = []
            for doc in cursor:
                content = str(doc.get("content", "")).strip()
                if not content:
                    continue
                if len(content) > 220:
                    content = content[:217] + "..."
                messages.append(
                    {
                        "author": "You" if doc.get("sender_id") == user_id else "Partner",
                        "content": content,
                        "created_at": AgentOrchestrator._format_datetime(doc.get("created_at")),
                    }
                )
            return messages[:3]
        except Exception:
            return []

    @staticmethod
    def _upcoming_events(user_id: str) -> List[Dict[str, Any]]:
        try:
            now = datetime.utcnow()
            window = now + timedelta(days=7)
            cursor = mongo.db.events.find(
                {
                    "user_id": user_id,
                    "start_time": {"$gte": now, "$lte": window},
                }
            ).sort("start_time", 1).limit(5)
            events: List[Dict[str, Any]] = []
            for event in cursor:
                title = str(event.get("title", "Shared plan")).strip() or "Shared plan"
                if len(title) > 120:
                    title = title[:117] + "..."
                events.append(
                    {
                        "title": title,
                        "start_time": AgentOrchestrator._format_datetime(event.get("start_time")),
                    }
                )
            return events[:3]
        except Exception:
            return []

    @staticmethod
    def _format_datetime(value: Any) -> Optional[str]:
        if isinstance(value, datetime):
            return value.isoformat() + "Z"
        if isinstance(value, str):
            return value
        return None
