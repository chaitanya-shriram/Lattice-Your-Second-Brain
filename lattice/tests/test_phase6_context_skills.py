"""
Phase 6 tests: Session Context + Skills Engine.
"""
import pytest
import asyncio
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def test_context_loader_builds():
    from llm.context_loader import ContextLoader
    loader = ContextLoader()
    ctx = loader.load()
    assert isinstance(ctx, str)
    assert len(ctx) > 0
    print(f"  Context length: {len(ctx)} chars")


def test_lattice_context_generated():
    from llm.context_loader import ContextLoader
    from config.settings import get_settings
    loader = ContextLoader()
    loader._generate_lattice_context()
    s = get_settings()
    ctx_path = s.context_path / "lattice-context.md"
    assert ctx_path.exists()
    content = ctx_path.read_text()
    assert "Lattice" in content


def test_session_context_function():
    from llm.context_loader import build_session_context
    ctx = build_session_context()
    assert isinstance(ctx, str)
    assert len(ctx) > 10


def test_skill_engine_seeds_builtins():
    from engines.skill_engine import SkillEngine
    from config.settings import get_settings
    engine = SkillEngine()
    skills = engine.load_skills()
    assert len(skills) >= 4
    names = [s["name"] for s in skills]
    assert "daily-review" in names
    assert "explain-concept" in names
    assert "question-brainstorm" in names
    assert "week-plan" in names
    print(f"  Skills loaded: {names}")


def test_skill_engine_list():
    from engines.skill_engine import SkillEngine
    engine = SkillEngine()
    skills = engine.list_skills()
    assert isinstance(skills, list)
    assert len(skills) >= 4
    for s in skills:
        assert "name" in s
        assert "trigger" in s
        assert "description" in s


def test_skill_execute_mock():
    """Execute a skill with mock LLM."""
    from engines.skill_engine import SkillEngine

    class MockLLM:
        async def complete(self, prompt, system="", schema=None, model=None):
            return "Daily review generated successfully."
        async def complete_json(self, *args, **kwargs):
            return {}
        async def embed(self, text):
            return [0.1] * 768

    engine = SkillEngine()
    engine.llm = MockLLM()
    result = asyncio.run(engine.execute("daily-review"))
    assert isinstance(result, str)
    assert len(result) > 0
    print(f"  Skill result: {result[:60]}")


def test_skills_api_list():
    from fastapi.testclient import TestClient
    from main import app
    client = TestClient(app)

    # First reload
    r = client.post("/api/skills/reload")
    assert r.status_code == 200
    data = r.json()
    assert "loaded" in data
    assert data["loaded"] >= 4

    # Then list
    r = client.get("/api/skills/")
    assert r.status_code == 200
    skills = r.json()
    assert isinstance(skills, list)
    assert len(skills) >= 4


def test_skills_api_context():
    from fastapi.testclient import TestClient
    from main import app
    client = TestClient(app)
    r = client.get("/api/skills/context")
    assert r.status_code == 200
    data = r.json()
    assert "context" in data
    assert isinstance(data["context"], str)
    print(f"  API context length: {len(data['context'])} chars")
