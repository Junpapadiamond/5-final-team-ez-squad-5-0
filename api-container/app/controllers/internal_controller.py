from __future__ import annotations

from datetime import datetime
from typing import Optional

from flask import Blueprint, current_app, jsonify, request

from ..services.agent_activity_service import AgentActivityService
from ..services.agent_decision_service import AgentDecisionService

internal_bp = Blueprint("internal", __name__)


def _is_token_valid(token: Optional[str]) -> bool:
    expected = current_app.config.get("INTERNAL_SERVICE_TOKEN")
    if not expected:
        return False
    return token == expected


@internal_bp.before_request
def _verify_internal_token() -> None:
    token = request.headers.get("X-Internal-Token")
    if not _is_token_valid(token):
        return jsonify({"message": "Unauthorized"}), 401


@internal_bp.route("/activity-feed", methods=["GET"])
def get_activity_feed():
    since_param = request.args.get("since")
    scenario = request.args.get("scenario")
    include_processed = request.args.get("include_processed") in {"1", "true", "True"}
    limit_param = request.args.get("limit", "100")

    try:
        limit = max(1, min(int(limit_param), 200))
    except ValueError:
        limit = 100

    since_dt: Optional[datetime] = None
    if since_param:
        try:
            since_dt = datetime.fromisoformat(since_param.replace("Z", ""))
        except ValueError:
            return jsonify({"message": "Invalid 'since' timestamp"}), 400

    events = AgentActivityService.fetch_recent(
        limit=limit,
        since=since_dt,
        scenario=scenario,
        include_processed=include_processed,
    )

    response = {
        "events": events,
        "count": len(events),
    }
    if events:
        response["latest_occurred_at"] = events[0]["occurred_at"]

    return jsonify(response), 200


@internal_bp.route("/activity-feed/ack", methods=["POST"])
def acknowledge_activity():
    data = request.get_json() or {}
    identifiers = data.get("ids") or []
    if not isinstance(identifiers, list):
        return jsonify({"message": "ids must be a list"}), 400
    updated = AgentActivityService.mark_processed(identifiers)
    return jsonify({"updated": updated}), 200


@internal_bp.route("/decisions/run", methods=["POST"])
def run_decision_engine():
    payload = request.get_json() or {}
    batch_size = int(payload.get("batch_size", 25)) if isinstance(payload, dict) else 25
    metrics = AgentDecisionService.process_pending_events(batch_size=batch_size)
    return jsonify(metrics), 200
