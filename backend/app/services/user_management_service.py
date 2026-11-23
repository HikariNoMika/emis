"""User account administration and self-service profile editing."""

from app.extensions import db
from app.models import User
from app.utils.serializers import user_to_dict
from app.utils.security import hash_password

from .audit_service import log_action
from .exceptions import ConflictError, NotFoundError, ValidationAppError


def list_users(filters, page, per_page):
    from app.extensions import or_

    query = User.query
    if filters.get("search"):
        term = f"%{filters['search']}%"
        query = query.filter(
            or_(
                User.username.ilike(term),
                User.email.ilike(term),
                User.full_name.ilike(term),
            )
        )
    if filters.get("role"):
        query = query.filter_by(role=filters["role"])
    if filters.get("is_active") is not None:
        query = query.filter_by(is_active=filters["is_active"])
    return query.order_by(User.id).paginate(
        page=page, per_page=per_page, error_out=False
    )


def get_user(user_id):
    user = db.session.get(User, user_id)
    if user is None:
        raise NotFoundError("User not found.")
    return user


def _validate_unique(username=None, email=None, exclude_id=None):
    if username:
        query = User.query.filter_by(username=username)
        if exclude_id:
            query = query.filter(User.id != exclude_id)
        if query.first():
            raise ConflictError("That username is already in use.")
    if email:
        query = User.query.filter_by(email=email)
        if exclude_id:
            query = query.filter(User.id != exclude_id)
        if query.first():
            raise ConflictError("That email is already in use.")


def create_user(data, actor_id):
    _validate_unique(data["username"], data["email"])
    user = User(
        username=data["username"],
        email=data["email"],
        full_name=data["full_name"],
        password_hash=hash_password(data["password"]),
        role=data.get("role", "admin"),
        is_active=data.get("is_active", True),
        must_change_password=True,
    )
    db.session.add(user)
    db.session.flush()
    log_action("USER_CREATED", "users", user.id,
               new_values=user_to_dict(user), user_id=actor_id, commit=False)
    db.session.commit()
    return user


def update_user(user, data, actor_id):
    previous = user_to_dict(user)
    _validate_unique(
        data.get("username"), data.get("email"), exclude_id=user.id
    )
    for field in ("username", "email", "full_name", "role", "is_active"):
        if field in data and data[field] is not None:
            setattr(user, field, data[field])
    log_action("USER_UPDATED", "users", user.id,
               previous_values=previous, new_values=user_to_dict(user),
               user_id=actor_id, commit=False)
    db.session.commit()
    return user


def set_active(user, is_active, actor_id):
    if user.is_active == is_active:
        return user
    previous = user_to_dict(user)
    user.is_active = is_active
    log_action(
        "USER_ACTIVATED" if is_active else "USER_DEACTIVATED",
        "users", user.id, previous_values=previous,
        new_values=user_to_dict(user), user_id=actor_id, commit=False,
    )
    db.session.commit()
    return user


def reset_password(user, new_password, actor_id, must_change=True):
    user.password_hash = hash_password(new_password)
    user.must_change_password = must_change
    log_action("USER_PASSWORD_RESET", "users", user.id,
               user_id=actor_id, commit=False)
    db.session.commit()
    return user


def update_own_profile(user, full_name, email, actor_id=None):
    """Let any authenticated user edit their own name and email."""
    previous = user_to_dict(user)
    _validate_unique(email=email, exclude_id=user.id)
    user.full_name = full_name
    user.email = email
    log_action("PROFILE_UPDATED", "users", user.id,
               previous_values=previous, new_values=user_to_dict(user),
               user_id=actor_id or user.id, commit=False)
    db.session.commit()
    return user
