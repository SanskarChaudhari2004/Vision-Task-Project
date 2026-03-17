"""Flask application factory for Vision Task with full SRS feature coverage."""
from flask import (
    Flask, jsonify, request, render_template,
    redirect, url_for, session,
)
from .auth import (
    require_role, authenticate, verify_password,
    is_reauth_valid, set_reauth_session, clear_reauth_session,
    get_user, list_users, create_user, delete_user, REAUTH_TIMEOUT_MINUTES,
)
from werkzeug.security import generate_password_hash
from .tasks import TaskManager
from .logger import activity_logger, AuditLog


def create_app():
    app = Flask(__name__)
    app.secret_key = "dev-secret-key-change-in-production"
    task_manager = TaskManager()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_session_user():
        username = session.get("username")
        return get_user(username) if username else None

    def _require_login():
        """Return redirect if not logged in, else None."""
        if not _get_session_user():
            return redirect(url_for("login_page"))
        return None

    # ------------------------------------------------------------------
    # Core API Routes
    # ------------------------------------------------------------------

    @app.route("/", methods=["GET"])
    def index():
        return jsonify({"message": "Vision Task API", "version": "1.0", "docs": "/api/docs"})

    @app.route("/api/tasks", methods=["GET"])
    @authenticate
    def list_tasks(user):
        tasks = task_manager.list_tasks(user)
        return jsonify({
            "tasks": [t.to_dict() for t in tasks],
            "count": len(tasks),
            "stats": task_manager.get_stats(user),
        })

    @app.route("/api/tasks", methods=["POST"])
    @authenticate
    def create_task_api(user):
        data = request.json or {}
        task = task_manager.create_task(user, data)
        return jsonify(task.to_dict()), 201

    @app.route("/api/tasks/<task_id>", methods=["GET"])
    @authenticate
    def get_task_api(user, task_id):
        task = task_manager.get_task(user, task_id)
        if not task:
            return jsonify({"error": "Task not found or access denied"}), 404
        return jsonify(task.to_dict())

    @app.route("/api/tasks/<task_id>", methods=["PUT"])
    @authenticate
    def update_task_api(user, task_id):
        data = request.json or {}
        task = task_manager.update_task(user, task_id, data)
        if not task:
            return jsonify({"error": "Task not found or access denied"}), 404
        return jsonify(task.to_dict())

    @app.route("/api/tasks/<task_id>", methods=["DELETE"])
    @authenticate
    @require_role("admin")
    def delete_task_api(user, task_id):
        success = task_manager.delete_task(user, task_id)
        if not success:
            return jsonify({"error": "Task not found"}), 404
        return jsonify({"deleted": True}), 200

    @app.route("/api/stats", methods=["GET"])
    @authenticate
    def get_stats_api(user):
        return jsonify({"user": user.username, "department": user.department,
                        "stats": task_manager.get_stats(user)})

    @app.route("/api/users", methods=["GET"])
    @authenticate
    @require_role("admin")
    def list_users_api(user):
        users = list_users()
        users_list = [
            {"username": u.username, "roles": u.roles,
             "department": u.department,
             "can_view_high_sensitivity": u.can_view_high_sensitivity}
            for u in users
        ]
        AuditLog.log_action(user.username, "list", "users", "all")
        return jsonify({"users": users_list, "count": len(users_list)})

    @app.route("/api/docs", methods=["GET"])
    def api_docs():
        return jsonify({"endpoints": [
            {"path": "/api/tasks",       "method": "GET",    "auth": True, "description": "List tasks visible to user"},
            {"path": "/api/tasks",       "method": "POST",   "auth": True, "description": "Create new task"},
            {"path": "/api/tasks/<id>",  "method": "GET",    "auth": True, "description": "Get task details"},
            {"path": "/api/tasks/<id>",  "method": "PUT",    "auth": True, "description": "Update task"},
            {"path": "/api/tasks/<id>",  "method": "DELETE", "auth": True, "roles": ["admin"], "description": "Delete task"},
            {"path": "/api/stats",       "method": "GET",    "auth": True, "description": "User task statistics"},
            {"path": "/api/users",       "method": "GET",    "auth": True, "roles": ["admin"], "description": "List all users"},
        ]})

    # ------------------------------------------------------------------
    # UI: Auth Routes
    # ------------------------------------------------------------------

    @app.route("/login", methods=["GET"])
    def login_page():
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

    @app.route("/logout", methods=["GET"])
    def logout():
        username = session.get("username", "unknown")
        clear_reauth_session()
        session.clear()
        AuditLog.log_action(username, "logout", "auth", "session")
        return redirect(url_for("login_page"))

    # ------------------------------------------------------------------
    # UI: Re-authentication (UC-5)
    # ------------------------------------------------------------------

    @app.route("/reauth", methods=["GET"])
    def reauth_page():
        """Display re-authentication dialog before accessing a high-sensitivity task."""
        redir = _require_login()
        if redir:
            return redir
        next_url = request.args.get("next", url_for("ui_dashboard"))
        return render_template("reauth.html", next_url=next_url,
                               timeout_minutes=REAUTH_TIMEOUT_MINUTES)

    @app.route("/reauth", methods=["POST"])
    def reauth_submit():
        """Process re-authentication credentials."""
        user = _get_session_user()
        if not user:
            return redirect(url_for("login_page"))

        password = request.form.get("password", "").strip()
        next_url = request.form.get("next_url", url_for("ui_dashboard"))

        if verify_password(user.username, password):
            set_reauth_session()
            AuditLog.log_action(user.username, "reauth", "auth", "session",
                                details={"next": next_url})
            return redirect(next_url)
        else:
            AuditLog.log_action(user.username, "reauth", "auth", "session",
                                status="denied", details={"reason": "Wrong password"})
            return render_template("reauth.html", next_url=next_url,
                                   timeout_minutes=REAUTH_TIMEOUT_MINUTES,
                                   error="Incorrect password. Please try again."), 401

    # ------------------------------------------------------------------
    # UI: Dashboard with search/filter (UC-10)
    # ------------------------------------------------------------------

    @app.route("/dashboard", methods=["GET"])
    def ui_dashboard():
        redir = _require_login()
        if redir:
            return redir
        user = _get_session_user()

        # Search & filter parameters (UC-10)
        search_query = request.args.get("q", "").strip().lower()
        filter_sensitivity = request.args.get("sensitivity", "")
        filter_status = request.args.get("status", "")
        filter_assigned = request.args.get("assigned_to", "")

        all_tasks = task_manager.list_tasks(user)

        # Apply search
        if search_query:
            all_tasks = [t for t in all_tasks if
                         search_query in t.title.lower() or
                         search_query in (t.description or "").lower()]

        # Apply filters
        if filter_sensitivity:
            all_tasks = [t for t in all_tasks if t.sensitivity.value == filter_sensitivity]
        if filter_status:
            all_tasks = [t for t in all_tasks if t.status.value == filter_status]
        if filter_assigned:
            all_tasks = [t for t in all_tasks if (t.assigned_to or "") == filter_assigned]

        stats = task_manager.get_stats(user)
        return render_template(
            "dashboard.html",
            user=user,
            tasks=[t.to_dict() for t in all_tasks],
            stats=stats,
            search_query=search_query,
            filter_sensitivity=filter_sensitivity,
            filter_status=filter_status,
            filter_assigned=filter_assigned,
            is_doctor="doctor" in user.roles,
            is_nurse="nurse" in user.roles,
        )

    @app.route("/dashboard", methods=["POST"])
    def ui_create_task():
        redir = _require_login()
        if redir:
            return redir
        user = _get_session_user()
        form = request.form
        data = {
            "title": form.get("title", ""),
            "description": form.get("description", ""),
            "sensitivity": form.get("sensitivity", "low"),
            "assigned_to": form.get("assigned_to") or None,
            "priority": int(form.get("priority", 0)),
        }
        task_manager.create_task(user, data)
        return redirect(url_for("ui_dashboard"))

    # ------------------------------------------------------------------
    # UI: Task detail with re-auth gate (UC-5, UC-11)
    # ------------------------------------------------------------------

    @app.route("/task/<task_id>", methods=["GET"])
    def ui_view_task(task_id):
        redir = _require_login()
        if redir:
            return redir
        user = _get_session_user()

        task = task_manager.get_task(user, task_id)
        if not task:
            return render_template("error.html", user=user,
                                   message="Task not found or access denied."), 404

        # UC-5: High-sensitivity tasks require valid re-auth session
        if task.sensitivity.value == "high" and not is_reauth_valid():
            AuditLog.log_action(user.username, "reauth_required", "task", task_id,
                                details={"sensitivity": "high"})
            return redirect(url_for("reauth_page",
                                    next=url_for("ui_view_task", task_id=task_id)))

        return render_template("task_detail.html", task=task.to_dict(), user=user)

    @app.route("/task/<task_id>", methods=["POST"])
    def ui_update_task(task_id):
        redir = _require_login()
        if redir:
            return redir
        user = _get_session_user()

        task_obj = task_manager.get_task(user, task_id)
        if not task_obj:
            return render_template("error.html", user=user,
                                   message="Task not found or access denied."), 404

        # UC-5: Modifications to high-sensitivity tasks also require re-auth
        if task_obj.sensitivity.value == "high" and not is_reauth_valid():
            return redirect(url_for("reauth_page",
                                    next=url_for("ui_view_task", task_id=task_id)))

        form = request.form
        data = {k: v for k, v in {
            "title": form.get("title"),
            "description": form.get("description"),
            "status": form.get("status"),
            "assigned_to": form.get("assigned_to") or None,
            "priority": int(form.get("priority", 0)),
        }.items() if v is not None}

        task = task_manager.update_task(user, task_id, data)
        if not task:
            return render_template("error.html", user=user,
                                   message="You do not have permission to edit this task."), 403
        return redirect(url_for("ui_view_task", task_id=task_id))

    @app.route("/task/<task_id>/delete", methods=["POST"])
    def ui_delete_task(task_id):
        """UC-11: Delete restricted to admins, high-sensitivity requires re-auth."""
        redir = _require_login()
        if redir:
            return redir
        user = _get_session_user()

        if "admin" not in user.roles:
            return render_template("error.html", user=user,
                                   message="Only administrators can delete tasks."), 403

        task_obj = task_manager.get_task(user, task_id)
        if task_obj and task_obj.sensitivity.value == "high" and not is_reauth_valid():
            return redirect(url_for("reauth_page",
                                    next=url_for("ui_view_task", task_id=task_id)))

        task_manager.delete_task(user, task_id)
        return redirect(url_for("ui_dashboard"))

    # ------------------------------------------------------------------
    # UI: Activity Log viewer (UC-6)
    # ------------------------------------------------------------------

    @app.route("/activity-log", methods=["GET"])
    def ui_activity_log():
        redir = _require_login()
        if redir:
            return redir
        user = _get_session_user()

        if "admin" not in user.roles and "manager" not in user.roles:
            return render_template("error.html", user=user,
                                   message="You do not have permission to view activity logs."), 403

        # Parse the flat log file into structured entries
        log_entries = _parse_activity_log()

        # Filter controls
        filter_user = request.args.get("filter_user", "").strip()
        filter_action = request.args.get("filter_action", "").strip()
        filter_status = request.args.get("filter_status", "").strip()

        if filter_user:
            log_entries = [e for e in log_entries if filter_user.lower() in e.get("user_id", "").lower()]
        if filter_action:
            log_entries = [e for e in log_entries if e.get("action") == filter_action]
        if filter_status:
            log_entries = [e for e in log_entries if e.get("status") == filter_status]

        # Export as plain text
        export = request.args.get("export")
        if export == "txt":
            from flask import Response
            raw_lines = []
            try:
                with open("activity_log.txt", "r") as f:
                    raw_lines = f.readlines()
            except FileNotFoundError:
                pass
            AuditLog.log_action(user.username, "export", "activity_log", "all")
            return Response("".join(raw_lines), mimetype="text/plain",
                            headers={"Content-Disposition": "attachment; filename=activity_log.txt"})

        unique_users = sorted(set(e.get("user_id", "") for e in log_entries if e.get("user_id")))
        unique_actions = sorted(set(e.get("action", "") for e in log_entries if e.get("action")))

        return render_template(
            "activity_log.html",
            user=user,
            entries=log_entries[:500],      # cap display at 500
            total=len(log_entries),
            filter_user=filter_user,
            filter_action=filter_action,
            filter_status=filter_status,
            unique_users=unique_users,
            unique_actions=unique_actions,
        )

    def _parse_activity_log():
        """Parse activity_log.txt into a list of dicts for display."""
        import json, re
        entries = []
        try:
            with open("activity_log.txt", "r") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    # Extract the JSON blob after the last ' | '
                    parts = line.split(" | ")
                    json_blob = parts[-1] if parts else ""
                    try:
                        entry = json.loads(json_blob)
                        entries.append(entry)
                    except (json.JSONDecodeError, ValueError):
                        # Fallback: show raw line
                        entries.append({"timestamp": "", "user_id": "system",
                                        "action": "raw", "resource_type": "",
                                        "resource_id": "", "status": "info",
                                        "details": {"raw": line}})
        except FileNotFoundError:
            pass
        return list(reversed(entries))   # most recent first

    # ------------------------------------------------------------------
    # UI: Role Management (UC-9)
    # ------------------------------------------------------------------

    @app.route("/users", methods=["GET"])
    def ui_users():
        """User management panel — admin only."""
        redir = _require_login()
        if redir:
            return redir
        user = _get_session_user()
        if "admin" not in user.roles:
            return render_template("error.html", user=user,
                                   message="Only administrators can manage users."), 403

        success_msg = request.args.get("success")
        return render_template("users.html", user=user,
                               users=list_users(),
                               success_msg=success_msg)

    @app.route("/users/<username>/role", methods=["POST"])
    def ui_update_role(username):
        """UC-9: Update a user's role."""
        redir = _require_login()
        if redir:
            return redir
        actor = _get_session_user()
        if "admin" not in actor.roles:
            return render_template("error.html", user=actor,
                                   message="Only administrators can modify roles."), 403

        target = get_user(username)
        if not target:
            return render_template("error.html", user=actor,
                                   message=f"User '{username}' not found."), 404

        new_roles_raw = request.form.getlist("roles")
        valid_roles = {"admin", "manager", "user", "doctor", "nurse"}
        new_roles = [r for r in new_roles_raw if r in valid_roles]

        if not new_roles:
            return render_template("users.html", user=actor,
                                   users=list_users(),
                                   error_msg="At least one role must be selected.")

        # UC-9 constraint: system must keep at least one active admin
        if "admin" in target.roles and "admin" not in new_roles:
            admin_count = sum(1 for u in list_users() if "admin" in u.roles)
            if admin_count <= 1:
                return render_template("users.html", user=actor,
                                       users=list_users(),
                                       error_msg="Cannot remove the last system administrator.")

        # Also update sensitivity clearances based on role
        # Doctors and managers have high-sensitivity clearance; nurses get medium clearance.
        new_high = "admin" in new_roles or "manager" in new_roles or "doctor" in new_roles
        new_medium = new_high or "user" in new_roles or "nurse" in new_roles

        old_roles = target.roles[:]
        target.roles = new_roles
        target.can_view_high_sensitivity = new_high
        target.can_view_medium_sensitivity = new_medium

        create_user(target)

        AuditLog.log_action(
            actor.username, "update_role", "user", username,
            details={
                "previous_roles": old_roles,
                "new_roles": new_roles,
                "changed_by": actor.username,
            }
        )

        return redirect(url_for("ui_users", success=f"Role for '{username}' updated successfully."))

    @app.route("/users/create", methods=["POST"])
    def ui_create_user():
        """Admin-only user creation."""
        redir = _require_login()
        if redir:
            return redir
        actor = _get_session_user()
        if "admin" not in actor.roles:
            return render_template("error.html", user=actor,
                                   message="Only administrators can create users."), 403
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        department = request.form.get("department", "")
        roles = request.form.getlist("roles")

        if not username or not password:
            return render_template("users.html", user=actor,
                                   users=list_users(),
                                   error_msg="Username and password are required."), 400

        if get_user(username):
            return render_template("users.html", user=actor,
                                   users=list_users(),
                                   error_msg=f"User '{username}' already exists."), 400

        valid_roles = {"admin", "manager", "user", "doctor", "nurse"}
        roles = [r for r in roles if r in valid_roles]
        if not roles:
            roles = ["user"]

        # Determine clearance based on role
        can_view_high = "admin" in roles or "manager" in roles or "doctor" in roles
        can_view_medium = can_view_high or "user" in roles or "nurse" in roles

        new_user = type(actor)(
            username=username,
            password_hash=generate_password_hash(password),
            roles=roles,
            department=department,
            can_view_high_sensitivity=can_view_high,
            can_view_medium_sensitivity=can_view_medium,
        )
        create_user(new_user)

        AuditLog.log_action(
            actor.username, "create", "user", username,
            details={
                "created_by": actor.username,
                "roles": roles,
                "department": department,
            }
        )

        return redirect(url_for("ui_users", success=f"User '{username}' created successfully."))

    @app.route("/users/<username>/delete", methods=["POST"])
    def ui_delete_user(username):
        """Admin-only user deletion."""
        redir = _require_login()
        if redir:
            return redir
        actor = _get_session_user()
        if "admin" not in actor.roles:
            return render_template("error.html", user=actor,
                                   message="Only administrators can delete users."), 403

        if username == actor.username:
            return render_template("users.html", user=actor,
                                   users=list_users(),
                                   error_msg="You cannot delete your own account."), 400

        # Ensure at least one admin remains
        target = get_user(username)
        if not target:
            return render_template("users.html", user=actor,
                                   users=list_users(),
                                   error_msg=f"User '{username}' not found."), 404

        if "admin" in target.roles:
            admin_count = sum(1 for u in list_users() if "admin" in u.roles)
            if admin_count <= 1:
                return render_template("users.html", user=actor,
                                       users=list_users(),
                                       error_msg="Cannot delete the last system administrator."), 400

        delete_user(username)
        AuditLog.log_action(actor.username, "delete", "user", username)
        return redirect(url_for("ui_users", success=f"User '{username}' deleted successfully."))
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        department = request.form.get("department", "")
        roles = request.form.getlist("roles")

        if not username or not password:
            return render_template("users.html", user=actor,
                                   users=list_users(),
                                   error_msg="Username and password are required."), 400

        if get_user(username):
            return render_template("users.html", user=actor,
                                   users=list_users(),
                                   error_msg=f"User '{username}' already exists."), 400

        valid_roles = {"admin", "manager", "user", "doctor", "nurse"}
        roles = [r for r in roles if r in valid_roles]
        if not roles:
            roles = ["user"]

        # Determine clearance based on role
        can_view_high = "admin" in roles or "manager" in roles or "doctor" in roles
        can_view_medium = can_view_high or "user" in roles or "nurse" in roles

        new_user = type(actor)(
            username=username,
            password_hash=generate_password_hash(password),
            roles=roles,
            department=department,
            can_view_high_sensitivity=can_view_high,
            can_view_medium_sensitivity=can_view_medium,
        )
        create_user(new_user)

        AuditLog.log_action(
            actor.username, "create", "user", username,
            details={
                "created_by": actor.username,
                "roles": roles,
                "department": department,
            }
        )

        return redirect(url_for("ui_users", success=f"User '{username}' created successfully."))

    return app
