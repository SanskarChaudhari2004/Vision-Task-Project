"""Authentication and authorization helpers with password support and re-auth."""
from functools import wraps
from flask import request, jsonify, session
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from .models import User

# ---------------------------------------------------------------------------
# In-memory user store with hashed passwords
# Passwords are hashed using Werkzeug's pbkdf2:sha256
# In production: replace with a real database
# ---------------------------------------------------------------------------
USERS = {
    "admin": User(
        username="admin",
        password_hash=generate_password_hash("Admin123!"),
        roles=["admin", "manager"],
        department="Administration",
        can_view_high_sensitivity=True,
        can_view_medium_sensitivity=True,
    ),
    "manager": User(
        username="manager",
        password_hash=generate_password_hash("Manager123!"),
        roles=["manager", "user"],
        department="Clinic",
        can_view_high_sensitivity=True,
        can_view_medium_sensitivity=True,
    ),
    "clerk": User(
        username="clerk",
        password_hash=generate_password_hash("Clerk123!"),
        roles=["user"],
        department="Clinic",
        can_view_high_sensitivity=False,
        can_view_medium_sensitivity=True,
    ),
    "staff": User(
        username="staff",
        password_hash=generate_password_hash("Staff123!"),
        roles=["user"],
        department="Billing",
        can_view_high_sensitivity=False,
        can_view_medium_sensitivity=False,
    ),
}

# Re-auth session duration (minutes) — matches SRS UC-5 requirement
REAUTH_TIMEOUT_MINUTES = 15


def verify_password(username: str, password: str) -> bool:
    """Verify a username/password pair against the user store."""
    user = USERS.get(username)
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
        auth_header = request.headers.get("Authorization", "")
        token = auth_header.replace("Bearer ", "").strip()
        user = USERS.get(token)
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
