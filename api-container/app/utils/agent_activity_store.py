from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional

from bson import ObjectId
from pymongo.collection import Collection
from pymongo.errors import DuplicateKeyError


class AgentActivityStore:
    """Persistence helper for agent activity events."""

    def __init__(self, collection: Collection):
        self.collection = collection
        self._ensure_indexes()

    def _ensure_indexes(self) -> None:
        # idempotent index creation; MongoDB ignores duplicates.
        self.collection.create_index([("user_id", 1), ("occurred_at", -1)])
        self.collection.create_index([("processed", 1), ("occurred_at", -1)])
        self.collection.create_index([("scenario", 1), ("occurred_at", -1)])
        self.collection.create_index([("dedupe_key", 1)], unique=True, sparse=True)

    def record_event(
        self,
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
        """Insert a new activity document, respecting optional dedupe keys."""
        now = datetime.utcnow()
        document: Dict[str, Any] = {
            "user_id": str(user_id),
            "event_type": event_type,
            "source": source,
            "scenario": scenario,
            "payload": payload,
            "metadata": metadata or {},
            "occurred_at": occurred_at or now,
            "recorded_at": now,
            "processed": False,
        }
        if dedupe_key:
            document["dedupe_key"] = dedupe_key

        if dedupe_key:
            existing = self.collection.find_one({"dedupe_key": dedupe_key})
            if existing:
                return self._format(existing)

        try:
            result = self.collection.insert_one(document)
            document["_id"] = result.inserted_id
            return self._format(document)
        except DuplicateKeyError:
            existing = self.collection.find_one({"dedupe_key": dedupe_key})
            return self._format(existing) if existing else self._format(document)

    def fetch_recent(
        self,
        *,
        limit: int = 100,
        since: Optional[datetime] = None,
        scenario: Optional[str] = None,
        include_processed: bool = False,
        user_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Return recent events ordered by most recent occurrence."""
        query: Dict[str, Any] = {}
        if user_id:
            query["user_id"] = str(user_id)
        if since:
            query["occurred_at"] = {"$gt": since}
        if scenario:
            query["scenario"] = scenario
        if not include_processed:
            query["processed"] = False

        cursor = (
            self.collection.find(query)
            .sort("occurred_at", -1)
            .limit(max(1, min(limit, 500)))
        )
        return [self._format(doc) for doc in cursor]

    def mark_processed(self, identifiers: Iterable[str]) -> int:
        """Flag events as processed by their string ObjectIds."""
        ids = [ObjectId(ident) for ident in identifiers]
        if not ids:
            return 0
        result = self.collection.update_many(
            {"_id": {"$in": ids}},
            {"$set": {"processed": True, "processed_at": datetime.utcnow()}},
        )
        return result.modified_count

    def prune_before(self, cutoff: datetime) -> int:
        """Delete stale events to keep the collection lean."""
        result = self.collection.delete_many({"occurred_at": {"$lt": cutoff}})
        return result.deleted_count

    @staticmethod
    def _format(document: Dict[str, Any]) -> Dict[str, Any]:
        doc = dict(document)
        doc["_id"] = str(doc.get("_id"))
        for key in ("occurred_at", "recorded_at", "processed_at"):
            value = doc.get(key)
            if isinstance(value, datetime):
                doc[key] = value.isoformat() + "Z"
        if doc.get("metadata") is None:
            doc["metadata"] = {}
        return doc


class MonitorCursorStore:
    """Persists incremental cursor positions for polling loops."""

    def __init__(self, collection: Collection):
        self.collection = collection
        self.collection.create_index("updated_at")

    def get_value(self, name: str) -> Optional[Any]:
        doc = self.collection.find_one({"_id": name})
        return doc.get("value") if doc else None

    def set_value(self, name: str, value: Any) -> None:
        self.collection.update_one(
            {"_id": name},
            {"$set": {"value": value, "updated_at": datetime.utcnow()}},
            upsert=True,
        )
