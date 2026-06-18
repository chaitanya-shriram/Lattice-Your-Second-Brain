"""
Phase 9 tests: Gamification engine — XP, levels, streaks, achievements, weekly report.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def test_award_xp_brain_dump():
    from engines.gamification import GamificationEngine
    engine = GamificationEngine()
    result = engine.award_xp("brain_dump", "test brain dump")
    assert "xp_earned" in result
    assert result["xp_earned"] == 10
    assert "level" in result
    print(f"  XP awarded: {result['xp_earned']}, level: {result['level']}")


def test_award_xp_task_completed():
    from engines.gamification import GamificationEngine
    engine = GamificationEngine()
    result = engine.award_xp("task_completed", "test task")
    assert result["xp_earned"] == 20
    print(f"  Task XP: {result['xp_earned']}")


def test_award_xp_unknown_skipped():
    from engines.gamification import GamificationEngine
    engine = GamificationEngine()
    result = engine.award_xp("unknown_action")
    assert result.get("skipped") is True


def test_get_stats():
    from engines.gamification import GamificationEngine
    engine = GamificationEngine()
    stats = engine.get_stats()
    assert "total_xp" in stats
    assert "level_name" in stats
    assert "capture_streak" in stats
    assert stats["total_xp"] >= 30  # At least brain_dump + task_completed from above
    print(f"  Stats: {stats['total_xp']} XP, level: {stats['level_name']}")


def test_xp_log():
    from engines.gamification import GamificationEngine
    engine = GamificationEngine()
    log = engine.get_xp_log(limit=10)
    assert isinstance(log, list)
    assert len(log) >= 2
    print(f"  XP log entries: {len(log)}")


def test_achievements_check():
    from engines.gamification import GamificationEngine
    engine = GamificationEngine()
    # Award multiple brain dumps to trigger first_dump achievement
    for i in range(3):
        engine.award_xp("brain_dump")
    achievements = engine.get_achievements()
    assert isinstance(achievements, list)
    # first_dump should be unlocked (we have > 1 brain dump)
    names = [a["name"] for a in achievements]
    assert "First Capture" in names
    print(f"  Achievements: {names}")


def test_weekly_report():
    from engines.gamification import GamificationEngine
    engine = GamificationEngine()
    report = engine.generate_weekly_report()
    assert "xp_earned" in report
    assert "total_xp" in report
    assert "level" in report
    assert "streaks" in report
    print(f"  Weekly report: {report['xp_earned']} XP this week, {report['total_xp']} total")


def test_gamification_api():
    from fastapi.testclient import TestClient
    from main import app
    client = TestClient(app)

    r = client.get("/api/xp/stats")
    assert r.status_code == 200
    data = r.json()
    assert "total_xp" in data
    assert "level_name" in data

    r = client.post("/api/xp/award", json={"action": "wiki_compiled", "context": "test"})
    assert r.status_code == 200
    data = r.json()
    assert data["xp_earned"] == 25

    r = client.get("/api/xp/achievements")
    assert r.status_code == 200
    assert isinstance(r.json(), list)

    r = client.get("/api/xp/weekly-report")
    assert r.status_code == 200
    assert "xp_earned" in r.json()
