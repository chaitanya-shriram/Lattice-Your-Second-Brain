"""
Phase 8 tests: Self-improvement engine + Journal + CRM.
"""
import asyncio
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def test_self_improve_run():
    from engines.self_improve import SelfImproveEngine
    engine = SelfImproveEngine()
    result = engine.run_full_check()
    assert "timestamp" in result
    assert "total_issues" in result
    assert "checks" in result
    checks = result["checks"]
    assert "broken_links" in checks
    assert "contradictions" in checks
    assert "orphaned_notes" in checks
    assert "gap_detection" in checks
    print(f"  Health check: {result['total_issues']} issues, checks: {list(checks.keys())}")


def test_self_improve_reports():
    from engines.self_improve import SelfImproveEngine
    engine = SelfImproveEngine()
    reports = engine.get_recent_reports(limit=5)
    assert isinstance(reports, list)
    print(f"  Reports: {len(reports)}")


def test_journal_add_entry():
    from engines.journal_engine import JournalEngine

    class MockLLM:
        async def complete(self, prompt, system="", **kwargs):
            return "What was the most challenging moment of your day?"
        async def complete_json(self, *args, **kwargs):
            return {}
        async def embed(self, text):
            return [0.1] * 768

    engine = JournalEngine()
    engine.llm = MockLLM()

    result = asyncio.run(engine.add_entry(
        "Studied information theory today. Worked through KL divergence proofs. Feeling progress.",
        prompt_reflection=True,
    ))
    assert "daily_note" in result
    assert "reflection_prompt" in result
    assert len(result["reflection_prompt"]) > 0
    print(f"  Journal entry: {result['daily_note']}")
    print(f"  Reflection: {result['reflection_prompt'][:60]}")


def test_journal_get_entries():
    from engines.journal_engine import JournalEngine
    engine = JournalEngine()
    entries = engine.get_entries(limit=5)
    assert isinstance(entries, list)
    assert len(entries) >= 1  # We just added one
    print(f"  Journal entries: {len(entries)}")


def test_daily_review_generate():
    from engines.daily_review import DailyReviewEngine

    class MockLLM:
        async def complete(self, prompt, system="", **kwargs):
            return "### Summary\n- Made progress on information theory.\n\n### Tomorrow\n- Keep going."
        async def complete_json(self, *args, **kwargs):
            return {}
        async def embed(self, text):
            return [0.1] * 768

    engine = DailyReviewEngine()
    engine.llm = MockLLM()

    result = asyncio.run(engine.generate())
    assert result["review_text"].startswith("### Summary")
    assert "tasks_completed" in result
    assert "tasks_pending" in result

    from config.settings import get_settings
    note = get_settings().vault_path / result["daily_note"]
    assert "## Daily Review" in note.read_text(encoding="utf-8")


def test_daily_review_api():
    from fastapi.testclient import TestClient
    from main import app
    client = TestClient(app)
    r = client.post("/api/daily-review/generate")
    assert r.status_code == 200
    assert "review_text" in r.json()


def test_crm_upsert_contact():
    from engines.crm_engine import CRMEngine
    engine = CRMEngine()
    result = engine.upsert_contact(
        name="Yury Polyanskiy",
        role="Professor",
        institution="MIT",
        email="yp@mit.edu",
        context="Information theory lecturer, co-author of the textbook I'm using.",
        tags=["professor", "information-theory"],
    )
    assert "id" in result
    assert result["name"] == "Yury Polyanskiy"
    print(f"  Contact created: {result}")


def test_crm_list():
    from engines.crm_engine import CRMEngine
    engine = CRMEngine()
    contacts = engine.list_contacts()
    assert isinstance(contacts, list)
    assert len(contacts) >= 1
    print(f"  Contacts: {[c['name'] for c in contacts]}")


def test_crm_search():
    from engines.crm_engine import CRMEngine
    engine = CRMEngine()
    contacts = engine.list_contacts(search="Polyanskiy")
    assert len(contacts) >= 1
    assert contacts[0]["name"] == "Yury Polyanskiy"


def test_health_check_api():
    from fastapi.testclient import TestClient
    from main import app
    client = TestClient(app)
    r = client.post("/api/vault-health/run")
    assert r.status_code == 200
    data = r.json()
    assert "total_issues" in data


def test_crm_api():
    from fastapi.testclient import TestClient
    from main import app
    client = TestClient(app)

    r = client.get("/api/crm/")
    assert r.status_code == 200
    contacts = r.json()
    assert isinstance(contacts, list)

    # Get specific contact
    if contacts:
        cid = contacts[0]["id"]
        r = client.get(f"/api/crm/{cid}")
        assert r.status_code == 200
        assert "name" in r.json()
