from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Tuple
from bson import ObjectId
from .. import mongo
from ..email_utils import send_partner_message


class MessagesService:
    """Service logic for direct messages and scheduled deliveries."""

    @staticmethod
    def _get_user(user_id: str) -> Optional[Dict[str, Any]]:
        try:
            user = mongo.db.users.find_one({"_id": ObjectId(user_id)})
            if user:
                user["_id"] = str(user["_id"])
            return user
        except Exception:
            return None

    @staticmethod
    def _safe_object_id(value: str) -> Optional[ObjectId]:
        try:
            return ObjectId(value)
        except Exception:
            return None

    @staticmethod
    def _resolve_partner_id(user: Dict[str, Any]) -> Optional[str]:
        partner_id = user.get("partner_id")
        status = user.get("partner_status")
        if partner_id and status == "connected":
            return partner_id
        return None

    @staticmethod
    def _format_message(doc: Dict[str, Any], user_lookup: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        sender_id = doc.get("sender_id")
        receiver_id = doc.get("receiver_id")
        sender = user_lookup.get(sender_id) or MessagesService._get_user(sender_id)
        receiver = user_lookup.get(receiver_id) or MessagesService._get_user(receiver_id)

        if sender:
            user_lookup[sender_id] = sender
        if receiver:
            user_lookup[receiver_id] = receiver

        created_at = doc.get("created_at")
        if isinstance(created_at, datetime):
            created_at_str = created_at.isoformat()
        else:
            created_at_str = created_at

        return {
            "_id": str(doc["_id"]),
            "sender_id": sender_id,
            "sender_name": (sender or {}).get("name", "You" if sender_id == receiver_id else ""),
            "recipient_id": receiver_id,
            "recipient_name": (receiver or {}).get("name", ""),
            "content": doc.get("content", ""),
            "timestamp": created_at_str,
            "is_scheduled": bool(doc.get("scheduled_from")),
            "is_read": doc.get("is_read", False),
        }

    @staticmethod
    def get_user_messages(user_id: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        try:
            messages = list(
                mongo.db.messages.find(
                    {
                        "$or": [
                            {"sender_id": user_id},
                            {"receiver_id": user_id},
                        ]
                    }
                )
                .sort("created_at", -1)
                .limit(100)
            )

            user_cache: Dict[str, Dict[str, Any]] = {}
            formatted = [MessagesService._format_message(m, user_cache) for m in messages]

            return {"messages": formatted, "total_messages": len(formatted)}, None

        except Exception as exc:
            return None, f"Failed to get messages: {str(exc)}"

    @staticmethod
    def send_message(
        sender_id: str,
        content: str,
        receiver_id: Optional[str] = None,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        try:
            if not content:
                return None, "Message content is required"

            sender = MessagesService._get_user(sender_id)
            if not sender:
                return None, "Sender not found"

            target_receiver_id = receiver_id or MessagesService._resolve_partner_id(sender)
            if not target_receiver_id:
                return None, "No partner connected and no recipient specified"

            receiver = MessagesService._get_user(target_receiver_id)
            if not receiver:
                return None, "Recipient not found"

            message_doc = {
                "content": content,
                "sender_id": sender_id,
                "receiver_id": target_receiver_id,
                "created_at": datetime.utcnow(),
                "is_read": False,
            }

            result = mongo.db.messages.insert_one(message_doc)
            message_doc["_id"] = result.inserted_id

            # Send email notification if enabled
            if receiver.get("email_notifications", True):
                try:
                    send_partner_message(receiver["email"], sender.get("name", "Your partner"), content)
                except Exception:
                    # Swallow email errors so we don't block the main flow
                    pass

            formatted = MessagesService._format_message(message_doc, {sender_id: sender, target_receiver_id: receiver})

            return {
                "message": "Message sent successfully",
                "data": formatted,
            }, None

        except Exception as exc:
            return None, f"Failed to send message: {str(exc)}"

    @staticmethod
    def schedule_message(
        sender_id: str,
        content: str,
        scheduled_for: str,
        receiver_id: Optional[str] = None,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        try:
            if not content:
                return None, "Message content is required"

            if not scheduled_for:
                return None, "Scheduled time is required"

            sender = MessagesService._get_user(sender_id)
            if not sender:
                return None, "Sender not found"

            target_receiver_id = receiver_id or MessagesService._resolve_partner_id(sender)
            if not target_receiver_id:
                return None, "No partner connected and no recipient specified"

            receiver = MessagesService._get_user(target_receiver_id)
            if not receiver:
                return None, "Recipient not found"

            try:
                parsed_time = datetime.fromisoformat(
                    scheduled_for.replace("Z", "+00:00")
                )
            except ValueError:
                return None, "Invalid scheduled time format"

            # Normalize to UTC naive datetime for compatibility with the worker
            if parsed_time.tzinfo:
                scheduled_time = parsed_time.astimezone(timezone.utc).replace(tzinfo=None)
            else:
                scheduled_time = parsed_time

            scheduled_doc = {
                "content": content,
                "sender_id": sender_id,
                "receiver_id": target_receiver_id,
                "scheduled_time": scheduled_time,
                "created_at": datetime.utcnow(),
                "status": "pending",
            }

            result = mongo.db.scheduled_messages.insert_one(scheduled_doc)
            scheduled_doc["_id"] = result.inserted_id

            return {
                "message": "Message scheduled successfully",
                "data": {
                    "_id": str(scheduled_doc["_id"]),
                    "content": content,
                    "scheduled_for": scheduled_time.isoformat() + "Z",
                    "sender_name": sender.get("name", ""),
                    "status": scheduled_doc["status"],
                },
            }, None

        except Exception as exc:
            return None, f"Failed to schedule message: {str(exc)}"

    @staticmethod
    def get_scheduled_messages(user_id: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        try:
            sender = MessagesService._get_user(user_id)
            if not sender:
                return None, "User not found"

            scheduled = list(
                mongo.db.scheduled_messages.find({"sender_id": user_id}).sort("scheduled_time", 1)
            )

            formatted: List[Dict[str, Any]] = []
            for doc in scheduled:
                scheduled_time = doc.get("scheduled_time")
                if isinstance(scheduled_time, datetime):
                    scheduled_str = scheduled_time.isoformat() + "Z"
                else:
                    scheduled_str = scheduled_time

                formatted.append(
                    {
                        "_id": str(doc["_id"]),
                        "content": doc.get("content", ""),
                        "scheduled_for": scheduled_str,
                        "sender_name": sender.get("name", ""),
                        "status": doc.get("status", "pending"),
                    }
                )

            return {"scheduled_messages": formatted}, None

        except Exception as exc:
            return None, f"Failed to load scheduled messages: {str(exc)}"

    @staticmethod
    def cancel_scheduled_message(user_id: str, message_id: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        try:
            db_id = MessagesService._safe_object_id(message_id)
            if not db_id:
                return None, "Invalid message id"

            result = mongo.db.scheduled_messages.update_one(
                {"_id": db_id, "sender_id": user_id, "status": "pending"},
                {"$set": {"status": "cancelled", "cancelled_at": datetime.utcnow()}},
            )

            if result.modified_count == 0:
                return None, "No pending scheduled message found"

            return {"message": "Scheduled message cancelled successfully"}, None

        except Exception as exc:
            return None, f"Failed to cancel scheduled message: {str(exc)}"

    @staticmethod
    def get_conversation(user_id: str, partner_id: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        try:
            messages = list(
                mongo.db.messages.find(
                    {
                        "$or": [
                            {"sender_id": user_id, "receiver_id": partner_id},
                            {"sender_id": partner_id, "receiver_id": user_id},
                        ]
                    }
                ).sort("created_at", 1)
            )

            user_cache: Dict[str, Dict[str, Any]] = {}
            formatted = [MessagesService._format_message(m, user_cache) for m in messages]

            mongo.db.messages.update_many(
                {"sender_id": partner_id, "receiver_id": user_id, "is_read": False},
                {"$set": {"is_read": True}},
            )

            return {
                "messages": formatted,
                "conversation_with": partner_id,
                "total_messages": len(formatted),
            }, None

        except Exception as exc:
            return None, f"Failed to get conversation: {str(exc)}"

    @staticmethod
    def get_unread_count(user_id: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        try:
            count = mongo.db.messages.count_documents({"receiver_id": user_id, "is_read": False})
            return {"unread_count": count}, None
        except Exception as exc:
            return None, f"Failed to get unread count: {str(exc)}"
