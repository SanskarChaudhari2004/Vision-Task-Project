"""Flask application factory for Vision Task with healthcare features."""
from flask import (
    Flask,
    jsonify,
    request,
    render_template,
    redirect,
    url_for,
    session,
)
from .auth import require_role, authenticate, USERS
from .tasks import TaskManager
from .logger import activity_logger, AuditLog


def create_app():
    app = Flask(__name__)
    app.secret_key = "dev-secret-key-change-in-production"
    task_manager = TaskManager()

    # ==================== API Routes ====================

    @app.route("/", methods=["GET"])
    def index():
        return jsonify(
            {
                "message": "Vision Task API is running",
                "version": "1.0",
                "docs": "/api/docs",
            }
        )

    @app.route("/api/tasks", methods=["GET"])
    @authenticate
    def list_tasks(user):
        """List tasks visible to the authenticated user."""
        tasks = task_manager.list_tasks(user)
        return jsonify(
            {
                "tasks": [t.to_dict() for t in tasks],
                "count": len(tasks),
                "stats": task_manager.get_stats(user),
            }
        )

    @app.route("/api/tasks", methods=["POST"])
    @authenticate
    def create_task(user):
        """Create a new task with sensitivity level and assignment."""
        data = request.json or {}
        task = task_manager.create_task(user, data)
        return jsonify(task.to_dict()), 201

    @app.route("/api/tasks/<task_id>", methods=["GET"])
    @authenticate
    def get_task(user, task_id):
        """Get a specific task."""
        task = task_manager.get_task(user, task_id)
        if not task:
            return jsonify({"error": "Task not found or access denied"}), 404
        return jsonify(task.to_dict())

    @app.route("/api/tasks/<task_id>", methods=["PUT"])
    @authenticate
    def update_task(user, task_id):
        """Update a task (creator or admin only)."""
        data = request.json or {}
        task = task_manager.update_task(user, task_id, data)
        if not task:
            return jsonify({"error": "Task not found or access denied"}), 404
        return jsonify(task.to_dict())

    @app.route("/api/tasks/<task_id>", methods=["DELETE"])
    @authenticate
    @require_role("admin")
    def delete_task_api(user, task_id):
        """Delete a task (admin only)."""
        success = task_manager.delete_task(user, task_id)
        if not success:
            return jsonify({"error": "Task not found"}), 404
        return jsonify({"deleted": True}), 200

    @app.route("/api/stats", methods=["GET"])
    @authenticate
    def get_stats(user):
        """Get task statistics for authenticated user."""
        stats = task_manager.get_stats(user)
        return jsonify({"user": user.username, "department": user.department, "stats": stats})

    @app.route("/api/users", methods=["GET"])
    @authenticate
    @require_role("admin")
    def list_users(user):
        """List all users (admin only)."""
        users_list = [
            {
                "username": u.username,
                "roles": u.roles,
                "department": u.department,
                "can_view_high_sensitivity": u.can_view_high_sensitivity,
            }
            for u in USERS.values()
        ]
        AuditLog.log_action(
            user_id=user.username,
            action="list",
            resource_type="users",
            resource_id="all",
        )
        return jsonify({"users": users_list, "count": len(users_list)})

    # ==================== UI Routes ====================

    @app.route("/login", methods=["GET"])
    def login_page():
        """Render login page."""
        return render_template("login.html")

    @app.route("/login", methods=["POST"])
    def login():
        """Handle login."""
        username = request.form.get("username")
        user = USERS.get(username)

        if not user:
            AuditLog.log_action(
                user_id=username,
                action="login",
                resource_type="auth",
                resource_id="session",
                status="denied",
                reason="Invalid username",
            )
            return render_template("login.html", error="Invalid username"), 401

        session["username"] = username
        AuditLog.log_action(
            user_id=username,
            action="login",
            resource_type="auth",
            resource_id="session",
        )
        return redirect(url_for("ui_dashboard"))

    @app.route("/logout", methods=["GET"])
    def logout():
        """Handle logout."""
        username = session.get("username", "unknown")
        session.clear()
        AuditLog.log_action(
            user_id=username, action="logout", resource_type="auth", resource_id="session"
        )
        return redirect(url_for("login_page"))

    def _get_session_user():
        """Helper to get user from session."""
        username = session.get("username")
        user = USERS.get(username) if username else None
        return user

    @app.route("/dashboard", methods=["GET"])
    def ui_dashboard():
        """Display task dashboard for logged-in user."""
        user = _get_session_user()
        if not user:
            return redirect(url_for("login_page"))

        tasks = task_manager.list_tasks(user)
        stats = task_manager.get_stats(user)

        return render_template(
            "dashboard.html",
            user=user,
            tasks=[t.to_dict() for t in tasks],
            stats=stats,
        )

    @app.route("/dashboard", methods=["POST"])
    def ui_create_task():
        """Create task from UI form."""
        user = _get_session_user()
        if not user:
            return redirect(url_for("login_page"))

        form = request.form
        data = {
            "title": form.get("title", ""),
            "description": form.get("description", ""),
            "sensitivity": form.get("sensitivity", "low"),
            "assigned_to": form.get("assigned_to"),
            "priority": int(form.get("priority", 0)),
        }
        task = task_manager.create_task(user, data)
        return redirect(url_for("ui_dashboard"))

    @app.route("/task/<task_id>", methods=["GET"])
    def ui_view_task(task_id):
        """View a single task."""
        user = _get_session_user()
        if not user:
            return redirect(url_for("login_page"))

        task = task_manager.get_task(user, task_id)
        if not task:
            return render_template("error.html", message="Task not found or access denied"), 404

        return render_template("task_detail.html", task=task.to_dict(), user=user)

    @app.route("/task/<task_id>", methods=["POST"])
    def ui_update_task(task_id):
        """Update a task from UI."""
        user = _get_session_user()
        if not user:
            return redirect(url_for("login_page"))

        form = request.form
        data = {
            "title": form.get("title"),
            "description": form.get("description"),
            "status": form.get("status"),
            "assigned_to": form.get("assigned_to"),
            "priority": int(form.get("priority", 0)),
        }
        task = task_manager.update_task(user, task_id, {k: v for k, v in data.items() if v})
        if not task:
            return render_template("error.html", message="Cannot update task"), 403

        return redirect(url_for("ui_view_task", task_id=task_id))

    @app.route("/api/docs", methods=["GET"])
    def api_docs():
        """API documentation."""
        return jsonify(
            {
                "endpoints": [
                    {"path": "/api/tasks", "method": "GET", "auth": True, "description": "List tasks visible to user"},
                    {"path": "/api/tasks", "method": "POST", "auth": True, "description": "Create new task"},
                    {"path": "/api/tasks/<id>", "method": "GET", "auth": True, "description": "Get task details"},
                    {"path": "/api/tasks/<id>", "method": "PUT", "auth": True, "description": "Update task"},
                    {"path": "/api/tasks/<id>", "method": "DELETE", "auth": True, "roles": ["admin"], "description": "Delete task"},
                    {"path": "/api/stats", "method": "GET", "auth": True, "description": "Get user task statistics"},
                    {"path": "/api/users", "method": "GET", "auth": True, "roles": ["admin"], "description": "List all users"},
                ]
            }
        )

    return app

