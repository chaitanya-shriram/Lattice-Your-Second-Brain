"""
Phase 12 tests: Intent detection (brain dump) + intent planning (commitment -> Project + vault plan).
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from storage.database import get_db
from storage.models import Intent, Project


class MockBrainDumpLLM:
    async def complete_json(self, prompt, system="", **kwargs):
        return {
            "tasks": [],
            "questions": [],
            "ideas": [],
            "references": [],
            "fleeting": [],
            "intents": [
                {
                    "title": "Personal Finance Tracker",
                    "text": "I'm going to build a personal finance tracker",
                    "topic": "coding",
                }
            ],
        }


def test_brain_dump_detects_intent():
    from engines.brain_dump import BrainDumpEngine

    engine = BrainDumpEngine()
    engine.llm = MockBrainDumpLLM()

    result = asyncio.run(engine.process("I'm going to build a personal finance tracker", source="test"))
    assert len(result["intents"]) == 1
    assert result["intents"][0]["title"] == "Personal Finance Tracker"

    with get_db() as db:
        rows = db.query(Intent).filter(Intent.brain_dump_id == result["dump_id"]).all()
        assert len(rows) == 1
        assert rows[0].status == "pending"
        db.delete(rows[0])  # cleanup — don't leave a pending intent for the real scheduler to sweep


class MockPlannerLLM:
    async def complete_json(self, prompt, system="", **kwargs):
        return {
            "description": "A small tool to track personal income and expenses.",
            "sections": ["Setup", "Build"],
            "tasks": [
                {"name": "Define data model", "section": "Setup", "priority": "High", "due_date": None},
                {"name": "Build CLI entry command", "section": "Build", "priority": "Medium", "due_date": None},
            ],
            "notes": "Keep it local-first, no cloud sync needed.",
        }


def test_intent_planner_creates_project_and_note():
    from engines.intent_planner import IntentPlannerEngine

    now = "2026-07-14T00:00:00"
    with get_db() as db:
        intent = Intent(
            id="test-intent-1",
            title="Personal Finance Tracker",
            raw_text="I'm going to build a personal finance tracker",
            topic="coding",
            status="pending",
            created_at=now,
        )
        db.add(intent)

    engine = IntentPlannerEngine()
    engine.llm = MockPlannerLLM()

    result = asyncio.run(engine._plan_one({
        "id": "test-intent-1", "title": "Personal Finance Tracker",
        "text": "I'm going to build a personal finance tracker", "topic": "coding",
    }))

    assert result["project_id"] is not None
    assert result["vault_note_path"] == "08-projects/personal-finance-tracker.md"

    with get_db() as db:
        intent = db.get(Intent, "test-intent-1")
        assert intent.status == "planned"
        assert intent.project_id == result["project_id"]
        assert intent.vault_note_path

        project = db.get(Project, result["project_id"])
        assert project.name == "Personal Finance Tracker"
        assert len(project.sections) == 2
        assert len(project.tasks) == 2

        # cleanup — don't leave a fake project in the user's real Projects tab
        db.delete(intent)
        db.delete(project)

    from config.settings import get_settings
    note = get_settings().vault_path / "08-projects" / "personal-finance-tracker.md"
    if note.exists():
        note.unlink()
