"""Authentication and authorization helpers with password support and re-auth."""
from functools import wraps
from flask import request, jsonify, session
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from .models import User

# ---------------------------------------------------------------------------
# In-memory user store (fallback when no DB module is present)
# ---------------------------------------------------------------------------
_USERS: dict[str, User] = {}

# Try to import the DB module your teammate added.
# If it doesn't exist yet, we fall back to the in-memory dict gracefully.
try:
    from .db import (
        get_user as db_get_user,
        list_users as db_list_users,
        insert_user as db_insert_user,
        delete_user as db_delete_user,
    )
    _USE_DB = True
except ImportError:
    _USE_DB = False

# ---------------------------------------------------------------------------
# Demo users — includes teammate's doctor + nurse additions
# ---------------------------------------------------------------------------
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

REAUTH_TIMEOUT_MINUTES = 15

# ---------------------------------------------------------------------------
# Internal store helpers
# ---------------------------------------------------------------------------

def _ensure_demo_users():
    """Seed demo users into whichever store is active."""
    for u in DEMO_USERS:
        if _raw_get(u.username) is None:
            _raw_insert(u)


def _raw_get(username: str) -> "User | None":
    if _USE_DB:
        return db_get_user(username)
    return _USERS.get(username)


def _raw_insert(user: User):
    if _USE_DB:
        db_insert_user(user)
    else:
        _USERS[user.username] = user

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_user(username: str) -> "User | None":
    _ensure_demo_users()
    return _raw_get(username)


def list_users() -> list:
    _ensure_demo_users()
    if _USE_DB:
        return db_list_users()
    return list(_USERS.values())


def create_user(user: User):
    _ensure_demo_users()
    _raw_insert(user)


def delete_user(username: str):
    if _USE_DB:
        db_delete_user(username)
    else:
        _USERS.pop(username, None)


def verify_password(username: str, password: str) -> bool:
    _ensure_demo_users()
    user = _raw_get(username)
    if not user:
        return False
    return check_password_hash(user.password_hash, password)


def is_reauth_valid() -> bool:
    reauth_time = session.get("reauth_timestamp")
    if not reauth_time:
        return False
    elapsed = datetime.utcnow() - datetime.fromisoformat(reauth_time)
    return elapsed < timedelta(minutes=REAUTH_TIMEOUT_MINUTES)


def set_reauth_session():
    session["reauth_timestamp"] = datetime.utcnow().isoformat()


def clear_reauth_session():
    session.pop("reauth_timestamp", None)


def authenticate(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        _ensure_demo_users()
        token = request.headers.get("Authorization", "").replace("Bearer ", "").strip()
        user = _raw_get(token)
        if not user:
            return jsonify({"error": "Unauthorized"}), 401
        return f(user, *args, **kwargs)
    return decorated


def require_role(role):
    def decorator(f):
        @wraps(f)
        def wrapped(user, *args, **kwargs):
            if role not in user.roles:
                return jsonify({"error": "Forbidden"}), 403
            return f(user, *args, **kwargs)
        return wrapped
    return decorator
