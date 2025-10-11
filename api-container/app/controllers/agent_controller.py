from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from ..services.style_profile_service import StyleProfileService
from ..services.agent_suggestion_service import AgentSuggestionService
from ..services.agent_analysis_service import AgentAnalysisService

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

    suggestions, error = AgentSuggestionService.get_suggestions(user_id)

    if error:
        return jsonify({"message": error}), 400

    return jsonify({"suggestions": suggestions}), 200


@agent_bp.route("/analyze", methods=["POST"])
@jwt_required()
def analyze_message():
    user_id = get_jwt_identity()
    data = request.get_json() or {}

    result, error = AgentAnalysisService.analyze_input(user_id, data.get("content"))

    if error:
        return jsonify({"message": error}), 400

    return jsonify(result), 200
