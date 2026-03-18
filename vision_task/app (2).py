"""
Vision Task — Merged Flask Application
Combines original features + teammate additions:
  - doctor/nurse roles with clinical quick actions
  - admin can create and delete users
  - filter by assigned_to
  - demo data seeded on startup
Bug fixes applied:
  - removed dead code after return in ui_delete_user
  - duplicate filter alert removed from dashboard
"""
from flask import (
    Flask, jsonify, request, render_template,
    redirect, url_for, session, Response,
)
from werkzeug.security import generate_password_hash
from .auth import (
    require_role, authenticate, verify_password,
    is_reauth_valid, set_reauth_session, clear_reauth_session,
    get_user, list_users, create_user, delete_user,
    REAUTH_TIMEOUT_MINUTES,
)
from .tasks import TaskManager
from .logger import AuditLog
from .models import Task, TaskStatus, SensitivityLevel
from datetime import datetime, timedelta
import os
import uuid


# ---------------------------------------------------------------------------
# Demo seed data
# ---------------------------------------------------------------------------

def _seed_demo_tasks(task_manager):
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
            title="Clinical Assessment — Patient #1042",
            description="Review lab results and prepare clinical notes for patient follow-up appointment.",
            sensitivity=SensitivityLevel.HIGH,
            created_by="doctor",
            assigned_to="doctor",
            department="Clinic",
            status=TaskStatus.IN_PROGRESS,
            priority=2,
            created_at=datetime.utcnow() - timedelta(hours=2),
            updated_at=datetime.utcnow() - timedelta(hours=1),
        ),
        Task(
            id=str(uuid.uuid4()),
            title="Medication Administration Log — Ward B",
            description="Update medication administration records for Ward B patients for the morning shift.",
            sensitivity=SensitivityLevel.MEDIUM,
            created_by="nurse",
            assigned_to="nurse",
            department="Clinic",
            status=TaskStatus.IN_PROGRESS,
            priority=1,
            created_at=datetime.utcnow() - timedelta(hours=4),
            updated_at=datetime.utcnow() - timedelta(hours=2),
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
    # Create demo tasks via the TaskManager so they are persisted and logged.
    for task in demo_tasks:
        task_manager.create_task(get_user(task.created_by), task.to_dict())
        AuditLog.log_action("system", "create", "task", task.id,
                            sensitivity=task.sensitivity.value,
                            details={"title": task.title, "note": "demo seed"})


# ---------------------------------------------------------------------------
# Role → clearance helper (shared by role update + user create)
# ---------------------------------------------------------------------------

def _clearance_from_roles(roles: list) -> tuple:
    """Return (can_view_high, can_view_medium) based on role list."""
    can_high   = any(r in roles for r in ("admin", "manager", "doctor"))
    can_medium = can_high or any(r in roles for r in ("user", "nurse"))
    return can_high, can_medium


VALID_ROLES = {"admin", "manager", "user", "doctor", "nurse"}


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

def create_app():
    app = Flask(__name__, template_folder=os.path.join(os.path.dirname(__file__), "templates"))
    app.secret_key = "vision-task-demo-2026"
    task_manager = TaskManager()
    _seed_demo_tasks(task_manager)

    # ── helpers ─────────────────────────────────────────────────────────

    def _get_session_user():
        username = session.get("username")
        return get_user(username) if username else None

    def _require_login():
        if not _get_session_user():
            return redirect(url_for("login_page"))
        return None

    # ── API ─────────────────────────────────────────────────────────────

    @app.route("/")
    def index():
        return redirect(url_for("login_page"))

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
        return jsonify({"user": user.username, "department": user.department,
                        "stats": task_manager.get_stats(user)})

    @app.route("/api/users", methods=["GET"])
    @authenticate
    @require_role("admin")
    def list_users_api(user):
        AuditLog.log_action(user.username, "list", "users", "all")
        return jsonify({"users": [
            {"username": u.username, "roles": u.roles, "department": u.department,
             "can_view_high_sensitivity": u.can_view_high_sensitivity}
            for u in list_users()
        ]})

    @app.route("/api/docs")
    def api_docs():
        return jsonify({"version": "1.0", "endpoints": [
            "/api/tasks", "/api/tasks/<id>", "/api/stats", "/api/users"
        ]})

    # ── Login / Logout ───────────────────────────────────────────────────

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
            AuditLog.log_action(username, "login", "auth", "session",
                                status="denied", details={"reason": "Invalid credentials"})
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

    # ── Re-auth (UC-5) ───────────────────────────────────────────────────

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

    # ── Dashboard (UC-10) ────────────────────────────────────────────────

    @app.route("/dashboard", methods=["GET"])
    def ui_dashboard():
        redir = _require_login()
        if redir: return redir
        user = _get_session_user()

        q               = request.args.get("q", "").strip().lower()
        filter_sens     = request.args.get("sensitivity", "")
        filter_stat     = request.args.get("status", "")
        filter_assigned = request.args.get("assigned_to", "")   # teammate addition
        sort_by = request.args.get("sort", "")
        sort_order = request.args.get("order", "desc")

        tasks = task_manager.list_tasks(user)
        if q:               tasks = [t for t in tasks if q in t.title.lower() or q in (t.description or "").lower()]
        if filter_sens:     tasks = [t for t in tasks if t.sensitivity.value == filter_sens]
        if filter_stat:     tasks = [t for t in tasks if t.status.value == filter_stat]
        if filter_assigned: tasks = [t for t in tasks if (t.assigned_to or "") == filter_assigned]

        if sort_by == "priority":
            # Higher priority (2) should come first by default.
            reverse = sort_order != "asc"
            tasks = sorted(tasks, key=lambda t: t.priority, reverse=reverse)

        return render_template("dashboard.html", user=user,
                               tasks=[t.to_dict() for t in tasks],
                               stats=task_manager.get_stats(user),
                               search_query=q,
                               filter_sensitivity=filter_sens,
                               filter_status=filter_stat,
                               filter_assigned=filter_assigned,
                               sort_by=sort_by,
                               sort_order=sort_order,
                               is_doctor="doctor" in user.roles,   # teammate addition
                               is_nurse="nurse"  in user.roles)    # teammate addition

    @app.route("/dashboard", methods=["POST"])
    def ui_create_task():
        redir = _require_login()
        if redir: return redir
        user = _get_session_user()
        f = request.form
        task_manager.create_task(user, {
            "title":       f.get("title", ""),
            "description": f.get("description", ""),
            "sensitivity": f.get("sensitivity", "low"),
            "assigned_to": f.get("assigned_to") or None,
            "priority":    int(f.get("priority", 0)),
        })
        return redirect(url_for("ui_dashboard"))

    # ── Task detail (UC-5, UC-11) ────────────────────────────────────────

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
            "title":       f.get("title"),
            "description": f.get("description"),
            "status":      f.get("status"),
            "assigned_to": f.get("assigned_to") or None,
            "priority":    int(f.get("priority", 0)),
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

    # ── Activity Log (UC-6) ──────────────────────────────────────────────

    @app.route("/activity-log", methods=["GET"])
    def ui_activity_log():
        redir = _require_login()
        if redir: return redir
        user = _get_session_user()
        if "admin" not in user.roles and "manager" not in user.roles:
            return render_template("error.html", user=user,
                                   message="You don't have permission to view activity logs."), 403

        entries       = _parse_activity_log()
        filter_user   = request.args.get("filter_user", "").strip()
        filter_action = request.args.get("filter_action", "").strip()
        filter_status = request.args.get("filter_status", "").strip()
        if filter_user:   entries = [e for e in entries if filter_user.lower() in e.get("user_id","").lower()]
        if filter_action: entries = [e for e in entries if e.get("action") == filter_action]
        if filter_status: entries = [e for e in entries if e.get("status") == filter_status]

        if request.args.get("export") == "txt":
            import os
            raw = open("activity_log.txt").read() if os.path.exists("activity_log.txt") else ""
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
        import json, os
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

    # ── User Management (UC-9 + teammate additions) ──────────────────────

    @app.route("/users", methods=["GET"])
    def ui_users():
        redir = _require_login()
        if redir: return redir
        user = _get_session_user()
        if "admin" not in user.roles:
            return render_template("error.html", user=user,
                                   message="Only administrators can manage users."), 403
        return render_template("users.html", user=user, users=list_users(),
                               success_msg=request.args.get("success"),
                               error_msg=request.args.get("error"))

    @app.route("/users/<username>/role", methods=["POST"])
    def ui_update_role(username):
        """UC-9: Update a user's role."""
        redir = _require_login()
        if redir: return redir
        actor = _get_session_user()
        if "admin" not in actor.roles:
            return render_template("error.html", user=actor,
                                   message="Only administrators can modify roles."), 403
        target = get_user(username)
        if not target:
            return render_template("error.html", user=actor,
                                   message=f"User '{username}' not found."), 404

        new_roles = [r for r in request.form.getlist("roles") if r in VALID_ROLES]
        if not new_roles:
            return render_template("users.html", user=actor, users=list_users(),
                                   error_msg="At least one role must be selected.")

        # Prevent removing the last admin
        if "admin" in target.roles and "admin" not in new_roles:
            if sum(1 for u in list_users() if "admin" in u.roles) <= 1:
                return render_template("users.html", user=actor, users=list_users(),
                                       error_msg="Cannot remove the last system administrator.")

        old_roles = target.roles[:]
        target.roles = new_roles
        target.can_view_high_sensitivity, target.can_view_medium_sensitivity = \
            _clearance_from_roles(new_roles)
        create_user(target)   # upsert

        AuditLog.log_action(actor.username, "update_role", "user", username,
                            details={"previous_roles": old_roles, "new_roles": new_roles})
        return redirect(url_for("ui_users",
                                success=f"Role for '{username}' updated successfully."))

    @app.route("/users/create", methods=["POST"])
    def ui_create_user():
        """Admin-only: create a new user account (teammate addition)."""
        redir = _require_login()
        if redir: return redir
        actor = _get_session_user()
        if "admin" not in actor.roles:
            return render_template("error.html", user=actor,
                                   message="Only administrators can create users."), 403

        username   = request.form.get("username", "").strip()
        password   = request.form.get("password", "")
        department = request.form.get("department", "")
        new_roles  = [r for r in request.form.getlist("roles") if r in VALID_ROLES] or ["user"]

        if not username or not password:
            return render_template("users.html", user=actor, users=list_users(),
                                   error_msg="Username and password are required.")
        if get_user(username):
            return render_template("users.html", user=actor, users=list_users(),
                                   error_msg=f"User '{username}' already exists.")

        can_high, can_medium = _clearance_from_roles(new_roles)
        from .models import User as UserModel
        new_user = UserModel(
            username=username,
            password_hash=generate_password_hash(password),
            roles=new_roles,
            department=department,
            can_view_high_sensitivity=can_high,
            can_view_medium_sensitivity=can_medium,
        )
        create_user(new_user)
        AuditLog.log_action(actor.username, "create", "user", username,
                            details={"roles": new_roles, "department": department})
        return redirect(url_for("ui_users",
                                success=f"User '{username}' created successfully."))

    @app.route("/users/<username>/delete", methods=["POST"])
    def ui_delete_user(username):
        """Admin-only: delete a user account (teammate addition). Bug fixed."""
        redir = _require_login()
        if redir: return redir
        actor = _get_session_user()
        if "admin" not in actor.roles:
            return render_template("error.html", user=actor,
                                   message="Only administrators can delete users."), 403
        if username == actor.username:
            return render_template("users.html", user=actor, users=list_users(),
                                   error_msg="You cannot delete your own account.")
        target = get_user(username)
        if not target:
            return render_template("users.html", user=actor, users=list_users(),
                                   error_msg=f"User '{username}' not found.")
        if "admin" in target.roles:
            if sum(1 for u in list_users() if "admin" in u.roles) <= 1:
                return render_template("users.html", user=actor, users=list_users(),
                                       error_msg="Cannot delete the last system administrator.")
        delete_user(username)
        AuditLog.log_action(actor.username, "delete", "user", username)
        return redirect(url_for("ui_users",
                                success=f"User '{username}' deleted successfully."))
        # NOTE: dead code that existed in teammate's version has been removed here.

    return app
