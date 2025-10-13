from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

from .. import mongo


class AgentFeedbackService:
    """Captures user ratings or comments on agent actions."""

    @staticmethod
    def _collection():
        collection = mongo.db.agent_feedback
        collection.create_index([("user_id", 1), ("created_at", -1)])
        collection.create_index("action_id")
        return collection

    @classmethod
    def record_feedback(
        cls,
        *,
        user_id: str,
        action_id: str,
        feedback: Dict[str, Any],
    ) -> str:
        doc = {
            "user_id": user_id,
            "action_id": action_id,
            "feedback": feedback,
            "created_at": datetime.utcnow(),
        }
        result = cls._collection().insert_one(doc)
        return str(result.inserted_id)
