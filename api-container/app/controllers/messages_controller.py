from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..services.messages_service import MessagesService

messages_bp = Blueprint("messages", __name__)


@messages_bp.route("/messages", methods=["GET"])
@jwt_required()
def get_messages():
    try:
        user_id = get_jwt_identity()

        result, error = MessagesService.get_user_messages(user_id)

        if error:
            return jsonify({"message": error}), 400

        return jsonify(result), 200

    except Exception as e:
        return jsonify({"message": f"Failed to get messages: {str(e)}"}), 500


@messages_bp.route("/send", methods=["POST"])
@jwt_required()
def send_message():
    try:
        user_id = get_jwt_identity()
        data = request.get_json() or {}

        result, error = MessagesService.send_message(
            sender_id=user_id,
            content=data.get("content"),
            receiver_id=data.get("receiver_id") or data.get("recipient_id"),
        )

        if error:
            return jsonify({"message": error}), 400

        return jsonify(result), 201

    except Exception as e:
        return jsonify({"message": f"Failed to send message: {str(e)}"}), 500


@messages_bp.route("/schedule", methods=["POST"])
@jwt_required()
def schedule_message():
    try:
        user_id = get_jwt_identity()
        data = request.get_json() or {}

        result, error = MessagesService.schedule_message(
            sender_id=user_id,
            content=data.get("content"),
            scheduled_for=data.get("scheduled_for") or data.get("scheduledTime"),
            receiver_id=data.get("receiver_id") or data.get("receiverId"),
        )

        if error:
            return jsonify({"message": error}), 400

        return jsonify(result), 201

    except Exception as e:
        return jsonify({"message": f"Failed to schedule message: {str(e)}"}), 500


@messages_bp.route("/scheduled", methods=["GET"])
@jwt_required()
def get_scheduled_messages():
    try:
        user_id = get_jwt_identity()

        result, error = MessagesService.get_scheduled_messages(user_id)

        if error:
            return jsonify({"message": error}), 400

        return jsonify(result), 200

    except Exception as e:
        return jsonify({"message": f"Failed to load scheduled messages: {str(e)}"}), 500


@messages_bp.route("/scheduled/<message_id>/cancel", methods=["POST"])
@jwt_required()
def cancel_scheduled_message(message_id):
    try:
        user_id = get_jwt_identity()

        result, error = MessagesService.cancel_scheduled_message(user_id, message_id)

        if error:
            return jsonify({"message": error}), 400

        return jsonify(result), 200

    except Exception as e:
        return jsonify({"message": f"Failed to cancel scheduled message: {str(e)}"}), 500


@messages_bp.route("/conversation/<partner_id>", methods=["GET"])
@jwt_required()
def get_conversation(partner_id):
    try:
        user_id = get_jwt_identity()

        result, error = MessagesService.get_conversation(user_id, partner_id)

        if error:
            return jsonify({"message": error}), 404

        return jsonify(result), 200

    except Exception as e:
        return jsonify({"message": f"Failed to get conversation: {str(e)}"}), 500
