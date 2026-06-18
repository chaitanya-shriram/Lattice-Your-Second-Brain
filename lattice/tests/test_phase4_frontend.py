"""
Phase 4 tests: Frontend + API integration.
Tests API endpoints that the React UI calls.
"""
import pytest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    from main import app
    return TestClient(app)


def test_health(client):
    r = client.get("/api/health/")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] in ("ok", "degraded")
    assert "db" in data


def test_task_stats_shape(client):
    r = client.get("/api/tasks/stats/summary")
    assert r.status_code == 200
    data = r.json()
    assert "pending" in data
    assert "completed_today" in data
    assert "files" in data
    assert "wiki_pages" in data
    assert "by_bucket" in data
    assert "daily" in data["by_bucket"]


def test_task_crud(client):
    # Create
    r = client.post("/api/tasks/", json={
        "title": "Test task from phase 4",
        "bucket": "daily",
        "priority": "normal",
    })
    assert r.status_code == 201
    task = r.json()
    tid = task["id"]
    assert task["title"] == "Test task from phase 4"
    assert "due_date" in task  # frontend alias

    # List
    r = client.get("/api/tasks/")
    assert r.status_code == 200
    ids = [t["id"] for t in r.json()]
    assert tid in ids

    # Complete
    r = client.post(f"/api/tasks/{tid}/complete")
    assert r.status_code == 200
    assert r.json()["status"] == "done"

    # Delete
    r = client.delete(f"/api/tasks/{tid}")
    assert r.status_code == 204


def test_wiki_list(client):
    r = client.get("/api/wiki/")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_wiki_search(client):
    r = client.get("/api/wiki/search?q=entropy")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_actions_list(client):
    r = client.get("/api/actions/")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_dump_history(client):
    r = client.get("/api/dump/history")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_files_list(client):
    r = client.get("/api/files/")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_frontend_served(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    assert "Lattice" in r.text


def test_spa_routing(client):
    """Non-API paths should serve index.html (SPA routing)."""
    r = client.get("/tasks")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
