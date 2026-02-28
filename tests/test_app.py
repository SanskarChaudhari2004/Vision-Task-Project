import pytest
from vision_task import create_app


@pytest.fixture
def app():
    app = create_app()
    app.config.update({"TESTING": True})
    return app


@pytest.fixture
def client(app):
    return app.test_client()


def test_index(client):
    res = client.get("/")
    assert res.status_code == 200
    assert b"Vision Task API is running" in res.data


def test_unauthenticated_list(client):
    res = client.get("/tasks")
    assert res.status_code == 401


def test_create_and_list_task(client):
    headers = {"Authorization": "Bearer admin"}
    # create task
    res = client.post(
        "/tasks",
        json={"title": "Test", "description": "desc", "sensitivity": "low"},
        headers=headers,
    )
    assert res.status_code == 201
    # list tasks
    res2 = client.get("/tasks", headers=headers)
    assert res2.status_code == 200
    assert len(res2.json) == 1
    assert res2.json[0]["title"] == "Test"


def test_ui_dashboard(client):
    # initial dashboard should work even without auth
    res = client.get("/dashboard")
    assert res.status_code == 200
    assert b"Tasks" in res.data


def test_ui_create_task(client):
    # submit form to create task via UI
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
