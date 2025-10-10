from datetime import datetime
from typing import Optional, Dict, Any, Tuple
from bson import ObjectId
from .. import mongo
from ..email_utils import send_invitation_email, send_partner_message


class PartnerService:
    """Business logic for partner invitations and relationship status."""

    @staticmethod
    def _get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
        try:
            user = mongo.db.users.find_one({"_id": ObjectId(user_id)})
            if user:
                user["_id"] = str(user["_id"])
            return user
        except Exception:
            return None

    @staticmethod
    def _get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
        if not email:
            return None
        user = mongo.db.users.find_one({"email": email})
        if user:
            user["_id"] = str(user["_id"])
        return user

    @staticmethod
    def _format_invitation(invitation: Dict[str, Any]) -> Dict[str, Any]:
        created_at = invitation.get("created_at")
        if isinstance(created_at, datetime):
            created_at_str = created_at.isoformat() + "Z"
        else:
            created_at_str = created_at

        return {
            "_id": str(invitation["_id"]),
            "inviter_name": invitation.get("sender_name"),
            "inviter_email": invitation.get("sender_email"),
            "invitee_email": invitation.get("receiver_email"),
            "created_at": created_at_str,
            "status": invitation.get("status", "pending"),
        }

    @staticmethod
    def get_partner_status(user_id: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        user = PartnerService._get_user_by_id(user_id)
        if not user:
            return None, "User not found"

        partner_data = None
        partner_id = user.get("partner_id")
        if partner_id:
            partner = PartnerService._get_user_by_id(partner_id)
            if partner:
                partner_data = {
                    "_id": partner["_id"],
                    "name": partner.get("name"),
                    "email": partner.get("email"),
                }

        pending_received = list(
            mongo.db.partner_invitations.find(
                {"receiver_id": user_id, "status": "pending"}
            ).sort("created_at", 1)
        )
        pending_sent = list(
            mongo.db.partner_invitations.find(
                {"sender_id": user_id, "status": "pending"}
            ).sort("created_at", 1)
        )

        return {
            "status": user.get("partner_status", "none"),
            "has_partner": bool(partner_data),
            "partner": partner_data,
            "pending_invitations": [
                PartnerService._format_invitation(invitation)
                for invitation in pending_received
            ],
            "sent_invitations": [
                PartnerService._format_invitation(invitation)
                for invitation in pending_sent
            ],
        }, None

    @staticmethod
    def invite_partner(user_id: str, partner_email: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        if not partner_email:
            return None, "Partner email is required"

        user = PartnerService._get_user_by_id(user_id)
        if not user:
            return None, "User not found"

        if user.get("email") == partner_email:
            return None, "You cannot invite yourself"

        if user.get("partner_status") == "connected":
            return None, "You are already connected with a partner"

        existing_invitation = mongo.db.partner_invitations.find_one(
            {"sender_id": user_id, "receiver_email": partner_email, "status": "pending"}
        )
        if existing_invitation:
            return {
                "message": "Invitation already pending",
                "invitation_id": str(existing_invitation["_id"]),
            }, None

        partner_user = PartnerService._get_user_by_email(partner_email)
        invitation_doc = {
            "sender_id": user_id,
            "sender_name": user.get("name"),
            "sender_email": user.get("email"),
            "receiver_email": partner_email,
            "status": "pending",
            "created_at": datetime.utcnow(),
        }

        if partner_user:
            # Ensure partner is not already connected
            if (
                partner_user.get("partner_id")
                and partner_user.get("partner_status") == "connected"
                and partner_user["partner_id"] != user_id
            ):
                return None, "This user is already connected with another partner"

            invitation_doc["receiver_id"] = partner_user["_id"]

            # Update status but DON'T set partner_id until invitation is accepted
            mongo.db.users.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": {"partner_status": "pending_sent"}},
            )
            mongo.db.users.update_one(
                {"_id": ObjectId(partner_user["_id"])},
                {"$set": {"partner_status": "pending_received"}},
            )

            if partner_user.get("email_notifications", True):
                try:
                    send_partner_message(
                        partner_user["email"],
                        user.get("name", "A partner"),
                        f"{user.get('name', 'Your partner')} has invited you to connect on Together.",
                    )
                except Exception:
                    pass
        else:
            # Update inviter status and send external email
            mongo.db.users.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": {"partner_email": partner_email, "partner_status": "invited"}},
            )

            try:
                send_invitation_email(partner_email, user.get("name", "Your partner"))
            except Exception:
                pass

        result = mongo.db.partner_invitations.insert_one(invitation_doc)

        return {
            "message": "Partnership invitation sent successfully",
            "invitation_id": str(result.inserted_id),
        }, None

    @staticmethod
    def accept_invitation(user_id: str, invitation_id: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        try:
            invitation_obj_id = ObjectId(invitation_id)
        except Exception:
            return None, "Invalid invitation id"

        invitation = mongo.db.partner_invitations.find_one(
            {"_id": invitation_obj_id, "status": "pending"}
        )

        if not invitation:
            return None, "Invitation not found or already processed"

        if invitation.get("receiver_id") and invitation["receiver_id"] != user_id:
            return None, "You are not authorized to accept this invitation"

        user = PartnerService._get_user_by_id(user_id)
        if not user:
            return None, "User not found"

        sender_id = invitation.get("sender_id")
        sender = PartnerService._get_user_by_id(sender_id)
        if not sender:
            return None, "Inviting partner not found"

        # Link users
        mongo.db.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"partner_id": sender_id, "partner_status": "connected"}},
        )
        mongo.db.users.update_one(
            {"_id": ObjectId(sender_id)},
            {"$set": {"partner_id": user_id, "partner_status": "connected"}},
        )

        mongo.db.partner_invitations.update_one(
            {"_id": invitation_obj_id},
            {"$set": {"status": "accepted", "responded_at": datetime.utcnow()}},
        )

        # Close out other pending invitations for these users
        mongo.db.partner_invitations.update_many(
            {
                "_id": {"$ne": invitation_obj_id},
                "$or": [
                    {"sender_id": {"$in": [user_id, sender_id]}},
                    {"receiver_id": {"$in": [user_id, sender_id]}},
                ],
                "status": "pending",
            },
            {"$set": {"status": "cancelled", "responded_at": datetime.utcnow()}},
        )

        if sender.get("email_notifications", True):
            try:
                send_partner_message(
                    sender["email"],
                    user.get("name", "Your partner"),
                    f"{user.get('name', 'Your partner')} has accepted your invitation. You are now connected!",
                )
            except Exception:
                pass

        return {"message": "Partnership accepted successfully"}, None

    @staticmethod
    def reject_invitation(user_id: str, invitation_id: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        try:
            invitation_obj_id = ObjectId(invitation_id)
        except Exception:
            return None, "Invalid invitation id"

        invitation = mongo.db.partner_invitations.find_one(
            {"_id": invitation_obj_id, "status": "pending"}
        )
        if not invitation:
            return None, "Invitation not found or already processed"

        if invitation.get("receiver_id") and invitation["receiver_id"] != user_id:
            return None, "You are not authorized to reject this invitation"

        sender_id = invitation.get("sender_id")

        # Reset partnership status if users were linked
        mongo.db.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$unset": {"partner_id": "", "partner_status": ""}},
        )
        if sender_id:
            mongo.db.users.update_one(
                {"_id": ObjectId(sender_id)},
                {"$unset": {"partner_id": "", "partner_status": ""}},
            )

        mongo.db.partner_invitations.update_one(
            {"_id": invitation_obj_id},
            {"$set": {"status": "rejected", "responded_at": datetime.utcnow()}},
        )

        return {"message": "Partnership invitation rejected"}, None
