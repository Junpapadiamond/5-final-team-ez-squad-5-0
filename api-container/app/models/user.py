from datetime import datetime
from bson.objectid import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash
from .. import mongo


class User:
    def __init__(self, name, email, password, partner_email=None):
        self.name = name
        self.email = email
        self.password_hash = generate_password_hash(password)
        self.partner_email = partner_email
        self.email_notifications = True
        self.created_at = datetime.utcnow()

    def to_dict(self):
        return {
            "name": self.name,
            "email": self.email,
            "password_hash": self.password_hash,
            "partner_email": self.partner_email,
            "email_notifications": self.email_notifications,
            "created_at": self.created_at
        }

    @staticmethod
    def serialize(user):
        if not user:
            return None

        serialized = {}
        for key, value in user.items():
            if key == "_id":
                serialized[key] = str(value)
            elif isinstance(value, ObjectId):
                serialized[key] = str(value)
            elif isinstance(value, datetime):
                serialized[key] = value.isoformat()
            else:
                serialized[key] = value
        return serialized

    @staticmethod
    def find_by_email(email):
        user = mongo.db.users.find_one({"email": email})
        return User.serialize(user)

    @staticmethod
    def find_by_id(user_id):
        try:
            user = mongo.db.users.find_one({"_id": ObjectId(user_id)})
            return User.serialize(user)
        except:
            return None

    @staticmethod
    def create(name, email, password, partner_email=None):
        user_obj = User(name, email, password, partner_email)
        result = mongo.db.users.insert_one(user_obj.to_dict())

        user_dict = user_obj.to_dict()
        user_dict["_id"] = str(result.inserted_id)
        return User.serialize(user_dict)

    @staticmethod
    def verify_password(user, password):
        return check_password_hash(user["password_hash"], password)

    @staticmethod
    def update(user_id, updates):
        try:
            result = mongo.db.users.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": updates}
            )
            return result.modified_count > 0
        except:
            return False
