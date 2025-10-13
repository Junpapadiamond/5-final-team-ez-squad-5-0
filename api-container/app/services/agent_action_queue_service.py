from __future__ import annotations

from datetime import datetime
from typing import Dict, Iterable, List, Optional

from .. import mongo
from ..utils.agent_action_queue_store import AgentActionQueueStore


class AgentActionQueueService:
    """Persistence helper for pending agent action plans."""

    @staticmethod
    def _collection():
        collection = mongo.db.agent_action_queue
        return AgentActionQueueStore(collection)

    @classmethod
    def enqueue(cls, plans: List[Dict[str, any]]) -> List[str]:
        store = cls._collection()
        return store.enqueue(plans)

    @classmethod
    def list_pending(
        cls,
        *,
        user_id: str,
        limit: int = 20,
        include_completed: bool = False,
    ) -> List[Dict[str, any]]:
        store = cls._collection()
        return store.list_pending(
            user_id=user_id,
            limit=limit,
            include_completed=include_completed,
        )

    @classmethod
    def update_status(
        cls,
        identifiers: Iterable[str],
        *,
        status: str,
        metadata: Optional[Dict[str, any]] = None,
    ) -> int:
        store = cls._collection()
        return store.update_status(identifiers, status=status, metadata=metadata)

    @classmethod
    def get_action(cls, action_id: str) -> Optional[Dict[str, any]]:
        store = cls._collection()
        return store.get_action(action_id)
