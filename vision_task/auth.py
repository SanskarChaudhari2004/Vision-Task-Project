"""Authentication and authorization helpers with password support and re-auth."""
from functools import wraps
from flask import request, jsonify, session
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from .models import User
from .db import get_user as db_get_user, list_users as db_list_users, insert_user as db_insert_user, delete_user as db_delete_user

# Default demo users (seeded into the DB on first access)
DEMO_USERS = [
    User(
        username="admin",
        password_hash=generate_password_hash("Admin123!"),
        roles=["admin", "manager"],
        department="Administration",
        can_view_high_sensitivity=True,
        can_view_medium_sensitivity=True,
    ),
    User(
        username="manager",
        password_hash=generate_password_hash("Manager123!"),
        roles=["manager", "user"],
        department="Clinic",
        can_view_high_sensitivity=True,
        can_view_medium_sensitivity=True,
    ),
    User(
        username="clerk",
        password_hash=generate_password_hash("Clerk123!"),
        roles=["user"],
        department="Clinic",
        can_view_high_sensitivity=False,
        can_view_medium_sensitivity=True,
    ),
    User(
        username="staff",
        password_hash=generate_password_hash("Staff123!"),
        roles=["user"],
        department="Billing",
        can_view_high_sensitivity=False,
        can_view_medium_sensitivity=False,
    ),
    User(
        username="doctor",
        password_hash=generate_password_hash("Doctor123!"),
        roles=["doctor", "user"],
        department="Clinic",
        can_view_high_sensitivity=True,
        can_view_medium_sensitivity=True,
    ),
    User(
        username="nurse",
        password_hash=generate_password_hash("Nurse123!"),
        roles=["nurse", "user"],
        department="Clinic",
        can_view_high_sensitivity=False,
        can_view_medium_sensitivity=True,
    ),
]

# Re-auth session duration (minutes) — matches SRS UC-5 requirement
REAUTH_TIMEOUT_MINUTES = 15


def _ensure_demo_users():
    """Ensure demo users exist in the database."""
    for u in DEMO_USERS:
        existing = db_get_user(u.username)
        if not existing:
            db_insert_user(u)


def verify_password(username: str, password: str) -> bool:
    """Verify a username/password pair against the user store."""
    _ensure_demo_users()
    user = db_get_user(username)
    if not user:
        return False
    return check_password_hash(user.password_hash, password)


def is_reauth_valid() -> bool:
    """
    Check if the user has a valid re-authentication session still active.
    Re-auth expires after REAUTH_TIMEOUT_MINUTES of inactivity (UC-5).
    """
    reauth_time = session.get("reauth_timestamp")
    if not reauth_time:
        return False
    elapsed = datetime.utcnow() - datetime.fromisoformat(reauth_time)
    return elapsed < timedelta(minutes=REAUTH_TIMEOUT_MINUTES)


def set_reauth_session():
    """Record the current time as the last re-authentication timestamp."""
    session["reauth_timestamp"] = datetime.utcnow().isoformat()


def clear_reauth_session():
    """Clear re-authentication state (e.g., on logout)."""
    session.pop("reauth_timestamp", None)


def authenticate(f):
    """Decorator: validate Bearer token for API routes."""
    @wraps(f)
    def decorated(*args, **kwargs):
        _ensure_demo_users()
        auth_header = request.headers.get("Authorization", "")
        token = auth_header.replace("Bearer ", "").strip()
        user = db_get_user(token)
        if not user:
            return jsonify({"error": "Unauthorized"}), 401
        return f(user, *args, **kwargs)
    return decorated


def require_role(role):
    """Decorator: enforce role-based access control."""
    def decorator(f):
        @wraps(f)
        def wrapped(user, *args, **kwargs):
            if role not in user.roles:
                return jsonify({"error": "Forbidden"}), 403
            return f(user, *args, **kwargs)
        return wrapped
    return decorator


def list_users() -> list[User]:
    """Get all users, seeding demo users if needed."""
    _ensure_demo_users()
    return db_list_users()


def create_user(user: User):
    """Create a new user."""
    _ensure_demo_users()
    db_insert_user(user)


def get_user(username: str) -> User | None:
    """Get a user by username."""
    _ensure_demo_users()
    return db_get_user(username)


def delete_user(username: str):
    """Delete a user."""
    return db_delete_user(username)
