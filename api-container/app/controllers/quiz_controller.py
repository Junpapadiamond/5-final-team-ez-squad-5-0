from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..services.quiz_service import QuizService

quiz_bp = Blueprint("quiz", __name__)


@quiz_bp.route("/status", methods=["GET"])
@jwt_required()
def get_quiz_status():
    try:
        user_id = get_jwt_identity()

        result, error = QuizService.get_user_quiz_status(user_id)

        if error:
            return jsonify({"message": error}), 404

        return jsonify(result), 200

    except Exception as e:
        return jsonify({"message": f"Failed to get quiz status: {str(e)}"}), 500


@quiz_bp.route("/questions", methods=["GET"])
@jwt_required()
def get_quiz_questions():
    try:
        user_id = get_jwt_identity()

        result, error = QuizService.get_quiz_questions(user_id)

        if error:
            return jsonify({"message": error}), 404

        return jsonify(result), 200

    except Exception as e:
        return jsonify({"message": f"Failed to get quiz questions: {str(e)}"}), 500


@quiz_bp.route("/submit", methods=["POST"])
@jwt_required()
def submit_quiz():
    try:
        user_id = get_jwt_identity()
        data = request.get_json()

        if not data.get("answers"):
            return jsonify({"message": "Answers are required"}), 400

        result, error = QuizService.submit_quiz_answers(
            user_id=user_id,
            answers=data["answers"]
        )

        if error:
            return jsonify({"message": error}), 400

        return jsonify(result), 200

    except Exception as e:
        return jsonify({"message": f"Failed to submit quiz: {str(e)}"}), 500