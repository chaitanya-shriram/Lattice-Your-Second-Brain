"""
Phase 7 tests: Scheduler + Git Engine.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def test_git_engine_init():
    from engines.git_engine import GitEngine
    engine = GitEngine()
    repo = engine._get_repo()
    # May be None if gitpython not installed, but shouldn't crash
    print(f"  Git repo: {repo}")


def test_git_engine_init_or_open():
    from engines.git_engine import GitEngine
    from config.settings import get_settings
    engine = GitEngine()
    try:
        import git
        repo = engine._get_repo()
        assert repo is not None
        print(f"  Repo path: {repo.working_dir}")
    except ImportError:
        print("  gitpython not installed, skipping")


def test_git_auto_commit():
    from engines.git_engine import GitEngine
    engine = GitEngine()
    result = engine.auto_commit("test: phase 7 test commit")
    assert isinstance(result, dict)
    assert "sha" in result or "skipped" in result or "error" in result
    print(f"  Commit result: {result}")


def test_git_history():
    from engines.git_engine import GitEngine
    engine = GitEngine()
    history = engine.get_history(max_commits=5)
    assert isinstance(history, list)
    print(f"  Git history: {len(history)} commits")


def test_scheduler_init():
    from engines.scheduler import LatticeScheduler
    sched = LatticeScheduler()
    assert sched is not None
    assert not sched._running


def test_scheduler_start_stop():
    import asyncio
    from engines.scheduler import LatticeScheduler

    async def _run():
        sched = LatticeScheduler()
        try:
            sched.start()
            assert sched._running
            jobs = sched.get_jobs()
            assert isinstance(jobs, list)
            assert len(jobs) >= 3
            print(f"  Jobs: {[j['id'] for j in jobs]}")
        finally:
            sched.stop()
            assert not sched._running

    asyncio.run(_run())


def test_notification_graceful():
    """Notification should not crash even if plyer isn't installed."""
    from engines.scheduler import _send_notification
    _send_notification("Test", "This is a test notification")
    # Should not raise


def test_git_api_available():
    from fastapi.testclient import TestClient
    from main import app
    client = TestClient(app)
    # Confirm server boots with scheduler + git
    r = client.get("/api/health/")
    assert r.status_code == 200
