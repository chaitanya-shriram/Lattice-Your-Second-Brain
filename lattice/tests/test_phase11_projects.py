"""
Phase 11 tests: Project manager (Asana-style task manager ported from Task Manager app).
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    from main import app
    return TestClient(app)


def test_personal_inbox_seeded(client):
    r = client.get("/api/projects/")
    assert r.status_code == 200
    projects = r.json()
    assert any(p["is_inbox"] for p in projects)


def test_project_crud(client):
    r = client.post("/api/projects/", json={"name": "Test Project", "color": "#4186e0"})
    assert r.status_code == 201
    project = r.json()
    pid = project["id"]
    assert project["name"] == "Test Project"

    r = client.get(f"/api/projects/{pid}")
    assert r.status_code == 200

    r = client.patch(f"/api/projects/{pid}", json={"description": "Updated description"})
    assert r.status_code == 200
    assert r.json()["description"] == "Updated description"

    r = client.delete(f"/api/projects/{pid}")
    assert r.status_code == 204

    r = client.get(f"/api/projects/{pid}")
    assert r.status_code == 404


def test_cannot_delete_inbox(client):
    r = client.get("/api/projects/")
    inbox = next(p for p in r.json() if p["is_inbox"])
    r = client.delete(f"/api/projects/{inbox['id']}")
    assert r.status_code == 400


def test_sections_tasks_dependencies_updates(client):
    r = client.post("/api/projects/", json={"name": "Full Flow Project"})
    pid = r.json()["id"]

    r = client.post(f"/api/projects/{pid}/sections", json={"name": "Backlog"})
    assert r.status_code == 201
    sid = r.json()["id"]

    r = client.post(f"/api/projects/{pid}/tasks", json={"name": "Task A", "section_id": sid, "priority": "High"})
    assert r.status_code == 201
    task_a = r.json()["id"]

    r = client.post(f"/api/projects/{pid}/tasks", json={"name": "Task B", "section_id": sid})
    task_b = r.json()["id"]

    r = client.post(f"/api/projects/tasks/{task_b}/dependencies", json={"depends_on_id": task_a})
    assert r.status_code == 201

    r = client.get(f"/api/projects/{pid}/full")
    assert r.status_code == 200
    full = r.json()
    task_b_data = next(t for t in full["tasks"] if t["id"] == task_b)
    assert task_b_data["blocked"] is True
    assert task_a in task_b_data["depends_on"]

    r = client.patch(f"/api/projects/tasks/{task_a}", json={"completed": True})
    assert r.status_code == 200

    r = client.get(f"/api/projects/{pid}/full")
    task_b_data = next(t for t in r.json()["tasks"] if t["id"] == task_b)
    assert task_b_data["blocked"] is False

    r = client.delete(f"/api/projects/tasks/{task_b}/dependencies/{task_a}")
    assert r.status_code == 204

    r = client.post(f"/api/projects/{pid}/updates", json={"status": "on_track", "body": "Kicked off"})
    assert r.status_code == 201
    update_id = r.json()["id"]

    r = client.get(f"/api/projects/{pid}/updates")
    assert r.status_code == 200
    assert len(r.json()) == 1

    r = client.delete(f"/api/projects/updates/{update_id}")
    assert r.status_code == 204

    r = client.delete(f"/api/projects/sections/{sid}")
    assert r.status_code == 204

    r = client.get(f"/api/projects/{pid}/full")
    task_a_data = next(t for t in r.json()["tasks"] if t["id"] == task_a)
    assert task_a_data["section_id"] is None

    r = client.delete(f"/api/projects/{pid}")
    assert r.status_code == 204


class MockChatLLM:
    def __init__(self, reply_json):
        self.reply_json = reply_json

    async def complete_json(self, prompt, system="", **kwargs):
        return self.reply_json


def test_chat_applies_task_update_and_answers_from_vault(client, monkeypatch):
    """
    /api/projects/chat both mutates tasks from the LLM's JSON and, per the
    system prompt, can answer vault questions using retrieved context —
    make sure both paths still work and don't require a live Ollama.
    """
    import api.projects as projects_api

    r = client.post("/api/projects/", json={"name": "Chat Test Project"})
    pid = r.json()["id"]
    r = client.post(f"/api/projects/{pid}/tasks", json={"name": "Draft outline"})
    task_id = r.json()["id"]

    mock_llm = MockChatLLM({
        "reply": "Marked it done. Also, your vault says the deadline is Friday.",
        "updates": [{"task_id": task_id, "completed": True}],
    })
    monkeypatch.setattr(projects_api, "get_llm", lambda: mock_llm)

    async def fake_retrieve_context(question, top_k=3, use_graph=True):
        return {"context": "[Wiki: Chat Test] deadline is Friday", "embedding_chunks": [], "wiki_contexts": [], "graph_contexts": []}

    import engines.rag_engine as rag_engine_module
    monkeypatch.setattr(rag_engine_module, "get_rag_engine", lambda: type(
        "R", (), {"retrieve_context": staticmethod(fake_retrieve_context)}
    )())

    r = client.post("/api/projects/chat", json={"messages": [{"role": "user", "content": "mark draft outline done, when's it due?"}]})
    assert r.status_code == 200
    assert "Friday" in r.json()["reply"]

    r = client.get(f"/api/projects/{pid}/full")
    task = next(t for t in r.json()["tasks"] if t["id"] == task_id)
    assert task["completed"] is True

    r = client.delete(f"/api/projects/{pid}")
    assert r.status_code == 204


def test_chat_creates_and_completes_quick_tasks(client, monkeypatch):
    """
    Quick tasks (the plain daily/weekly/someday buckets) are a separate model
    from Project tasks — make sure the chat endpoint can create and complete
    them too, not just Project tasks.
    """
    import api.projects as projects_api

    mock_llm = MockChatLLM({
        "reply": "Added it to your daily list.",
        "quick_tasks": [{"title": "Email advisor about extension", "bucket": "daily", "priority": "high"}],
    })
    monkeypatch.setattr(projects_api, "get_llm", lambda: mock_llm)

    r = client.post("/api/projects/chat", json={"messages": [{"role": "user", "content": "remind me to email my advisor about the extension"}]})
    assert r.status_code == 200

    r = client.get("/api/tasks/", params={"bucket": "daily"})
    task = next(t for t in r.json() if t["title"] == "Email advisor about extension")
    assert task["priority"] == "high"
    assert task["status"] != "done"

    mock_llm.reply_json = {
        "reply": "Done!",
        "quick_task_updates": [{"task_id": task["id"], "completed": True}],
    }
    r = client.post("/api/projects/chat", json={"messages": [{"role": "user", "content": "mark that done"}]})
    assert r.status_code == 200

    r = client.get(f"/api/tasks/{task['id']}")
    assert r.json()["status"] == "done"

    client.delete(f"/api/tasks/{task['id']}")


def test_home_and_my_tasks(client):
    r = client.get("/api/projects/home")
    assert r.status_code == 200
    assert isinstance(r.json(), list)

    r = client.get("/api/projects/my-tasks")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_subtasks(client):
    r = client.post("/api/projects/", json={"name": "Subtask Project"})
    pid = r.json()["id"]

    r = client.post(f"/api/projects/{pid}/tasks", json={"name": "Parent"})
    parent_id = r.json()["id"]

    r = client.post(f"/api/projects/{pid}/tasks", json={"name": "Child"})
    child_id = r.json()["id"]
    r = client.patch(f"/api/projects/tasks/{child_id}", json={"parent_id": parent_id})
    assert r.status_code == 200
    assert r.json()["parent_id"] == parent_id

    r = client.delete(f"/api/projects/tasks/{parent_id}")
    assert r.status_code == 204

    # Cascade: child deleted along with parent
    r = client.get(f"/api/projects/{pid}/full")
    ids = [t["id"] for t in r.json()["tasks"]]
    assert child_id not in ids

    r = client.delete(f"/api/projects/{pid}")
    assert r.status_code == 204
