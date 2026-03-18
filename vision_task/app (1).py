"""
Vision Task — Demo-Ready Flask Application
Pre-seeded with realistic healthcare data for presentation purposes.
"""
from flask import (
    Flask, jsonify, request, render_template,
    redirect, url_for, session,
)
from .auth import (
    require_role, authenticate, verify_password,
    is_reauth_valid, set_reauth_session, clear_reauth_session,
    USERS, REAUTH_TIMEOUT_MINUTES,
)
from .tasks import TaskManager
from .logger import activity_logger, AuditLog
from .models import Task, TaskStatus, SensitivityLevel
from datetime import datetime, timedelta
import uuid


def _seed_demo_tasks(task_manager):
    """Pre-load realistic healthcare tasks so the demo looks alive on launch."""
    demo_tasks = [
        Task(
            id=str(uuid.uuid4()),
            title="Patient Consent Form — Johnson, R.",
            description="Verify and file signed HIPAA consent forms for Robert Johnson prior to scheduled procedure on 3/20.",
            sensitivity=SensitivityLevel.HIGH,
            created_by="admin",
            assigned_to="clerk",
            department="Administration",
            status=TaskStatus.IN_PROGRESS,
            priority=2,
            created_at=datetime.utcnow() - timedelta(hours=3),
            updated_at=datetime.utcnow() - timedelta(hours=1),
        ),
        Task(
            id=str(uuid.uuid4()),
            title="Insurance Verification — Blue Cross #4471",
            description="Confirm active coverage and pre-authorization for upcoming MRI procedure.",
            sensitivity=SensitivityLevel.HIGH,
            created_by="manager",
            assigned_to="staff",
            department="Billing",
            status=TaskStatus.ASSIGNED,
            priority=2,
            created_at=datetime.utcnow() - timedelta(hours=5),
            updated_at=datetime.utcnow() - timedelta(hours=5),
        ),
        Task(
            id=str(uuid.uuid4()),
            title="Update Patient Records — Q1 Batch",
            description="Review and update demographic information for Q1 patient intake batch.",
            sensitivity=SensitivityLevel.HIGH,
            created_by="admin",
            assigned_to="clerk",
            department="Clinic",
            status=TaskStatus.NEW,
            priority=1,
            created_at=datetime.utcnow() - timedelta(days=1),
            updated_at=datetime.utcnow() - timedelta(days=1),
        ),
        Task(
            id=str(uuid.uuid4()),
            title="Staff Scheduling — March Week 4",
            description="Coordinate coverage schedule for the administration team for the last week of March.",
            sensitivity=SensitivityLevel.MEDIUM,
            created_by="manager",
            assigned_to="manager",
            department="Administration",
            status=TaskStatus.IN_PROGRESS,
            priority=1,
            created_at=datetime.utcnow() - timedelta(hours=8),
            updated_at=datetime.utcnow() - timedelta(hours=2),
        ),
        Task(
            id=str(uuid.uuid4()),
            title="Insurance Claims — February Reconciliation",
            description="Reconcile February insurance claims against payment ledger.",
            sensitivity=SensitivityLevel.MEDIUM,
            created_by="staff",
            assigned_to="staff",
            department="Billing",
            status=TaskStatus.COMPLETED,
            priority=0,
            created_at=datetime.utcnow() - timedelta(days=3),
            updated_at=datetime.utcnow() - timedelta(days=1),
        ),
        Task(
            id=str(uuid.uuid4()),
            title="HIPAA Training Reminder — New Staff",
            description="Send HIPAA compliance training reminder to all new hires onboarded in February.",
            sensitivity=SensitivityLevel.LOW,
            created_by="admin",
            assigned_to="manager",
            department="Administration",
            status=TaskStatus.ASSIGNED,
            priority=1,
            created_at=datetime.utcnow() - timedelta(days=2),
            updated_at=datetime.utcnow() - timedelta(days=2),
        ),
        Task(
            id=str(uuid.uuid4()),
            title="Order Office Supplies",
            description="Reorder printer paper, toner cartridges, and filing folders.",
            sensitivity=SensitivityLevel.LOW,
            created_by="clerk",
            assigned_to="clerk",
            department="Administration",
            status=TaskStatus.NEW,
            priority=0,
            created_at=datetime.utcnow() - timedelta(hours=12),
            updated_at=datetime.utcnow() - timedelta(hours=12),
        ),
    ]
    for task in demo_tasks:
        task_manager._tasks.append(task)
        AuditLog.log_action(
            "system", "create", "task", task.id,
            sensitivity=task.sensitivity.value,
            details={"title": task.title, "note": "demo seed"},
        )


def create_app():
    app = Flask(__name__)
    app.secret_key = "vision-task-demo-2026"
    task_manager = TaskManager()
    _seed_demo_tasks(task_manager)

    def _get_session_user():
        username = session.get("username")
        return USERS.get(username) if username else None

    def _require_login():
        if not _get_session_user():
            return redirect(url_for("login_page"))
        return None

    # ── API ────────────────────────────────────────────────────────────

    @app.route("/api/tasks", methods=["GET"])
    @authenticate
    def list_tasks_api(user):
        tasks = task_manager.list_tasks(user)
        return jsonify({"tasks": [t.to_dict() for t in tasks], "count": len(tasks),
                        "stats": task_manager.get_stats(user)})

    @app.route("/api/tasks", methods=["POST"])
    @authenticate
    def create_task_api(user):
        return jsonify(task_manager.create_task(user, request.json or {}).to_dict()), 201

    @app.route("/api/tasks/<task_id>", methods=["GET"])
    @authenticate
    def get_task_api(user, task_id):
        task = task_manager.get_task(user, task_id)
        return jsonify(task.to_dict()) if task else (jsonify({"error": "Not found"}), 404)

    @app.route("/api/tasks/<task_id>", methods=["PUT"])
    @authenticate
    def update_task_api(user, task_id):
        task = task_manager.update_task(user, task_id, request.json or {})
        return jsonify(task.to_dict()) if task else (jsonify({"error": "Not found"}), 404)

    @app.route("/api/tasks/<task_id>", methods=["DELETE"])
    @authenticate
    @require_role("admin")
    def delete_task_api(user, task_id):
        return jsonify({"deleted": True}) if task_manager.delete_task(user, task_id) \
               else (jsonify({"error": "Not found"}), 404)

    @app.route("/api/stats", methods=["GET"])
    @authenticate
    def get_stats_api(user):
        return jsonify({"user": user.username, "stats": task_manager.get_stats(user)})

    @app.route("/api/users", methods=["GET"])
    @authenticate
    @require_role("admin")
    def list_users_api(user):
        return jsonify({"users": [
            {"username": u.username, "roles": u.roles, "department": u.department}
            for u in USERS.values()
        ]})

    @app.route("/api/docs")
    def api_docs():
        return jsonify({"version": "1.0", "endpoints": [
            "/api/tasks", "/api/tasks/<id>", "/api/stats", "/api/users"
        ]})

    # ── UI: Login ──────────────────────────────────────────────────────

    @app.route("/")
    def index():
        return redirect(url_for("login_page"))

    @app.route("/login", methods=["GET"])
    def login_page():
        if _get_session_user():
            return redirect(url_for("ui_dashboard"))
        return render_template("login.html")

    @app.route("/login", methods=["POST"])
    def login():
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        if not verify_password(username, password):
            AuditLog.log_action(username, "login", "auth", "session", status="denied")
            return render_template("login.html", error="Invalid username or password"), 401
        session["username"] = username
        AuditLog.log_action(username, "login", "auth", "session")
        return redirect(url_for("ui_dashboard"))

    @app.route("/logout")
    def logout():
        username = session.get("username", "unknown")
        clear_reauth_session()
        session.clear()
        AuditLog.log_action(username, "logout", "auth", "session")
        return redirect(url_for("login_page"))

    # ── UI: Re-auth (UC-5) ─────────────────────────────────────────────

    @app.route("/reauth", methods=["GET"])
    def reauth_page():
        redir = _require_login()
        if redir: return redir
        return render_template("reauth.html",
                               next_url=request.args.get("next", url_for("ui_dashboard")),
                               timeout_minutes=REAUTH_TIMEOUT_MINUTES)

    @app.route("/reauth", methods=["POST"])
    def reauth_submit():
        user = _get_session_user()
        if not user: return redirect(url_for("login_page"))
        password = request.form.get("password", "").strip()
        next_url = request.form.get("next_url", url_for("ui_dashboard"))
        if verify_password(user.username, password):
            set_reauth_session()
            AuditLog.log_action(user.username, "reauth", "auth", "session",
                                details={"result": "success"})
            return redirect(next_url)
        AuditLog.log_action(user.username, "reauth", "auth", "session",
                            status="denied", details={"result": "wrong password"})
        return render_template("reauth.html", next_url=next_url,
                               timeout_minutes=REAUTH_TIMEOUT_MINUTES,
                               error="Incorrect password. Please try again."), 401

    # ── UI: Dashboard (UC-10) ──────────────────────────────────────────

    @app.route("/dashboard", methods=["GET"])
    def ui_dashboard():
        redir = _require_login()
        if redir: return redir
        user = _get_session_user()
        q           = request.args.get("q", "").strip().lower()
        filter_sens = request.args.get("sensitivity", "")
        filter_stat = request.args.get("status", "")
        tasks = task_manager.list_tasks(user)
        if q:           tasks = [t for t in tasks if q in t.title.lower() or q in (t.description or "").lower()]
        if filter_sens: tasks = [t for t in tasks if t.sensitivity.value == filter_sens]
        if filter_stat: tasks = [t for t in tasks if t.status.value == filter_stat]
        return render_template("dashboard.html", user=user,
                               tasks=[t.to_dict() for t in tasks],
                               stats=task_manager.get_stats(user),
                               search_query=q,
                               filter_sensitivity=filter_sens,
                               filter_status=filter_stat)

    @app.route("/dashboard", methods=["POST"])
    def ui_create_task():
        redir = _require_login()
        if redir: return redir
        user = _get_session_user()
        f = request.form
        task_manager.create_task(user, {
            "title": f.get("title",""), "description": f.get("description",""),
            "sensitivity": f.get("sensitivity","low"),
            "assigned_to": f.get("assigned_to") or None,
            "priority": int(f.get("priority", 0)),
        })
        return redirect(url_for("ui_dashboard"))

    # ── UI: Task detail (UC-5, UC-11) ──────────────────────────────────

    @app.route("/task/<task_id>", methods=["GET"])
    def ui_view_task(task_id):
        redir = _require_login()
        if redir: return redir
        user = _get_session_user()
        task = task_manager.get_task(user, task_id)
        if not task:
            return render_template("error.html", user=user,
                                   message="Task not found or access denied."), 404
        if task.sensitivity.value == "high" and not is_reauth_valid():
            AuditLog.log_action(user.username, "reauth_required", "task", task_id)
            return redirect(url_for("reauth_page", next=url_for("ui_view_task", task_id=task_id)))
        return render_template("task_detail.html", task=task.to_dict(), user=user)

    @app.route("/task/<task_id>", methods=["POST"])
    def ui_update_task(task_id):
        redir = _require_login()
        if redir: return redir
        user = _get_session_user()
        task_obj = task_manager.get_task(user, task_id)
        if not task_obj:
            return render_template("error.html", user=user, message="Task not found."), 404
        if task_obj.sensitivity.value == "high" and not is_reauth_valid():
            return redirect(url_for("reauth_page", next=url_for("ui_view_task", task_id=task_id)))
        f = request.form
        data = {k: v for k, v in {
            "title": f.get("title"), "description": f.get("description"),
            "status": f.get("status"), "assigned_to": f.get("assigned_to") or None,
            "priority": int(f.get("priority", 0)),
        }.items() if v is not None}
        task = task_manager.update_task(user, task_id, data)
        if not task:
            return render_template("error.html", user=user,
                                   message="You don't have permission to edit this task."), 403
        return redirect(url_for("ui_view_task", task_id=task_id))

    @app.route("/task/<task_id>/delete", methods=["POST"])
    def ui_delete_task(task_id):
        redir = _require_login()
        if redir: return redir
        user = _get_session_user()
        if "admin" not in user.roles:
            return render_template("error.html", user=user,
                                   message="Only administrators can delete tasks."), 403
        task_obj = task_manager.get_task(user, task_id)
        if task_obj and task_obj.sensitivity.value == "high" and not is_reauth_valid():
            return redirect(url_for("reauth_page", next=url_for("ui_view_task", task_id=task_id)))
        task_manager.delete_task(user, task_id)
        return redirect(url_for("ui_dashboard"))

    # ── UI: Activity Log (UC-6) ────────────────────────────────────────

    @app.route("/activity-log", methods=["GET"])
    def ui_activity_log():
        redir = _require_login()
        if redir: return redir
        user = _get_session_user()
        if "admin" not in user.roles and "manager" not in user.roles:
            return render_template("error.html", user=user,
                                   message="You don't have permission to view activity logs."), 403
        entries       = _parse_activity_log()
        filter_user   = request.args.get("filter_user","").strip()
        filter_action = request.args.get("filter_action","").strip()
        filter_status = request.args.get("filter_status","").strip()
        if filter_user:   entries = [e for e in entries if filter_user.lower() in e.get("user_id","").lower()]
        if filter_action: entries = [e for e in entries if e.get("action") == filter_action]
        if filter_status: entries = [e for e in entries if e.get("status") == filter_status]
        if request.args.get("export") == "txt":
            from flask import Response
            raw = open("activity_log.txt").read() if __import__("os").path.exists("activity_log.txt") else ""
            AuditLog.log_action(user.username, "export", "activity_log", "all")
            return Response(raw, mimetype="text/plain",
                            headers={"Content-Disposition": "attachment; filename=activity_log.txt"})
        unique_users   = sorted(set(e.get("user_id","")  for e in entries if e.get("user_id")))
        unique_actions = sorted(set(e.get("action","")   for e in entries if e.get("action")))
        return render_template("activity_log.html", user=user, entries=entries[:500],
                               total=len(entries), filter_user=filter_user,
                               filter_action=filter_action, filter_status=filter_status,
                               unique_users=unique_users, unique_actions=unique_actions)

    def _parse_activity_log():
        import json
        entries = []
        try:
            with open("activity_log.txt") as f:
                for line in f:
                    line = line.strip()
                    if not line: continue
                    try:
                        entries.append(json.loads(line.split(" | ")[-1]))
                    except Exception:
                        entries.append({"timestamp":"","user_id":"system","action":"raw",
                                        "resource_type":"","resource_id":"","status":"info",
                                        "details":{"raw": line}})
        except FileNotFoundError:
            pass
        return list(reversed(entries))

    # ── UI: Role Management (UC-9) ─────────────────────────────────────

    @app.route("/users", methods=["GET"])
    def ui_users():
        redir = _require_login()
        if redir: return redir
        user = _get_session_user()
        if "admin" not in user.roles:
            return render_template("error.html", user=user,
                                   message="Only administrators can manage users."), 403
        return render_template("users.html", user=user,
                               users=list(USERS.values()),
                               success_msg=request.args.get("success"))

    @app.route("/users/<username>/role", methods=["POST"])
    def ui_update_role(username):
        redir = _require_login()
        if redir: return redir
        actor = _get_session_user()
        if "admin" not in actor.roles:
            return render_template("error.html", user=actor,
                                   message="Only administrators can modify roles."), 403
        target = USERS.get(username)
        if not target:
            return render_template("error.html", user=actor,
                                   message=f"User '{username}' not found."), 404
        new_roles = [r for r in request.form.getlist("roles") if r in {"admin","manager","user"}]
        if not new_roles:
            return render_template("users.html", user=actor, users=list(USERS.values()),
                                   error_msg="At least one role must be selected.")
        if "admin" in target.roles and "admin" not in new_roles:
            if sum(1 for u in USERS.values() if "admin" in u.roles) <= 1:
                return render_template("users.html", user=actor, users=list(USERS.values()),
                                       error_msg="Cannot remove the last system administrator.")
        old_roles = target.roles[:]
        target.roles = new_roles
        target.can_view_high_sensitivity  = "admin" in new_roles or "manager" in new_roles
        target.can_view_medium_sensitivity = True
        AuditLog.log_action(actor.username, "update_role", "user", username,
                            details={"previous_roles": old_roles, "new_roles": new_roles})
        return redirect(url_for("ui_users",
                                success=f"Role for '{username}' updated successfully."))

    return app
