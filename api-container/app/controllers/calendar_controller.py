from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..services.calendar_service import CalendarService

calendar_bp = Blueprint("calendar", __name__)


@calendar_bp.route("/events", methods=["GET"])
@jwt_required()
def get_events():
    user_id = get_jwt_identity()
    year = request.args.get("year", type=int)
    month = request.args.get("month", type=int)

    result, error = CalendarService.get_events_for_month(user_id, year, month)

    if error:
        return jsonify({"message": error}), 400

    return jsonify(result), 200


@calendar_bp.route("/events", methods=["POST"])
@jwt_required()
def create_event():
    user_id = get_jwt_identity()
    data = request.get_json() or {}

    result, error = CalendarService.create_event(
        user_id=user_id,
        title=data.get("title"),
        date_str=data.get("date"),
        time_str=data.get("time"),
        description=data.get("description"),
    )

    if error:
        return jsonify({"message": error}), 400

    return jsonify(result), 201
