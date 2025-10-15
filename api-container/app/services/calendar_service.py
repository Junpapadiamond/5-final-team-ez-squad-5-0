from datetime import datetime
from typing import List, Tuple, Optional, Dict, Any
from bson import ObjectId

from .. import mongo
from .agent_activity_service import AgentActivityService


class CalendarService:
    """Service layer for coordinating shared calendar data."""

    @staticmethod
    def _get_user(user_id: str) -> Optional[Dict[str, Any]]:
        try:
            user = mongo.db.users.find_one({"_id": ObjectId(user_id)})
            if user:
                user["_id"] = str(user["_id"])
            return user
        except Exception:
            return None

    @staticmethod
    def get_events_for_month(user_id: str, year: Optional[int], month: Optional[int]) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        try:
            user = CalendarService._get_user(user_id)
            if not user:
                return None, "User not found"

            user_ids: List[str] = [user_id]

            partner_id = user.get("partner_id")
            partner_status = user.get("partner_status")
            if partner_id and partner_status == "connected":
                user_ids.append(partner_id)

            match_stage: Dict[str, Any] = {"user_id": {"$in": user_ids}}

            if year and month:
                # Handle both new (date field) and legacy (start_time) records
                start_of_month = datetime(year, month, 1)
                if month == 12:
                    end_of_month = datetime(year + 1, 1, 1)
                else:
                    end_of_month = datetime(year, month + 1, 1)

                match_stage["$or"] = [
                    {
                        "start_time": {
                            "$gte": start_of_month,
                            "$lt": end_of_month,
                        }
                    },
                    {
                        "date": {
                            "$gte": start_of_month.strftime("%Y-%m-%d"),
                            "$lt": end_of_month.strftime("%Y-%m-%d"),
                        }
                    },
                ]

            events = list(
                mongo.db.events.find(match_stage).sort("start_time", 1)
            )

            formatted_events: List[Dict[str, Any]] = []
            user_cache: Dict[str, Optional[Dict[str, Any]]] = {}

            def get_user_cached(target_user_id: str) -> Optional[Dict[str, Any]]:
                if target_user_id not in user_cache:
                    user_cache[target_user_id] = CalendarService._get_user(target_user_id)
                return user_cache[target_user_id]

            for event in events:
                creator_id = event.get("creator_id") or event.get("user_id")
                creator = get_user_cached(creator_id)

                # Support legacy events that only stored start_time
                start_time = event.get("start_time")
                event_date = event.get("date")
                event_time = event.get("time")

                if start_time and isinstance(start_time, datetime):
                    event_date = event_date or start_time.strftime("%Y-%m-%d")
                    event_time = event_time or start_time.strftime("%H:%M")

                formatted_events.append(
                    {
                        "_id": str(event["_id"]),
                        "title": event.get("title", ""),
                        "description": event.get("description", ""),
                        "date": event_date,
                        "time": event_time,
                        "creator_id": creator_id,
                        "creator_name": (creator or {}).get("name", "You"),
                    }
                )

            return {"events": formatted_events}, None

        except Exception as exc:
            return None, f"Failed to load events: {str(exc)}"

    @staticmethod
    def create_event(
        user_id: str,
        title: str,
        date_str: str,
        time_str: str,
        description: Optional[str] = None,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        try:
            user = CalendarService._get_user(user_id)
            if not user:
                return None, "User not found"

            if not title:
                return None, "Title is required"

            if not date_str or not time_str:
                return None, "Date and time are required"

            try:
                # Build a naive datetime to preserve compatibility with the worker
                start_time = datetime.fromisoformat(f"{date_str}T{time_str}:00")
            except ValueError:
                return None, "Invalid date or time format"

            event_doc = {
                "title": title,
                "description": description or "",
                "date": date_str,
                "time": time_str,
                "start_time": start_time,
                "user_id": user_id,
                "creator_id": user_id,
                "creator_name": user.get("name", ""),
                "created_at": datetime.utcnow(),
            }

            result = mongo.db.events.insert_one(event_doc)
            event_doc["_id"] = str(result.inserted_id)

            partner_id = user.get("partner_id") if user.get("partner_status") == "connected" else None

            try:
                payload = {
                    "event_id": event_doc["_id"],
                    "title": title,
                    "date": date_str,
                    "time": time_str,
                }
                AgentActivityService.record_event(
                    user_id=user_id,
                    event_type="calendar_event_created",
                    source="calendar_service",
                    scenario="anniversary_planning",
                    payload=payload,
                    dedupe_key=f"calendar-event:{event_doc['_id']}",
                    occurred_at=event_doc["created_at"],
                )
                if partner_id:
                    AgentActivityService.record_event(
                        user_id=partner_id,
                        event_type="partner_calendar_event_created",
                        source="calendar_service",
                        scenario="anniversary_planning",
                        payload={**payload, "creator_id": user_id},
                        dedupe_key=f"calendar-event:{event_doc['_id']}:partner:{partner_id}",
                        occurred_at=event_doc["created_at"],
                    )
            except Exception:
                pass

            return {
                "message": "Event created successfully",
                "event": {
                    "_id": event_doc["_id"],
                    "title": event_doc["title"],
                    "description": event_doc["description"],
                    "date": event_doc["date"],
                    "time": event_doc["time"],
                    "creator_id": event_doc["creator_id"],
                    "creator_name": event_doc["creator_name"],
                },
            }, None

        except Exception as exc:
            return None, f"Failed to create event: {str(exc)}"
