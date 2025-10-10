from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..services.auth_service import AuthService

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["POST"])
def register():
    try:
        data = request.get_json()

        # Validate required fields
        if not data.get("name") or not data.get("email") or not data.get("password"):
            return jsonify({"message": "Name, email, and password are required"}), 400

        result, error = AuthService.register_user(
            name=data["name"],
            email=data["email"],
            password=data["password"],
            partner_email=data.get("partner_email")
        )

        if error:
            return jsonify({"message": error}), 400

        return jsonify(result), 201

    except Exception as e:
        return jsonify({"message": f"Registration failed: {str(e)}"}), 500


@auth_bp.route("/login", methods=["POST"])
def login():
    try:
        data = request.get_json()

        # Validate required fields
        if not data.get("email") or not data.get("password"):
            return jsonify({"message": "Email and password are required"}), 400

        result, error = AuthService.login_user(
            email=data["email"],
            password=data["password"]
        )

        if error:
            return jsonify({"message": error}), 401

        return jsonify(result), 200

    except Exception as e:
        return jsonify({"message": f"Login failed: {str(e)}"}), 500


@auth_bp.route("/profile", methods=["GET"])
@jwt_required()
def get_profile():
    try:
        user_id = get_jwt_identity()

        result, error = AuthService.get_user_profile(user_id)

        if error:
            return jsonify({"message": error}), 404

        return jsonify(result), 200

    except Exception as e:
        return jsonify({"message": f"Failed to get profile: {str(e)}"}), 500


@auth_bp.route("/profile", methods=["PUT"])
@jwt_required()
def update_profile():
    try:
        user_id = get_jwt_identity()
        data = request.get_json() or {}

        result, error = AuthService.update_profile(user_id, data.get("name"))

        if error:
            return jsonify({"message": error}), 400

        return jsonify(result), 200

    except Exception as e:
        return jsonify({"message": f"Failed to update profile: {str(e)}"}), 500


@auth_bp.route("/notifications/email", methods=["PUT"])
@jwt_required()
def update_email_notifications():
    try:
        user_id = get_jwt_identity()
        data = request.get_json() or {}

        result, error = AuthService.update_email_notifications(
            user_id, data.get("enabled", True)
        )

        if error:
            return jsonify({"message": error}), 400

        return jsonify(result), 200

    except Exception as e:
        return jsonify({"message": f"Failed to update notifications: {str(e)}"}), 500


@auth_bp.route("/password", methods=["PUT"])
@jwt_required()
def change_password():
    try:
        user_id = get_jwt_identity()
        data = request.get_json() or {}

        current_password = data.get("current_password")
        new_password = data.get("new_password")

        if not current_password or not new_password:
            return jsonify({"message": "Both current and new password are required"}), 400

        result, error = AuthService.change_password(user_id, current_password, new_password)

        if error:
            return jsonify({"message": error}), 400

        return jsonify(result), 200

    except Exception as e:
        return jsonify({"message": f"Failed to update password: {str(e)}"}), 500


@auth_bp.route("/partner/status", methods=["GET"])
@jwt_required()
def get_partner_status():
    try:
        user_id = get_jwt_identity()

        result, error = AuthService.get_partner_status(user_id)

        if error:
            return jsonify({"message": error}), 400

        return jsonify(result), 200

    except Exception as e:
        return jsonify({"message": f"Failed to get partner status: {str(e)}"}), 500


@auth_bp.route("/partner/invite", methods=["POST"])
@jwt_required()
def send_partner_invite():
    try:
        user_id = get_jwt_identity()
        data = request.get_json() or {}

        result, error = AuthService.invite_partner(user_id, data.get("partner_email"))

        if error:
            return jsonify({"message": error}), 400

        return jsonify(result), 200

    except Exception as e:
        return jsonify({"message": f"Failed to send invite: {str(e)}"}), 500


@auth_bp.route("/partner/accept", methods=["POST"])
@jwt_required()
def accept_partner_invite():
    try:
        user_id = get_jwt_identity()
        data = request.get_json() or {}

        invitation_id = data.get("invitation_id") or data.get("inviter_id")
        if not invitation_id:
            return jsonify({"message": "Invitation id is required"}), 400

        result, error = AuthService.accept_partner_invitation(user_id, invitation_id)

        if error:
            return jsonify({"message": error}), 400

        return jsonify(result), 200

    except Exception as e:
        return jsonify({"message": f"Failed to accept invite: {str(e)}"}), 500


@auth_bp.route("/partner/reject", methods=["POST"])
@jwt_required()
def reject_partner_invite():
    try:
        user_id = get_jwt_identity()
        data = request.get_json() or {}

        invitation_id = data.get("invitation_id") or data.get("inviter_id")
        if not invitation_id:
            return jsonify({"message": "Invitation id is required"}), 400

        result, error = AuthService.reject_partner_invitation(user_id, invitation_id)

        if error:
            return jsonify({"message": error}), 400

        return jsonify(result), 200

    except Exception as e:
        return jsonify({"message": f"Failed to reject invite: {str(e)}"}), 500
