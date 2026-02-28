"""Authentication and authorization helpers."""
from functools import wraps
from flask import request, jsonify
from .models import User


# In-memory user store for demo purposes
USERS = {
    "admin": User(username="admin", roles=["admin", "user"]),
    "clerk": User(username="clerk", roles=["user"]),
}


def authenticate(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        token = auth_header.replace("Bearer ", "")
        user = USERS.get(token)
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
