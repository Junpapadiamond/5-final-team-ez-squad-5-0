from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

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
    except Exception as exc:
        return jsonify({"message": f"Failed to get quiz status: {str(exc)}"}), 500


@quiz_bp.route("/questions", methods=["GET"])
@jwt_required()
def get_question_bank():
    try:
        result, error = QuizService.get_question_bank()

        if error:
            return jsonify({"message": error}), 400

        return jsonify(result), 200
    except Exception as exc:
        return jsonify({"message": f"Failed to load questions: {str(exc)}"}), 500


@quiz_bp.route("/session/start", methods=["POST"])
@jwt_required()
def start_session():
    try:
        user_id = get_jwt_identity()
        data = request.get_json() or {}

        question_count = data.get("question_count")
        question_ids = data.get("question_ids")

        result, error = QuizService.start_session(
            user_id=user_id,
            question_count=question_count,
            question_ids=question_ids,
        )

        if error:
            return jsonify({"message": error}), 400

        status_code = 201 if result.get("created", False) else 200
        return jsonify(result), status_code
    except Exception as exc:
        return jsonify({"message": f"Failed to start session: {str(exc)}"}), 500


@quiz_bp.route("/session/current", methods=["GET"])
@jwt_required()
def get_active_session():
    try:
        user_id = get_jwt_identity()
        result, error = QuizService.get_active_session(user_id)

        if error:
            return jsonify({"message": error}), 400

        return jsonify(result), 200
    except Exception as exc:
        return jsonify({"message": f"Failed to load active session: {str(exc)}"}), 500


@quiz_bp.route("/session/<session_id>", methods=["GET"])
@jwt_required()
def get_session(session_id):
    try:
        user_id = get_jwt_identity()
        result, error = QuizService.get_session(user_id, session_id)

        if error:
            status_code = 404 if "not found" in error.lower() else 400
            return jsonify({"message": error}), status_code

        return jsonify(result), 200
    except Exception as exc:
        return jsonify({"message": f"Failed to load session: {str(exc)}"}), 500


@quiz_bp.route("/session/<session_id>/answer", methods=["POST"])
@jwt_required()
def submit_answer(session_id):
    try:
        user_id = get_jwt_identity()
        data = request.get_json() or {}

        question_id = data.get("question_id")
        answer = data.get("answer")

        if question_id is None:
            return jsonify({"message": "question_id is required"}), 400

        result, error = QuizService.submit_session_answer(
            user_id=user_id,
            session_id=session_id,
            question_id=question_id,
            answer=answer,
        )

        if error:
            return jsonify({"message": error}), 400

        return jsonify(result), 200
    except Exception as exc:
        return jsonify({"message": f"Failed to record answer: {str(exc)}"}), 500
