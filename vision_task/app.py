"""Flask application factory for Vision Task."""
from flask import Flask, jsonify, request, render_template, redirect, url_for
from .auth import require_role, authenticate, USERS
from .tasks import TaskManager
from .logger import activity_logger


def create_app():
    app = Flask(__name__)
    task_manager = TaskManager()

    @app.route("/", methods=["GET"])
    def index():
        return jsonify({"message": "Vision Task API is running"})

    @app.route("/tasks", methods=["GET"])
    @authenticate
    def list_tasks(user):
        tasks = task_manager.list_tasks(user)
        return jsonify([t.to_dict() for t in tasks])

    @app.route("/tasks", methods=["POST"])
    @authenticate
    def create_task(user):
        data = request.json or {}
        task = task_manager.create_task(user, data)
        activity_logger.info(f"User {user.username} created task {task.title}")
        return jsonify(task.to_dict()), 201

    # --- UI routes -------------------------------------------------
    @app.route("/dashboard", methods=["GET"])
    def ui_dashboard():
        # For simplicity we show all tasks without auth
        tasks = task_manager._tasks
        # convert to dicts for template
        return render_template("dashboard.html", tasks=[t.to_dict() for t in tasks])

    @app.route("/dashboard", methods=["POST"])
    def ui_create_task():
        # no auth in UI demo; in a real app you'd integrate login
        form = request.form
        data = {
            "title": form.get("title", ""),
            "description": form.get("description", ""),
            "sensitivity": form.get("sensitivity", "low"),
        }
        # fake user
        user = USERS.get("admin")
        task = task_manager.create_task(user, data)
        activity_logger.info(f"UI: created task {task.title}")
        return redirect(url_for("ui_dashboard"))

    return app
