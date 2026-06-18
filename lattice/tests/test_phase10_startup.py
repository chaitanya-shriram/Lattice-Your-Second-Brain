"""
Phase 10 tests: Startup scripts + full integration smoke test.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from pathlib import Path


def test_startup_bat_exists():
    root = Path(__file__).resolve().parent.parent.parent
    bat = root / "start_lattice.bat"
    assert bat.exists(), "start_lattice.bat not found"
    content = bat.read_text(encoding="utf-8", errors="replace")
    assert "python main.py" in content


def test_startup_ps1_exists():
    root = Path(__file__).resolve().parent.parent.parent
    ps1 = root / "start_lattice.ps1"
    assert ps1.exists(), "start_lattice.ps1 not found"


def test_autostart_xml_exists():
    root = Path(__file__).resolve().parent.parent.parent
    xml = root / "lattice_autostart.xml"
    assert xml.exists()
    content = xml.read_text(encoding="utf-8", errors="replace")
    assert "Lattice" in content
    assert "LogonTrigger" in content


def test_frontend_dist_exists():
    root = Path(__file__).resolve().parent.parent.parent
    dist = root / "frontend" / "dist" / "index.html"
    assert dist.exists(), "Frontend not built. Run: cd frontend && npm run build"


def test_full_app_import():
    """The full app with all routers must import without errors."""
    from main import app
    assert app is not None
    routes = [r.path for r in app.routes]
    assert "/api/tasks/" in routes or any("/tasks" in r for r in routes)
    assert any("/wiki" in r for r in routes)
    assert any("/graph" in r for r in routes)
    assert any("/skills" in r for r in routes)
    assert any("/xp" in r for r in routes)
    assert any("/crm" in r for r in routes)
    assert any("/journal" in r for r in routes)
    print(f"  Total routes: {len(routes)}")


def test_all_engines_importable():
    """All Phase 1-9 engines must import cleanly."""
    from engines.brain_dump import get_brain_dump_engine
    from engines.file_ingest import get_file_ingest_engine
    from engines.wiki_compiler import get_wiki_compiler
    from engines.vault_watcher import VaultWatcher
    from engines.vault_writer import get_vault_writer
    from engines.graph_builder import get_graph_builder
    from engines.rag_engine import get_rag_engine
    from engines.skill_engine import get_skill_engine
    from engines.git_engine import get_git_engine
    from engines.scheduler import get_scheduler
    from engines.self_improve import get_self_improve_engine
    from engines.journal_engine import get_journal_engine
    from engines.crm_engine import get_crm_engine
    from engines.gamification import get_gamification_engine
    print("  All 14 engines imported OK")


def test_smoke_api():
    """Full API smoke test through TestClient."""
    from fastapi.testclient import TestClient
    from main import app
    client = TestClient(app)

    endpoints = [
        ("GET", "/api/health/"),
        ("GET", "/api/tasks/"),
        ("GET", "/api/tasks/stats/summary"),
        ("GET", "/api/dump/history"),
        ("GET", "/api/files/"),
        ("GET", "/api/wiki/"),
        ("GET", "/api/graph/"),
        ("GET", "/api/skills/"),
        ("GET", "/api/actions/"),
        ("GET", "/api/crm/"),
        ("GET", "/api/journal/entries"),
        ("GET", "/api/xp/stats"),
        ("GET", "/api/xp/achievements"),
        ("GET", "/api/vault-health/reports"),
        ("GET", "/"),
        ("GET", "/tasks"),
    ]

    failures = []
    for method, path in endpoints:
        r = client.request(method, path)
        if r.status_code >= 500:
            failures.append(f"{method} {path} -> {r.status_code}")
        else:
            print(f"  {method} {path} -> {r.status_code}")

    assert not failures, f"Failing endpoints: {failures}"
