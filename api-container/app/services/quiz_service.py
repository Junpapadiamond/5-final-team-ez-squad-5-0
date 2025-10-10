from datetime import datetime
from .. import mongo
from bson import ObjectId


class QuizService:

    # Sample quiz questions for couples
    QUIZ_QUESTIONS = [
        {
            "id": 1,
            "question": "What is your partner's favorite color?",
            "type": "text"
        },
        {
            "id": 2,
            "question": "What is your partner's biggest fear?",
            "type": "text"
        },
        {
            "id": 3,
            "question": "What is your partner's dream vacation destination?",
            "type": "text"
        },
        {
            "id": 4,
            "question": "What makes your partner happiest?",
            "type": "text"
        },
        {
            "id": 5,
            "question": "What is your partner's favorite food?",
            "type": "text"
        },
        {
            "id": 6,
            "question": "What is your partner's biggest goal in life?",
            "type": "text"
        },
        {
            "id": 7,
            "question": "How does your partner prefer to receive love?",
            "type": "multiple_choice",
            "options": ["Words of affirmation", "Acts of service", "Receiving gifts", "Quality time", "Physical touch"]
        },
        {
            "id": 8,
            "question": "What is your partner's favorite way to relax?",
            "type": "text"
        },
        {
            "id": 9,
            "question": "What is your partner most proud of?",
            "type": "text"
        },
        {
            "id": 10,
            "question": "What is your partner's favorite memory of you together?",
            "type": "text"
        }
    ]

    @staticmethod
    def get_user_quiz_status(user_id):
        try:
            # Check if user has completed any quizzes
            quiz_count = mongo.db.quiz_responses.count_documents({"user_id": user_id})

            # Get latest quiz if exists
            latest_quiz = mongo.db.quiz_responses.find_one(
                {"user_id": user_id},
                sort=[("created_at", -1)]
            )

            status = {
                "has_taken_quiz": quiz_count > 0,
                "quiz_count": quiz_count,
                "latest_quiz_date": latest_quiz["created_at"].isoformat() if latest_quiz else None,
                "available_questions": len(QuizService.QUIZ_QUESTIONS)
            }

            return status, None

        except Exception as e:
            return None, f"Failed to get quiz status: {str(e)}"

    @staticmethod
    def get_quiz_questions(user_id):
        try:
            # Return all available questions
            return {
                "questions": QuizService.QUIZ_QUESTIONS,
                "total_questions": len(QuizService.QUIZ_QUESTIONS)
            }, None

        except Exception as e:
            return None, f"Failed to get quiz questions: {str(e)}"

    @staticmethod
    def submit_quiz_answers(user_id, answers):
        try:
            # Validate answers format
            if not isinstance(answers, list):
                return None, "Answers must be a list"

            # Create quiz response document
            quiz_response = {
                "user_id": user_id,
                "answers": answers,
                "created_at": datetime.utcnow(),
                "score": len(answers)  # Simple scoring - count of answered questions
            }

            # Insert quiz response
            result = mongo.db.quiz_responses.insert_one(quiz_response)

            return {
                "message": "Quiz submitted successfully",
                "quiz_id": str(result.inserted_id),
                "score": len(answers),
                "total_questions": len(QuizService.QUIZ_QUESTIONS)
            }, None

        except Exception as e:
            return None, f"Failed to submit quiz: {str(e)}"

    @staticmethod
    def get_user_quiz_results(user_id):
        try:
            # Get all quiz responses for user
            quizzes = list(mongo.db.quiz_responses.find(
                {"user_id": user_id},
                sort=[("created_at", -1)]
            ))

            # Convert ObjectId to string
            for quiz in quizzes:
                quiz["_id"] = str(quiz["_id"])
                quiz["created_at"] = quiz["created_at"].isoformat()

            return {
                "quizzes": quizzes,
                "total_quizzes": len(quizzes)
            }, None

        except Exception as e:
            return None, f"Failed to get quiz results: {str(e)}"