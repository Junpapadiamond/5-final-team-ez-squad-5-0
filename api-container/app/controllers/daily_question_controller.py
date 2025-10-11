from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..services.daily_question_service import DailyQuestionService

daily_question_bp = Blueprint("daily_question", __name__)


@daily_question_bp.route("/", methods=["GET"])
@jwt_required()
def get_daily_question():
    try:
        user_id = get_jwt_identity()

        result, error = DailyQuestionService.get_today_question(user_id)

        if error:
            return jsonify({"message": error}), 404

        return jsonify(result), 200

    except Exception as e:
        return jsonify({"message": f"Failed to get daily question: {str(e)}"}), 500


@daily_question_bp.route("/answer", methods=["POST"])
@jwt_required()
def submit_answer():
    try:
        user_id = get_jwt_identity()
        data = request.get_json()

        if not data.get("answer"):
            return jsonify({"message": "Answer is required"}), 400

        result, error = DailyQuestionService.submit_answer(
            user_id=user_id,
            answer=data["answer"]
        )

        if error:
            return jsonify({"message": error}), 400

        return jsonify(result), 200

    except Exception as e:
        return jsonify({"message": f"Failed to submit answer: {str(e)}"}), 500


@daily_question_bp.route("/answers", methods=["GET"])
@jwt_required()
def get_daily_answers():
    try:
        user_id = get_jwt_identity()

        result = DailyQuestionService.get_answers(user_id)

        return jsonify(result), 200

    except Exception as e:
        return jsonify({"message": f"Failed to get answers: {str(e)}"}), 500
