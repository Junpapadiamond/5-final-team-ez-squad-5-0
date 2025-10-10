from flask_jwt_extended import create_access_token
from werkzeug.security import check_password_hash, generate_password_hash
from ..models.user import User
from .partner_service import PartnerService


class AuthService:
    @staticmethod
    def register_user(name, email, password, partner_email=None):
        # Check if user already exists
        existing_user = User.find_by_email(email)
        if existing_user:
            return None, "Email already registered"

        # Create new user
        try:
            user = User.create(name, email, password, partner_email)
            token = create_access_token(identity=user["_id"])

            # Remove sensitive data before returning
            user_data = user.copy()
            if "password_hash" in user_data:
                del user_data["password_hash"]

            # Automatically send partner invite if provided during registration
            if partner_email:
                PartnerService.invite_partner(user_data["_id"], partner_email)

            return {
                "user": user_data,
                "token": token,
                "message": "User registered successfully"
            }, None
        except Exception as e:
            return None, f"Registration failed: {str(e)}"

    @staticmethod
    def login_user(email, password):
        # Find user by email
        user = User.find_by_email(email)
        if not user:
            return None, "Invalid email or password"

        # Verify password
        if not User.verify_password(user, password):
            return None, "Invalid email or password"

        # Create access token
        try:
            token = create_access_token(identity=user["_id"])

            # Remove sensitive data
            user_data = user.copy()
            if "password_hash" in user_data:
                del user_data["password_hash"]

            return {
                "user": user_data,
                "token": token,
                "message": "Login successful"
            }, None
        except Exception as e:
            return None, f"Login failed: {str(e)}"

    @staticmethod
    def get_user_profile(user_id):
        user = User.find_by_id(user_id)
        if not user:
            return None, "User not found"

        # Remove sensitive data
        user_data = user.copy()
        if "password_hash" in user_data:
            del user_data["password_hash"]

        return user_data, None

    @staticmethod
    def update_email_notifications(user_id, enabled):
        User.update(user_id, {"email_notifications": bool(enabled)})
        return {
            "message": "Email notification preferences updated successfully",
            "enabled": bool(enabled),
        }, None

    @staticmethod
    def update_profile(user_id, name):
        if not name:
            return None, "Name is required"

        User.update(user_id, {"name": name})
        user = User.find_by_id(user_id)
        if not user:
            return None, "User not found"

        if "password_hash" in user:
            del user["password_hash"]

        return user, None

    @staticmethod
    def change_password(user_id, current_password, new_password):
        user = User.find_by_id(user_id)
        if not user:
            return None, "User not found"

        password_hash = user.get("password_hash")
        if not password_hash or not check_password_hash(password_hash, current_password):
            return None, "Current password is incorrect"

        new_hash = generate_password_hash(new_password)
        User.update(user_id, {"password_hash": new_hash})

        return {"message": "Password updated successfully"}, None

    @staticmethod
    def get_partner_status(user_id):
        return PartnerService.get_partner_status(user_id)

    @staticmethod
    def invite_partner(user_id, partner_email):
        return PartnerService.invite_partner(user_id, partner_email)

    @staticmethod
    def accept_partner_invitation(user_id, invitation_id):
        return PartnerService.accept_invitation(user_id, invitation_id)

    @staticmethod
    def reject_partner_invitation(user_id, invitation_id):
        return PartnerService.reject_invitation(user_id, invitation_id)
