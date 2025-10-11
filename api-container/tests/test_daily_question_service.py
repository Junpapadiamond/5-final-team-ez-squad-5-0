from datetime import datetime, timedelta
from types import SimpleNamespace

from bson import ObjectId

from app.services.daily_question_service import DailyQuestionService


def test_get_answers_includes_partner(monkeypatch):
    today = datetime.utcnow().date().isoformat()
    user_id = str(ObjectId())
    partner_id = str(ObjectId())

    user_entry = {
        "_id": ObjectId(),
        "user_id": user_id,
        "question": "What made you smile today?",
        "answer": "Sunrise walk",
        "answered": True,
        "answered_at": datetime.utcnow(),
        "date": today,
    }
    partner_entry = {
        "_id": ObjectId(),
        "user_id": partner_id,
        "question": "What made you smile today?",
        "answer": "Your message",
        "answered": True,
        "answered_at": datetime.utcnow() - timedelta(minutes=5),
        "date": today,
    }

    user_doc = {"_id": ObjectId(user_id), "name": "You", "partner_id": partner_id}
    partner_doc = {"_id": ObjectId(partner_id), "name": "Partner", "partner_id": user_id}

    def find_one_daily(query):
        if query["user_id"] == user_id:
            return user_entry
        if query["user_id"] == partner_id:
            return partner_entry
        return None

    def find_one_users(query):
        target_id = query.get("_id")
        if target_id == ObjectId(user_id):
            return user_doc
        if target_id == ObjectId(partner_id):
            return partner_doc
        return None

    mongo_stub = SimpleNamespace(
        db=SimpleNamespace(
            daily_questions=SimpleNamespace(find_one=find_one_daily),
            users=SimpleNamespace(find_one=find_one_users),
        )
    )

    monkeypatch.setattr("app.services.daily_question_service.mongo", mongo_stub)

    result = DailyQuestionService.get_answers(user_id)

    assert result["question"]["question"] == "What made you smile today?"
    assert result["your_answer"]["answer"] == "Sunrise walk"
    assert result["partner_answer"]["user_name"] == "Partner"
    assert result["both_answered"] is True


def test_unanswered_entries_are_hidden(monkeypatch):
    today = datetime.utcnow().date().isoformat()
    user_id = str(ObjectId())

    unanswered_entry = {
        "_id": ObjectId(),
        "user_id": user_id,
        "question": "What made you smile today?",
        "answered": False,
        "answer": None,
        "date": today,
    }

    mongo_stub = SimpleNamespace(
        db=SimpleNamespace(
            daily_questions=SimpleNamespace(
                find_one=lambda query: unanswered_entry if query["user_id"] == user_id else None
            ),
            users=SimpleNamespace(find_one=lambda query: {"_id": ObjectId(user_id), "name": "You"}),
        )
    )

    monkeypatch.setattr("app.services.daily_question_service.mongo", mongo_stub)

    result = DailyQuestionService.get_answers(user_id)

    assert result["your_answer"] is None
    assert result["both_answered"] is False
