from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timedelta
from typing import Dict, Optional

from bson import ObjectId
from pymongo import MongoClient

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from app.utils.agent_activity_store import AgentActivityStore, MonitorCursorStore

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("agent_activity_worker")

MONGO_URI = os.environ.get("MONGO_URI", "mongodb://db:27017/together")
CHECK_INTERVAL_SECONDS = int(os.environ.get("AGENT_ACTIVITY_POLL_INTERVAL", "60"))
CALENDAR_GAP_CHECK_INTERVAL_HOURS = int(
    os.environ.get("AGENT_CALENDAR_GAP_CHECK_HOURS", "6")
)
DAILY_MISS_THRESHOLD_HOURS = int(
    os.environ.get("AGENT_DAILY_MISS_THRESHOLD_HOURS", "24")
)

client = MongoClient(MONGO_URI)
db = client.get_database()

activity_store = AgentActivityStore(db.agent_activity)
cursor_store = MonitorCursorStore(db.agent_monitor_cursors)


def _to_iso(dt: datetime) -> str:
    return dt.isoformat() + "Z"


def _record_message_events(message: Dict) -> None:
    message_id = str(message["_id"])
    sender_id = str(message.get("sender_id"))
    receiver_id = str(message.get("receiver_id"))
    occurred_at = message.get("created_at")
    if not isinstance(occurred_at, datetime):
        occurred_at = message["_id"].generation_time

    snippet = str(message.get("content", "") or "").strip()
    if len(snippet) > 160:
        snippet = snippet[:157] + "..."

    payload = {
        "message_id": message_id,
        "preview": snippet,
        "sender_id": sender_id,
        "receiver_id": receiver_id,
    }

    if sender_id:
        activity_store.record_event(
            user_id=sender_id,
            event_type="message_sent",
            source="messages",
            scenario="daily_check_in",
            payload=payload,
            dedupe_key=f"msg:{message_id}:sender",
            occurred_at=occurred_at,
        )

    if receiver_id:
        activity_store.record_event(
            user_id=receiver_id,
            event_type="message_received",
            source="messages",
            scenario="daily_check_in",
            payload=payload,
            dedupe_key=f"msg:{message_id}:receiver",
            occurred_at=occurred_at,
        )


def process_new_messages() -> None:
    last_value = cursor_store.get_value("messages:last_id")
    query = {}
    if last_value:
        try:
            query["_id"] = {"$gt": ObjectId(last_value)}
        except Exception:
            logger.warning("Invalid last message cursor %s; ignoring", last_value)
    cursor = db.messages.find(query).sort("_id", 1).limit(500)

    last_processed_id: Optional[ObjectId] = None
    for message in cursor:
        _record_message_events(message)
        last_processed_id = message["_id"]

    if last_processed_id:
        cursor_store.set_value("messages:last_id", str(last_processed_id))


def process_quiz_completions() -> None:
    last_completed = cursor_store.get_value("quiz:last_completed_at")
    query: Dict = {"status": "completed"}
    if last_completed:
        try:
            last_dt = datetime.fromisoformat(last_completed.replace("Z", ""))
            query["completed_at"] = {"$gt": last_dt}
        except ValueError:
            logger.warning("Invalid quiz cursor %s; ignoring", last_completed)
    cursor = db.quiz_sessions.find(query).sort("completed_at", 1).limit(200)

    latest_seen: Optional[datetime] = None
    for session in cursor:
        completed_at = session.get("completed_at")
        if not isinstance(completed_at, datetime):
            continue
        user_ids = [str(uid) for uid in session.get("user_ids", []) if uid]
        summary = session.get("compatibility_summary", {})
        payload = {
            "session_id": str(session.get("_id")),
            "score": summary.get("score"),
            "matches": summary.get("matches"),
            "total": summary.get("total"),
        }
        for user_id in user_ids:
            activity_store.record_event(
                user_id=user_id,
                event_type="quiz_completed",
                source="quiz_sessions",
                scenario="quiz_follow_up",
                payload=payload,
                dedupe_key=f"quiz:{session['_id']}:{user_id}",
                occurred_at=completed_at,
            )
        latest_seen = completed_at

    if latest_seen:
        cursor_store.set_value("quiz:last_completed_at", _to_iso(latest_seen))


def process_daily_question_misses() -> None:
    threshold = datetime.utcnow() - timedelta(hours=DAILY_MISS_THRESHOLD_HOURS)
    threshold_date = threshold.date().isoformat()
    records = db.daily_questions.find(
        {
            "answered": False,
            "date": {"$lte": threshold_date},
        }
    )

    for record in records:
        user_id = record.get("user_id")
        if not user_id:
            continue
        dedupe_key = f"daily-miss:{user_id}:{record.get('date')}"
        payload = {
            "question": record.get("question"),
            "date": record.get("date"),
        }
        occurred_at = record.get("created_at")
        if not isinstance(occurred_at, datetime):
            try:
                occurred_at = datetime.fromisoformat(f"{record.get('date')}T00:00:00")
            except Exception:
                occurred_at = threshold
        activity_store.record_event(
            user_id=user_id,
            event_type="daily_question_missed",
            source="daily_questions",
            scenario="daily_check_in",
            payload=payload,
            dedupe_key=dedupe_key,
            occurred_at=occurred_at,
        )


def process_calendar_gaps() -> None:
    now = datetime.utcnow()
    last_run_iso = cursor_store.get_value("calendar:last_check_at")
    if last_run_iso:
        try:
            last_run = datetime.fromisoformat(last_run_iso.replace("Z", ""))
            if now - last_run < timedelta(hours=CALENDAR_GAP_CHECK_INTERVAL_HOURS):
                return
        except ValueError:
            logger.warning("Invalid calendar cursor %s; continuing", last_run_iso)

    window_end = now + timedelta(days=7)
    users_cursor = db.users.find({}, {"_id": 1})
    for user in users_cursor:
        user_id = str(user["_id"])
        has_upcoming = db.events.find_one(
            {
                "user_id": user_id,
                "start_time": {"$gte": now, "$lt": window_end},
            }
        )
        if has_upcoming:
            continue

        dedupe_key = f"calendar-gap:{user_id}:{now.strftime('%Y-%m-%d')}"
        payload = {
            "gap_window_start": _to_iso(now),
            "gap_window_end": _to_iso(window_end),
        }
        activity_store.record_event(
            user_id=user_id,
            event_type="calendar_gap_detected",
            source="events",
            scenario="anniversary_planning",
            payload=payload,
            dedupe_key=dedupe_key,
            occurred_at=now,
        )

    cursor_store.set_value("calendar:last_check_at", _to_iso(now))


def run_monitor_loop() -> None:
    logger.info("Starting agent activity monitor loop")
    while True:
        try:
            process_new_messages()
            process_quiz_completions()
            process_daily_question_misses()
            process_calendar_gaps()
        except Exception as exc:
            logger.exception("Agent activity loop error: %s", exc)
        time.sleep(max(10, CHECK_INTERVAL_SECONDS))


if __name__ == "__main__":
    run_monitor_loop()
