import pytest
from vision_task import create_app
from vision_task.auth import get_user


@pytest.fixture
def app(tmp_path):
    # Use an isolated SQLite file per test to ensure a clean state.
    db_path = tmp_path / "vision_task_test.db"
    import os

    os.environ["VISION_TASK_DB"] = str(db_path)

    app = create_app()
    app.config.update({"TESTING": True})
    return app


@pytest.fixture
def client(app):
    return app.test_client()


def test_index(client):
    # The UI entrypoint redirects unauthenticated users to the login page.
    res = client.get("/")
    assert res.status_code == 302
    assert "/login" in res.headers.get("Location", "")


def test_unauthenticated_list(client):
    res = client.get("/api/tasks")
    assert res.status_code == 401


def test_create_and_list_task(client):
    headers = {"Authorization": "Bearer admin"}

    # create task
    res = client.post(
        "/api/tasks",
        json={"title": "Test", "description": "desc", "sensitivity": "low"},
        headers=headers,
    )
    assert res.status_code == 201
    assert res.json.get("title") == "Test"

    # list tasks
    res2 = client.get("/api/tasks", headers=headers)
    assert res2.status_code == 200
    assert isinstance(res2.json.get("tasks"), list)
    assert any(t["title"] == "Test" for t in res2.json["tasks"])


def test_non_admin_cannot_create_task_api(client):
    headers = {"Authorization": "Bearer manager"}
    res = client.post(
        "/api/tasks",
        json={"title": "Should Fail", "description": "nope", "sensitivity": "low"},
        headers=headers,
    )
    assert res.status_code == 403


def test_advanced_api_filtering(client):
    headers = {"Authorization": "Bearer admin"}

    # Seed a known task shape for advanced filtering.
    create_res = client.post(
        "/api/tasks",
        json={
            "title": "Advanced Filter Target",
            "description": "filter test",
            "sensitivity": "medium",
            "assigned_to": "manager",
            "priority": 2,
        },
        headers=headers,
    )
    assert create_res.status_code == 201

    res = client.get(
        "/api/tasks?created_by=admin&assigned_to=manager&priority_min=2&sort=priority&order=desc",
        headers=headers,
    )
    assert res.status_code == 200

    tasks = res.json.get("tasks", [])
    assert len(tasks) > 0
    assert all(t["created_by"] == "admin" for t in tasks)
    assert all((t.get("assigned_to") or "") == "manager" for t in tasks)
    assert all(t["priority"] >= 2 for t in tasks)


def test_ui_dashboard_redirects_when_unauthenticated(client):
    res = client.get("/dashboard")
    assert res.status_code == 302
    assert "/login" in res.headers.get("Location", "")


def test_ui_create_task_with_login(client):
    # Simulate a logged-in user
    with client.session_transaction() as sess:
        sess["username"] = "admin"

    res = client.post(
        "/dashboard",
        data={
            "title": "UI Task",
            "description": "UI desc",
            "sensitivity": "medium",
        },
        follow_redirects=True,
    )
    assert res.status_code == 200
    assert b"UI Task" in res.data


def test_non_admin_cannot_create_task_ui(client):
    with client.session_transaction() as sess:
        sess["username"] = "manager"

    res = client.post(
        "/dashboard",
        data={
            "title": "Manager Task",
            "description": "should not create",
            "sensitivity": "low",
        },
        follow_redirects=False,
    )
    assert res.status_code == 403


def test_ui_dashboard_shows_clinical_quick_actions_for_doctor(client):
    with client.session_transaction() as sess:
        sess["username"] = "doctor"

    res = client.get("/dashboard")
    assert res.status_code == 200
    assert b"Clinical Quick Actions" in res.data


def test_login_requires_valid_password(client):
    bad = client.post(
        "/login",
        data={"username": "admin", "password": "wrong-password"},
        follow_redirects=False,
    )
    assert bad.status_code == 401

    good = client.post(
        "/login",
        data={"username": "admin", "password": "Admin123!"},
        follow_redirects=False,
    )
    assert good.status_code == 302
    assert "/dashboard" in good.headers.get("Location", "")


def test_admin_can_create_and_delete_user(client):
    with client.session_transaction() as sess:
        sess["username"] = "admin"

    # Create a new user
    res = client.post(
        "/users/create",
        data={
            "username": "testuser",
            "password": "Test1234!",
            "department": "Clinic",
            "roles": ["user"],
        },
        follow_redirects=True,
    )
    if res.status_code != 200:
        print(res.data.decode())
    assert res.status_code == 200
    assert b"created successfully" in res.data

    created_user = get_user("testuser")
    assert created_user is not None
    assert created_user.password_hash.startswith("$2")

    # Delete the new user
    res = client.post(
        "/users/testuser/delete",
        follow_redirects=True,
    )
    assert res.status_code == 200
    assert b"deleted successfully" in res.data
    # Verify we're back on the user management page
    assert b"User Management" in res.data


def test_force_https_redirects_insecure_requests(tmp_path):
    import os

    db_path = tmp_path / "vision_task_https_test.db"
    os.environ["VISION_TASK_DB"] = str(db_path)
    os.environ["VISION_TASK_FORCE_HTTPS"] = "1"

    try:
        app = create_app()
        app.config.update({"TESTING": True})
        client = app.test_client()

        with client.session_transaction() as sess:
            sess["username"] = "admin"

        res = client.get("/dashboard", base_url="http://example.com", follow_redirects=False)
        assert res.status_code == 301
        assert res.headers.get("Location", "").startswith("https://")
    finally:
        os.environ.pop("VISION_TASK_FORCE_HTTPS", None)


def test_performance_analytics_api(client):
    headers = {"Authorization": "Bearer admin"}
    res = client.get("/api/analytics/performance", headers=headers)
    assert res.status_code == 200
    analytics = res.json.get("analytics", {})
    assert "kpis" in analytics
    assert "trend_last_7d" in analytics


def test_ui_performance_analytics_requires_login(client):
    res = client.get("/analytics")
    assert res.status_code == 302
    assert "/login" in res.headers.get("Location", "")


def test_ui_performance_analytics_renders_for_authenticated_user(client):
    with client.session_transaction() as sess:
        sess["username"] = "admin"

    res = client.get("/analytics")
    assert res.status_code == 200
    assert b"Performance Analytics" in res.data


def test_ui_complete_task_marks_task_completed(client):
    with client.session_transaction() as sess:
        sess["username"] = "admin"

    create_res = client.post(
        "/dashboard",
        data={
            "title": "Complete Me",
            "description": "quick complete path",
            "sensitivity": "low",
            "priority": "1",
        },
        follow_redirects=True,
    )
    assert create_res.status_code == 200

    list_res = client.get("/api/tasks", headers={"Authorization": "Bearer admin"})
    target = next((t for t in list_res.json.get("tasks", []) if t["title"] == "Complete Me"), None)
    assert target is not None

    complete_res = client.post(f"/task/{target['id']}/complete", follow_redirects=True)
    assert complete_res.status_code == 200

    detail_res = client.get(f"/api/tasks/{target['id']}", headers={"Authorization": "Bearer admin"})
    assert detail_res.status_code == 200
    assert detail_res.json.get("status") == "completed"


def test_admin_can_bulk_delete_completed_tasks(client):
    with client.session_transaction() as sess:
        sess["username"] = "admin"

    # Create and complete a task.
    create_res = client.post(
        "/dashboard",
        data={
            "title": "Bulk Delete Target",
            "description": "to be completed then deleted",
            "sensitivity": "low",
            "priority": "1",
        },
        follow_redirects=True,
    )
    assert create_res.status_code == 200

    list_res = client.get("/api/tasks", headers={"Authorization": "Bearer admin"})
    target = next((t for t in list_res.json.get("tasks", []) if t["title"] == "Bulk Delete Target"), None)
    assert target is not None

    complete_res = client.post(f"/task/{target['id']}/complete", follow_redirects=True)
    assert complete_res.status_code == 200

    # Bulk delete all completed tasks.
    delete_res = client.post("/tasks/delete-completed", follow_redirects=True)
    assert delete_res.status_code == 200

    get_deleted = client.get(f"/api/tasks/{target['id']}", headers={"Authorization": "Bearer admin"})
    assert get_deleted.status_code == 404


def test_dashboard_default_view_hides_default_sort_filter_summary(client):
    with client.session_transaction() as sess:
        sess["username"] = "admin"

    res = client.get("/dashboard")
    assert res.status_code == 200
    assert b"Showing filtered results" not in res.data


def test_dashboard_non_admin_no_creation_restriction_banner(client):
    with client.session_transaction() as sess:
        sess["username"] = "manager"

    res = client.get("/dashboard")
    assert res.status_code == 200
    assert b"Task creation is restricted to administrators." not in res.data
