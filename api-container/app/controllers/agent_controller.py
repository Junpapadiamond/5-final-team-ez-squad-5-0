from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from ..services.style_profile_service import StyleProfileService
from ..services.agent_suggestion_service import AgentSuggestionService
from ..services.agent_analysis_service import AgentAnalysisService
from ..services.agent_action_queue_service import AgentActionQueueService
from ..services.agent_decision_service import AgentDecisionService
from ..services.agent_execution_service import AgentExecutionService
from ..services.agent_feedback_service import AgentFeedbackService

agent_bp = Blueprint("agent", __name__)


@agent_bp.route("/style-profile", methods=["GET"])
@jwt_required()
def get_style_profile():
    user_id = get_jwt_identity()
    force_refresh = request.args.get("refresh") in {"1", "true", "True"}

    profile, error = StyleProfileService.get_style_profile(user_id, force_refresh=force_refresh)

    if error:
        return jsonify({"message": error}), 400

    return jsonify(profile), 200


@agent_bp.route("/actions", methods=["GET"])
@jwt_required()
def get_agent_actions():
    user_id = get_jwt_identity()

    AgentDecisionService.process_pending_events(batch_size=25)

    suggestions, error = AgentSuggestionService.get_suggestions(user_id)

    if error:
        return jsonify({"message": error}), 400

    automation_queue = AgentActionQueueService.list_pending(user_id=user_id, limit=20)

    return jsonify({"suggestions": suggestions, "automation_queue": automation_queue}), 200


@agent_bp.route("/analyze", methods=["POST"])
@jwt_required()
def analyze_message():
    user_id = get_jwt_identity()
    data = request.get_json() or {}

    result, error = AgentAnalysisService.analyze_input(user_id, data.get("content"))

    if error:
        return jsonify({"message": error}), 400

    return jsonify(result), 200


@agent_bp.route("/actions/<action_id>/execute", methods=["POST"])
@jwt_required()
def execute_agent_action(action_id: str):
    user_id = get_jwt_identity()
    payload = request.get_json() or {}
    result, error = AgentExecutionService.execute_action(
        user_id=user_id,
        action_id=action_id,
        execution_payload=payload.get("input"),
        auto_approved=payload.get("auto_approved", False),
    )

    if error:
        return jsonify({"message": error}), 400

    return jsonify(result or {"status": "executed"}), 200


@agent_bp.route("/actions/<action_id>/feedback", methods=["POST"])
@jwt_required()
def submit_agent_feedback(action_id: str):
    user_id = get_jwt_identity()
    payload = request.get_json() or {}
    feedback = {
        "rating": payload.get("rating"),
        "comment": payload.get("comment"),
        "status": payload.get("status"),
    }
    AgentFeedbackService.record_feedback(user_id=user_id, action_id=action_id, feedback=feedback)
    AgentActionQueueService.update_status(
        [action_id],
        status=payload.get("status", "acknowledged"),
        metadata={"feedback": feedback},
    )
    return jsonify({"status": "recorded"}), 200
