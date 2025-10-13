from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from .. import mongo


class AgentAuditService:
    """Stores audit records for automated or assisted agent actions."""

    @staticmethod
    def _collection():
        collection = mongo.db.agent_audit
        collection.create_index([("user_id", 1), ("created_at", -1)])
        collection.create_index("action_id")
        return collection

    @classmethod
    def log(
        cls,
        *,
        user_id: str,
        action_id: Optional[str],
        action_type: str,
        status: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        doc = {
            "user_id": user_id,
            "action_id": action_id,
            "action_type": action_type,
            "status": status,
            "metadata": metadata or {},
            "created_at": datetime.utcnow(),
        }
        result = cls._collection().insert_one(doc)
        return str(result.inserted_id)
