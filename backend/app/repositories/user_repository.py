"""Database queries for users."""

from app.extensions import db, or_
from app.models import LoginHistory, User
from app.utils.request_context import get_request_info


class UserRepository:
    @staticmethod
    def find_by_identifier(identifier):
        return User.query.filter(
            or_(
                db.func.lower(User.username) == identifier.lower(),
                db.func.lower(User.email) == identifier.lower(),
            )
        ).first()

    @staticmethod
    def find_by_id(user_id):
        return db.session.get(User, user_id)

    @staticmethod
    def record_login_event(user_id, event, ip_address=None, user_agent=None):
        info = get_request_info()
        entry = LoginHistory(
            user_id=user_id,
            event=event,
            ip_address=ip_address or info.get("ip_address"),
            user_agent=user_agent or info.get("user_agent"),
        )
        db.session.add(entry)
        db.session.commit()
        return entry
