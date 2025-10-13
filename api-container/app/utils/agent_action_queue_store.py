from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional

from bson import ObjectId
from pymongo.collection import Collection


class AgentActionQueueStore:
    """Backs the agent action queue collection with shared helpers."""

    def __init__(self, collection: Collection):
        self.collection = collection
        self.collection.create_index([("user_id", 1), ("created_at", -1)])
        self.collection.create_index([("status", 1), ("created_at", -1)])

    def enqueue(self, plans: List[Dict[str, Any]]) -> List[str]:
        if not plans:
            return []
        now = datetime.utcnow()
        documents: List[Dict[str, Any]] = []
        for plan in plans:
            doc = dict(plan)
            doc.setdefault("status", "pending")
            doc.setdefault("created_at", now)
            doc.setdefault("updated_at", now)
            documents.append(doc)
        result = self.collection.insert_many(documents)
        return [str(identifier) for identifier in result.inserted_ids]

    def list_pending(
        self,
        *,
        user_id: str,
        limit: int = 20,
        include_completed: bool = False,
    ) -> List[Dict[str, Any]]:
        query: Dict[str, Any] = {"user_id": user_id}
        if not include_completed:
            query["status"] = "pending"
        cursor = (
            self.collection.find(query)
            .sort("created_at", -1)
            .limit(max(1, min(limit, 100)))
        )
        return [self._format(doc) for doc in cursor]

    def update_status(
        self,
        identifiers: Iterable[str],
        *,
        status: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        ids = [ObjectId(ident) for ident in identifiers]
        if not ids:
            return 0
        update_doc: Dict[str, Any] = {
            "status": status,
            "updated_at": datetime.utcnow(),
        }
        if metadata:
            update_doc["metadata"] = metadata
        result = self.collection.update_many(
            {"_id": {"$in": ids}},
            {"$set": update_doc},
        )
        return result.modified_count

    def get_action(self, identifier: str) -> Optional[Dict[str, Any]]:
        try:
            object_id = ObjectId(identifier)
        except Exception:
            return None
        doc = self.collection.find_one({"_id": object_id})
        if not doc:
            return None
        return self._format(doc)

    @staticmethod
    def _format(document: Dict[str, Any]) -> Dict[str, Any]:
        doc = dict(document)
        doc["_id"] = str(doc.get("_id"))
        for field in ("created_at", "updated_at"):
            value = doc.get(field)
            if isinstance(value, datetime):
                doc[field] = value.isoformat() + "Z"
        return doc
