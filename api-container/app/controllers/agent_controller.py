from datetime import datetime

import time

from flask import Blueprint, jsonify, request, current_app
from flask_jwt_extended import get_jwt_identity, jwt_required

from ..services.style_profile_service import StyleProfileService
from ..services.agent_suggestion_service import AgentSuggestionService
from ..services.agent_analysis_service import AgentAnalysisService
from ..services.agent_action_queue_service import AgentActionQueueService
from ..services.agent_decision_service import AgentDecisionService
from ..services.agent_execution_service import AgentExecutionService
from ..services.agent_feedback_service import AgentFeedbackService
from ..services.agent_activity_service import AgentActivityService

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


@agent_bp.route("/activity", methods=["GET"])
@jwt_required()
def get_agent_activity():
    user_id = get_jwt_identity()
    since_param = request.args.get("since")
    include_processed = request.args.get("include_processed") in {"1", "true", "True"}
    limit_param = request.args.get("limit", "50")

    try:
        limit = max(1, min(int(limit_param), 200))
    except ValueError:
        limit = 50

    since_dt = None
    if since_param:
        try:
            since_dt = datetime.fromisoformat(since_param.replace("Z", ""))
        except ValueError:
            return jsonify({"message": "Invalid 'since' timestamp"}), 400

    events = AgentActivityService.fetch_recent(
        limit=limit,
        since=since_dt,
        include_processed=include_processed,
        user_id=user_id,
    )

    response = {
        "events": events,
        "count": len(events),
    }
    if events:
        response["latest_occurred_at"] = events[0]["occurred_at"]

    return jsonify(response), 200


@agent_bp.route("/actions", methods=["GET"])
@jwt_required()
def get_agent_actions():
    user_id = get_jwt_identity()

    request_start = time.perf_counter()
    try:
        decision_stats = AgentDecisionService.process_pending_events(
            batch_size=10,
            user_id=user_id,
            time_budget_seconds=2.5,
        )
    except TypeError:
        decision_stats = AgentDecisionService.process_pending_events(batch_size=10)

    suggestions_payload, error = AgentSuggestionService.get_suggestions(user_id)

    if error:
        return jsonify({"message": error}), 400

    suggestions = (suggestions_payload or {}).get("suggestions", [])
    suggestion_meta = (suggestions_payload or {}).get("metadata")
    automation_queue = AgentActionQueueService.list_pending(user_id=user_id, limit=20)
    total_elapsed = time.perf_counter() - request_start
    if total_elapsed > 2.5:
        current_app.logger.warning(
            "Agent actions response slow for user %s: %.2fs (decision_stats=%s, suggestions=%s, queue=%s)",
            user_id,
            total_elapsed,
            decision_stats,
            len(suggestions),
            len(automation_queue),
        )

    return jsonify(
        {
            "suggestions": suggestions,
            "automation_queue": automation_queue,
            "llm": suggestion_meta,
        }
    ), 200


@agent_bp.route("/queue", methods=["GET"])
@jwt_required()
def get_agent_queue():
    user_id = get_jwt_identity()
    limit_param = request.args.get("limit", "10")
    include_completed = request.args.get("include_completed") in {"1", "true", "True"}

    try:
        limit = max(1, min(int(limit_param), 50))
    except ValueError:
        limit = 10

    request_start = time.perf_counter()
    try:
        decision_stats = AgentDecisionService.process_pending_events(
            batch_size=10,
            user_id=user_id,
            time_budget_seconds=2.5,
        )
    except TypeError:
        decision_stats = AgentDecisionService.process_pending_events(batch_size=10)

    pending = AgentActionQueueService.list_pending(
        user_id=user_id,
        limit=limit,
        include_completed=False,
    )
    recent = (
        AgentActionQueueService.list_pending(
            user_id=user_id,
            limit=limit,
            include_completed=True,
        )
        if include_completed
        else []
    )
    total_elapsed = time.perf_counter() - request_start
    if total_elapsed > 2.5:
        current_app.logger.warning(
            "Agent queue response slow for user %s: %.2fs (decision_stats=%s, pending=%s)",
            user_id,
            total_elapsed,
            decision_stats,
            len(pending),
        )

    return jsonify(
        {
            "pending": pending,
            "recent": recent if include_completed else None,
            "pending_count": len(pending),
        }
    ), 200


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
