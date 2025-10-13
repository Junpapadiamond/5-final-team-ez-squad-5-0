from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional

from .. import mongo
from ..utils.agent_activity_store import AgentActivityStore


class AgentActivityService:
    """High-level facade around agent activity persistence."""

    @staticmethod
    def _store() -> AgentActivityStore:
        collection = mongo.db.agent_activity
        return AgentActivityStore(collection)

    @staticmethod
    def record_event(
        *,
        user_id: str,
        event_type: str,
        source: str,
        payload: Dict[str, Any],
        scenario: Optional[str] = None,
        dedupe_key: Optional[str] = None,
        occurred_at: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        store = AgentActivityService._store()
        return store.record_event(
            user_id=user_id,
            event_type=event_type,
            source=source,
            payload=payload,
            scenario=scenario,
            dedupe_key=dedupe_key,
            occurred_at=occurred_at,
            metadata=metadata,
        )

    @staticmethod
    def fetch_recent(
        *,
        limit: int = 100,
        since: Optional[datetime] = None,
        scenario: Optional[str] = None,
        include_processed: bool = False,
    ) -> List[Dict[str, Any]]:
        store = AgentActivityService._store()
        return store.fetch_recent(
            limit=limit,
            since=since,
            scenario=scenario,
            include_processed=include_processed,
        )

    @staticmethod
    def mark_processed(identifiers: Iterable[str]) -> int:
        store = AgentActivityService._store()
        return store.mark_processed(identifiers)

    @staticmethod
    def prune_stale(days: int = 30) -> int:
        from datetime import timedelta

        cutoff = datetime.utcnow() - timedelta(days=max(1, days))
        store = AgentActivityService._store()
        return store.prune_before(cutoff)
