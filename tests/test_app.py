import pytest
from vision_task import create_app


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


def test_ui_dashboard_shows_clinical_quick_actions_for_doctor(client):
    with client.session_transaction() as sess:
        sess["username"] = "doctor"

    res = client.get("/dashboard")
    assert res.status_code == 200
    assert b"Clinical Quick Actions" in res.data


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

    # Delete the new user
    res = client.post(
        "/users/testuser/delete",
        follow_redirects=True,
    )
    assert res.status_code == 200
    assert b"deleted successfully" in res.data
    # Verify we're back on the user management page
    assert b"User Management" in res.data
