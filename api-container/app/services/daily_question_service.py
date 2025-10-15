from datetime import datetime, date
from typing import Any, Dict, Optional
from bson import ObjectId
import random

from .. import mongo
from .agent_activity_service import AgentActivityService


class DailyQuestionService:

    # Sample questions for daily questions feature
    DAILY_QUESTIONS = [
        "What made you smile today?",
        "What are you most grateful for right now?",
        "What's one thing you learned today?",
        "How did you show love today?",
        "What's something you're looking forward to?",
        "What made you feel proud today?",
        "How did you take care of yourself today?",
        "What's one way you helped someone today?",
        "What's the best part of your day so far?",
        "What's something new you tried recently?",
        "How did you and your partner connect today?",
        "What's one thing you appreciate about your relationship?",
        "What goal are you working towards together?",
        "How did you support each other today?",
        "What's a happy memory you made recently?"
    ]

    @staticmethod
    def get_today_question(user_id):
        try:
            today = date.today().isoformat()

            # Check if user already has a question for today
            existing_question = mongo.db.daily_questions.find_one({
                "user_id": user_id,
                "date": today
            })

            if existing_question:
                return {
                    "question": existing_question["question"],
                    "date": existing_question["date"],
                    "answered": existing_question.get("answered", False),
                    "answer": existing_question.get("answer")
                }, None

            # Generate a new question for today
            # Use date as seed for consistent daily questions
            random.seed(today + user_id)
            question = random.choice(DailyQuestionService.DAILY_QUESTIONS)

            # Save the question
            question_doc = {
                "user_id": user_id,
                "question": question,
                "date": today,
                "answered": False,
                "created_at": datetime.utcnow()
            }

            mongo.db.daily_questions.insert_one(question_doc)

            return {
                "question": question,
                "date": today,
                "answered": False,
                "answer": None
            }, None

        except Exception as e:
            return None, f"Failed to get daily question: {str(e)}"

    @staticmethod
    def submit_answer(user_id, answer):
        try:
            today = date.today().isoformat()

            # Find today's question
            question = mongo.db.daily_questions.find_one({
                "user_id": user_id,
                "date": today
            })

            if not question:
                return None, "No question found for today"

            # Update with answer
            mongo.db.daily_questions.update_one(
                {"user_id": user_id, "date": today},
                {
                    "$set": {
                        "answer": answer,
                        "answered": True,
                        "answered_at": datetime.utcnow()
                    }
                }
            )

            try:
                AgentActivityService.record_event(
                    user_id=user_id,
                    event_type="daily_question_answered",
                    source="daily_question_service",
                    scenario="daily_check_in",
                    payload={
                        "question": question["question"],
                        "answer": answer,
                        "date": today,
                    },
                    dedupe_key=f"daily-answer:{user_id}:{today}",
                )
            except Exception:
                pass

            return {
                "message": "Answer submitted successfully",
                "question": question["question"],
                "answer": answer,
                "date": today
            }, None

        except Exception as e:
            return None, f"Failed to submit answer: {str(e)}"

    @staticmethod
    def get_answers(user_id: str) -> Dict[str, Any]:
        today = date.today().isoformat()

        user_doc = DailyQuestionService._get_user(user_id)
        partner_id = (user_doc or {}).get("partner_id")

        user_entry = mongo.db.daily_questions.find_one({"user_id": user_id, "date": today})
        partner_entry = (
            mongo.db.daily_questions.find_one({"user_id": partner_id, "date": today})
            if partner_id
            else None
        )

        partner_doc = DailyQuestionService._get_user(partner_id) if partner_id else None

        question_entry = user_entry or partner_entry
        question_payload = (
            {
                "question": question_entry.get("question"),
                "date": question_entry.get("date"),
            }
            if question_entry
            else None
        )

        your_answer = DailyQuestionService._format_answer(user_entry, user_doc)
        partner_answer = DailyQuestionService._format_answer(partner_entry, partner_doc)

        return {
            "question": question_payload,
            "your_answer": your_answer,
            "partner_answer": partner_answer,
            "both_answered": bool(your_answer and your_answer.get("answered")) and bool(
                partner_answer and partner_answer.get("answered")
            ),
        }

    @staticmethod
    def _get_user(user_id: Optional[str]) -> Optional[Dict[str, Any]]:
        if not user_id:
            return None
        try:
            doc = mongo.db.users.find_one({"_id": ObjectId(user_id)})
            if doc:
                doc["_id"] = str(doc["_id"])
            return doc
        except Exception:
            return None

    @staticmethod
    def _format_answer(entry: Optional[Dict[str, Any]], user_doc: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if not entry:
            return None

        answered_flag = entry.get("answered", bool(entry.get("answer")))
        if not answered_flag and not entry.get("answer"):
            return None

        answered_at_value = entry.get("answered_at")
        if isinstance(answered_at_value, datetime):
            answered_at_iso = answered_at_value.isoformat() + "Z"
        elif isinstance(answered_at_value, str):
            answered_at_iso = answered_at_value
        else:
            answered_at_iso = None

        question_date = entry.get("date")

        return {
            "_id": str(entry.get("_id")),
            "user_id": entry.get("user_id"),
            "user_name": (user_doc or {}).get("name"),
            "question": entry.get("question"),
            "answer": entry.get("answer"),
            "answered": answered_flag,
            "answered_at": answered_at_iso,
            "question_date": question_date,
            "date": answered_at_iso or question_date,
        }
