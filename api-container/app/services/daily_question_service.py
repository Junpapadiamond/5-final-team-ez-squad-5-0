from datetime import datetime, date
from .. import mongo
import random


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

            return {
                "message": "Answer submitted successfully",
                "question": question["question"],
                "answer": answer,
                "date": today
            }, None

        except Exception as e:
            return None, f"Failed to submit answer: {str(e)}"