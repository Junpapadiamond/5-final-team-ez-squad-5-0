import random
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from bson import ObjectId

from .. import mongo


class QuizService:
    """Service logic for compatibility quiz sessions shared by partners."""

    DEFAULT_BATCH_SIZES = [10, 15, 20]

    COMPATIBILITY_QUESTIONS: List[Dict[str, Any]] = [
        {"id": 101, "question": "Coffee or tea to start the day?", "options": ["Coffee", "Tea"], "category": "food"},
        {"id": 102, "question": "Beach vacation or mountain escape?", "options": ["Beach vacation", "Mountain escape"], "category": "travel"},
        {"id": 103, "question": "Are you an early bird or a night owl?", "options": ["Early bird", "Night owl"], "category": "lifestyle"},
        {"id": 104, "question": "Preferred Friday night plan?", "options": ["Stay in", "Go out"], "category": "lifestyle"},
        {"id": 105, "question": "Home-cooked meal or dining out?", "options": ["Cook at home", "Eat out"], "category": "food"},
        {"id": 106, "question": "How do you like to communicate?", "options": ["Phone call", "Text message"], "category": "communication"},
        {"id": 107, "question": "Dogs or cats?", "options": ["Dogs", "Cats"], "category": "pets"},
        {"id": 108, "question": "City skyline or countryside views?", "options": ["City life", "Countryside"], "category": "travel"},
        {"id": 109, "question": "Morning workouts or evening workouts?", "options": ["Morning", "Evening"], "category": "wellness"},
        {"id": 110, "question": "Netflix marathon or outdoor adventure?", "options": ["Streaming marathon", "Outdoor adventure"], "category": "leisure"},
        {"id": 111, "question": "Sweet snacks or salty snacks?", "options": ["Sweet", "Salty"], "category": "food"},
        {"id": 112, "question": "Board games or video games?", "options": ["Board games", "Video games"], "category": "leisure"},
        {"id": 113, "question": "Concert or theater performance?", "options": ["Concert", "Theater"], "category": "entertainment"},
        {"id": 114, "question": "Summer sunshine or winter coziness?", "options": ["Summer", "Winter"], "category": "seasons"},
        {"id": 115, "question": "Comedy movies or drama movies?", "options": ["Comedy", "Drama"], "category": "entertainment"},
        {"id": 116, "question": "Save money or spend on experiences?", "options": ["Save", "Spend on experiences"], "category": "finance"},
        {"id": 117, "question": "Road trip or fly to the destination?", "options": ["Road trip", "Fly"], "category": "travel"},
        {"id": 118, "question": "Read a book or listen to a podcast?", "options": ["Read a book", "Listen to a podcast"], "category": "learning"},
        {"id": 119, "question": "Cook together or order takeout?", "options": ["Cook together", "Order takeout"], "category": "food"},
        {"id": 120, "question": "Celebrate big or keep it low-key?", "options": ["Big celebration", "Low-key celebration"], "category": "traditions"},
        {"id": 121, "question": "Sleep in or start weekends early?", "options": ["Sleep in", "Start early"], "category": "lifestyle"},
        {"id": 122, "question": "Shared calendar or spontaneous plans?", "options": ["Shared calendar", "Spontaneous"], "category": "organization"},
        {"id": 123, "question": "Try new restaurant or revisit a favorite?", "options": ["Try something new", "Stick with a favorite"], "category": "food"},
        {"id": 124, "question": "DIY gifts or store-bought surprises?", "options": ["DIY gifts", "Store-bought"], "category": "gifts"},
        {"id": 125, "question": "Workout together or cheer each other on?", "options": ["Exercise together", "Encourage from afar"], "category": "wellness"},
        {"id": 126, "question": "Public displays of affection?", "options": ["Love them", "Keep it private"], "category": "affection"},
        {"id": 127, "question": "Surprise parties: yay or nay?", "options": ["Absolutely", "I'd rather know"], "category": "traditions"},
        {"id": 128, "question": "Long heartfelt texts or quick check-ins?", "options": ["Long texts", "Quick check-ins"], "category": "communication"},
        {"id": 129, "question": "Plan finances monthly or quarterly?", "options": ["Monthly", "Quarterly"], "category": "finance"},
        {"id": 130, "question": "Relaxing day: spa or adventurous outing?", "options": ["Spa day", "Adventure outing"], "category": "leisure"},
        {"id": 131, "question": "Ideal celebration: intimate dinner or group gathering?", "options": ["Intimate dinner", "Group gathering"], "category": "traditions"},
        {"id": 132, "question": "Holiday getaway: snowy cabin or tropical island?", "options": ["Snowy cabin", "Tropical island"], "category": "travel"},
        {"id": 133, "question": "Weekend project: gardening or home upgrade?", "options": ["Gardening", "Home improvement"], "category": "home"},
        {"id": 134, "question": "Preferred gift: experience or something tangible?", "options": ["Experience", "Tangible gift"], "category": "gifts"},
        {"id": 135, "question": "Handle conflict immediately or take time to cool off?", "options": ["Talk it out now", "Take time first"], "category": "communication"},
        {"id": 136, "question": "Which sounds better for Sunday afternoon?", "options": ["Brunch out", "Lazy day in"], "category": "lifestyle"},
        {"id": 137, "question": "Organize closet or organize digital photos?", "options": ["Closet", "Digital photos"], "category": "organization"},
        {"id": 138, "question": "Romantic gesture: handwritten note or surprise outing?", "options": ["Handwritten note", "Surprise outing"], "category": "affection"},
        {"id": 139, "question": "Choose a creative date: paint night or cooking class?", "options": ["Paint night", "Cooking class"], "category": "leisure"},
        {"id": 140, "question": "Evening wind-down: reading or watching a show?", "options": ["Reading", "Watching a show"], "category": "lifestyle"},
    ]

    QUESTION_LOOKUP: Dict[int, Dict[str, Any]] = {q["id"]: q for q in COMPATIBILITY_QUESTIONS}

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
    def _serialize_session(session: Dict[str, Any], viewer_id: str) -> Dict[str, Any]:
        if not session:
            return {}

        session_id = session.get("_id")
        if isinstance(session_id, ObjectId):
            session_id = str(session_id)

        questions = session.get("questions", [])
        responses = session.get("responses") or {}
        user_ids: List[str] = session.get("user_ids", [])

        viewer_answers = responses.get(viewer_id, {})
        partner_id = next((uid for uid in user_ids if uid != viewer_id), None)
        partner_answers = responses.get(partner_id, {}) if partner_id else {}

        serialized_questions: List[Dict[str, Any]] = []
        matches = 0
        for question in questions:
            question_id = question.get("id")
            question_key = str(question_id)
            your_answer = viewer_answers.get(question_key)
            partner_answer = partner_answers.get(question_key)

            is_match = (
                your_answer is not None
                and partner_answer is not None
                and your_answer.strip().lower() == partner_answer.strip().lower()
            )
            if is_match:
                matches += 1

            serialized_questions.append(
                {
                    "id": question_id,
                    "question": question.get("question"),
                    "options": question.get("options", []),
                    "category": question.get("category"),
                    "your_answer": your_answer,
                    "partner_answer": partner_answer,
                    "is_match": is_match,
                }
            )

        total_questions = len(questions)
        your_answers_count = len([ans for ans in viewer_answers.values() if ans])
        partner_answers_count = len([ans for ans in partner_answers.values() if ans])

        completed = session.get("status") == "completed"
        compatibility_summary = session.get("compatibility_summary") or {}
        if completed and not compatibility_summary and total_questions:
            score = int(round((matches / total_questions) * 100))
            compatibility_summary = {
                "matches": matches,
                "total": total_questions,
                "score": score,
            }

        completed_at = session.get("completed_at")
        if isinstance(completed_at, datetime):
            compatibility_summary["completed_at"] = completed_at.isoformat()

        partner_snapshot: Optional[Dict[str, Any]] = None
        if partner_id:
            partner = QuizService._get_user(partner_id)
            if partner:
                partner_snapshot = {
                    "_id": partner["_id"],
                    "name": partner.get("name"),
                    "email": partner.get("email"),
                }

        awaiting_partner_for = [
            q["id"]
            for q in serialized_questions
            if q["your_answer"] and not q["partner_answer"]
        ]

        return {
            "id": session_id,
            "status": session.get("status", "in_progress"),
            "created_at": session.get("created_at").isoformat()
            if isinstance(session.get("created_at"), datetime)
            else session.get("created_at"),
            "question_count": total_questions,
            "questions": serialized_questions,
            "progress": {
                "your_answers": your_answers_count,
                "partner_answers": partner_answers_count,
                "total_questions": total_questions,
                "awaiting_partner_for": awaiting_partner_for,
            },
            "compatibility": compatibility_summary if compatibility_summary else None,
            "partner": partner_snapshot,
        }

    @staticmethod
    def get_question_bank() -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        try:
            return {
                "questions": QuizService.COMPATIBILITY_QUESTIONS,
                "total_questions": len(QuizService.COMPATIBILITY_QUESTIONS),
                "default_batch_sizes": QuizService.DEFAULT_BATCH_SIZES,
            }, None
        except Exception as exc:
            return None, f"Failed to load question bank: {str(exc)}"

    @staticmethod
    def get_user_quiz_status(user_id: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        try:
            sessions = list(
                mongo.db.quiz_sessions.find({"user_ids": user_id}).sort("created_at", -1)
            )

            total_sessions = len(sessions)
            completed_sessions = [s for s in sessions if s.get("status") == "completed"]
            active_session = next((s for s in sessions if s.get("status") == "in_progress"), None)

            last_completed = completed_sessions[0] if completed_sessions else None
            average_score = None
            if completed_sessions:
                scores = [
                    s.get("compatibility_summary", {}).get("score", 0)
                    for s in completed_sessions
                ]
                if scores:
                    average_score = round(sum(scores) / len(scores), 2)

            status = {
                "total_sessions": total_sessions,
                "completed_sessions": len(completed_sessions),
                "active_session_id": str(active_session["_id"])
                if active_session and isinstance(active_session.get("_id"), ObjectId)
                else active_session.get("_id") if active_session else None,
                "last_score": (last_completed or {}).get("compatibility_summary", {}).get("score"),
                "last_completed_at": (
                    last_completed.get("completed_at").isoformat()
                    if last_completed and isinstance(last_completed.get("completed_at"), datetime)
                    else None
                ),
                "average_score": average_score,
                "question_bank_size": len(QuizService.COMPATIBILITY_QUESTIONS),
                "default_batch_sizes": QuizService.DEFAULT_BATCH_SIZES,
            }

            return status, None
        except Exception as exc:
            return None, f"Failed to get quiz status: {str(exc)}"

    @staticmethod
    def start_session(
        user_id: str,
        question_count: Optional[int] = None,
        question_ids: Optional[List[int]] = None,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        try:
            user = QuizService._get_user(user_id)
            if not user:
                return None, "User not found"

            partner_id = user.get("partner_id")
            partner_status = user.get("partner_status", "none")
            if not partner_id or partner_status != "connected":
                return None, "You need to be connected with your partner to start a session"

            # Return existing in-progress session if one is open
            existing_session = mongo.db.quiz_sessions.find_one(
                {"user_ids": user_id, "status": "in_progress"}
            )
            if existing_session:
                payload = QuizService._serialize_session(existing_session, user_id)
                payload["created"] = False
                return payload, None

            questions_for_session: List[Dict[str, Any]] = []

            if question_ids:
                missing = [qid for qid in question_ids if qid not in QuizService.QUESTION_LOOKUP]
                if missing:
                    return None, f"Unknown question ids: {missing}"
                for qid in question_ids:
                    source_q = QuizService.QUESTION_LOOKUP[qid]
                    questions_for_session.append(
                        {
                            "id": source_q["id"],
                            "question": source_q["question"],
                            "options": list(source_q.get("options", [])),
                            "category": source_q.get("category"),
                        }
                    )
            else:
                pool_size = len(QuizService.COMPATIBILITY_QUESTIONS)
                desired = question_count or QuizService.DEFAULT_BATCH_SIZES[0]
                desired = max(1, min(desired, pool_size))
                sample = random.sample(QuizService.COMPATIBILITY_QUESTIONS, desired)
                questions_for_session = [
                    {
                        "id": q["id"],
                        "question": q["question"],
                        "options": list(q.get("options", [])),
                        "category": q.get("category"),
                    }
                    for q in sample
                ]

            session_doc = {
                "user_ids": [user_id, partner_id],
                "created_by": user_id,
                "question_count": len(questions_for_session),
                "questions": questions_for_session,
                "responses": {
                    user_id: {},
                    partner_id: {},
                },
                "status": "in_progress",
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            }

            result = mongo.db.quiz_sessions.insert_one(session_doc)
            session_doc["_id"] = result.inserted_id

            payload = QuizService._serialize_session(session_doc, user_id)
            payload["created"] = True
            return payload, None

        except Exception as exc:
            return None, f"Failed to start session: {str(exc)}"

    @staticmethod
    def get_active_session(user_id: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        try:
            session = mongo.db.quiz_sessions.find_one(
                {"user_ids": user_id, "status": "in_progress"},
                sort=[("created_at", -1)],
            )

            if not session:
                return {"session": None}, None

            return {"session": QuizService._serialize_session(session, user_id)}, None

        except Exception as exc:
            return None, f"Failed to load active session: {str(exc)}"

    @staticmethod
    def get_session(user_id: str, session_id: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        try:
            try:
                session_obj_id = ObjectId(session_id)
            except Exception:
                return None, "Invalid session id"

            session = mongo.db.quiz_sessions.find_one({"_id": session_obj_id})
            if not session:
                return None, "Session not found"

            if user_id not in session.get("user_ids", []):
                return None, "You do not have access to this session"

            return {"session": QuizService._serialize_session(session, user_id)}, None

        except Exception as exc:
            return None, f"Failed to load session: {str(exc)}"

    @staticmethod
    def submit_session_answer(
        user_id: str,
        session_id: str,
        question_id: int,
        answer: str,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        try:
            if not answer or not str(answer).strip():
                return None, "Answer cannot be empty"

            try:
                session_obj_id = ObjectId(session_id)
            except Exception:
                return None, "Invalid session id"

            session = mongo.db.quiz_sessions.find_one({"_id": session_obj_id})
            if not session:
                return None, "Session not found"

            if session.get("status") == "completed":
                return None, "Session already completed"

            user_ids = session.get("user_ids", [])
            if user_id not in user_ids:
                return None, "You are not part of this session"

            question_ids = [q.get("id") for q in session.get("questions", [])]
            if question_id not in question_ids:
                return None, "Question is not part of this session"

            responses = session.get("responses") or {}
            for participant in user_ids:
                responses.setdefault(participant, {})

            question_key = str(question_id)
            responses[user_id][question_key] = str(answer).strip()

            total_questions = len(question_ids)
            completed = True
            matches = 0

            partner_id = next((uid for uid in user_ids if uid != user_id), None)

            for q in question_ids:
                q_key = str(q)
                for participant in user_ids:
                    if not responses.get(participant, {}).get(q_key):
                        completed = False
                        break
                if not completed:
                    break

            if partner_id:
                for q in question_ids:
                    q_key = str(q)
                    a1 = responses[user_id].get(q_key)
                    a2 = responses[partner_id].get(q_key)
                    if a1 and a2 and a1.strip().lower() == a2.strip().lower():
                        matches += 1

            update_fields: Dict[str, Any] = {
                "responses": responses,
                "updated_at": datetime.utcnow(),
            }

            if completed and total_questions:
                score = int(round((matches / total_questions) * 100))
                update_fields.update(
                    {
                        "status": "completed",
                        "completed_at": datetime.utcnow(),
                        "compatibility_summary": {
                            "matches": matches,
                            "total": total_questions,
                            "score": score,
                        },
                    }
                )

            mongo.db.quiz_sessions.update_one(
                {"_id": session_obj_id},
                {"$set": update_fields},
            )

            updated_session = mongo.db.quiz_sessions.find_one({"_id": session_obj_id})
            payload = QuizService._serialize_session(updated_session, user_id)
            payload["completed"] = payload.get("status") == "completed"

            return {"session": payload}, None

        except Exception as exc:
            return None, f"Failed to record answer: {str(exc)}"
