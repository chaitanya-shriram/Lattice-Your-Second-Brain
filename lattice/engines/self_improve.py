"""
Self-improvement engine: analyzes vault for health issues.
- Broken links: VaultLink records with unresolved targets
- Orphaned notes: vault files with no incoming links
- Contradictions: wiki pages flagged has_contradictions=1
- Gap detection: questions without answers, ideas without tasks
"""
import uuid
import json
from pathlib import Path
from datetime import datetime

from storage.database import get_db
from storage.models import WikiPage, VaultLink, HealthReport, Task, BrainDump
from utils.logger import get_logger

log = get_logger("engines.self_improve")


class SelfImproveEngine:
    def __init__(self):
        from config.settings import get_settings
        self.settings = get_settings()

    def run_full_check(self) -> dict:
        """Run all health checks and return aggregated report."""
        log.info("Running self-improvement health check")
        now = datetime.utcnow().isoformat()
        results = {}

        results["broken_links"] = self._check_broken_links(now)
        results["contradictions"] = self._check_contradictions(now)
        results["orphaned_notes"] = self._check_orphaned_notes(now)
        results["gap_detection"] = self._check_gaps(now)

        total_issues = sum(r["count"] for r in results.values())
        log.info(f"Health check complete: {total_issues} issues found")

        return {
            "timestamp": now,
            "total_issues": total_issues,
            "checks": results,
        }

    def _check_broken_links(self, now: str) -> dict:
        """Find VaultLink records where target file doesn't exist."""
        vault = self.settings.vault_path
        broken = []

        with get_db() as db:
            links = db.query(VaultLink).all()
            for lnk in links:
                target = vault / lnk.target_path
                if not target.exists():
                    broken.append({
                        "source": lnk.source_path,
                        "target": lnk.target_path,
                    })

            report = HealthReport(
                id=str(uuid.uuid4()),
                report_type="broken_links",
                items_found=len(broken),
                report_json=json.dumps(broken[:50]),
                auto_fixed=0,
                created_at=now,
            )
            db.add(report)

        log.debug(f"Broken links: {len(broken)}")
        return {"count": len(broken), "items": broken[:10]}

    def _check_contradictions(self, now: str) -> dict:
        """Find wiki pages flagged with contradictions."""
        with get_db() as db:
            pages = (
                db.query(WikiPage)
                .filter(WikiPage.has_contradictions == 1)
                .all()
            )
            items = [{"concept": p.concept, "folder": p.folder, "version": p.version} for p in pages]

            report = HealthReport(
                id=str(uuid.uuid4()),
                report_type="contradictions",
                items_found=len(items),
                report_json=json.dumps(items),
                auto_fixed=0,
                created_at=now,
            )
            db.add(report)

        log.debug(f"Contradictions: {len(items)}")
        return {"count": len(items), "items": items}

    def _check_orphaned_notes(self, now: str) -> dict:
        """Find vault .md files with no incoming VaultLink."""
        vault = self.settings.vault_path
        if not vault.exists():
            return {"count": 0, "items": []}

        all_files = set()
        for f in vault.rglob("*.md"):
            rel = str(f.relative_to(vault))
            # Skip system folders
            if not any(rel.startswith(p) for p in ["_context", "_skills"]):
                all_files.add(rel)

        with get_db() as db:
            linked = {lnk.target_path for lnk in db.query(VaultLink).all()}
            orphans = [f for f in all_files if f not in linked and not f.startswith("01-daily")]

            report = HealthReport(
                id=str(uuid.uuid4()),
                report_type="orphaned",
                items_found=len(orphans),
                report_json=json.dumps(orphans[:50]),
                auto_fixed=0,
                created_at=now,
            )
            db.add(report)

        log.debug(f"Orphaned notes: {len(orphans)}")
        return {"count": len(orphans), "items": orphans[:10]}

    def _check_gaps(self, now: str) -> dict:
        """Detect knowledge gaps: unanswered questions, unactionable ideas."""
        gaps = []

        # Questions vault files without corresponding tasks
        questions_path = self.settings.vault_path / "03-questions"
        if questions_path.exists():
            for f in questions_path.rglob("*.md"):
                content = f.read_text(encoding="utf-8", errors="replace")
                unanswered = [
                    line.strip()[2:]
                    for line in content.splitlines()
                    if line.strip().startswith("? ")
                ]
                if unanswered:
                    gaps.append({
                        "type": "unanswered_question",
                        "file": f.name,
                        "count": len(unanswered),
                    })

        with get_db() as db:
            report = HealthReport(
                id=str(uuid.uuid4()),
                report_type="gaps",
                items_found=len(gaps),
                report_json=json.dumps(gaps),
                auto_fixed=0,
                created_at=now,
            )
            db.add(report)

        log.debug(f"Gaps: {len(gaps)}")
        return {"count": len(gaps), "items": gaps}

    def get_recent_reports(self, limit: int = 10) -> list[dict]:
        """Return recent health reports."""
        with get_db() as db:
            reports = (
                db.query(HealthReport)
                .order_by(HealthReport.created_at.desc())
                .limit(limit)
                .all()
            )
            return [
                {
                    "id": r.id,
                    "type": r.report_type,
                    "items_found": r.items_found,
                    "auto_fixed": r.auto_fixed,
                    "created_at": r.created_at,
                }
                for r in reports
            ]


_engine: SelfImproveEngine | None = None


def get_self_improve_engine() -> SelfImproveEngine:
    global _engine
    if _engine is None:
        _engine = SelfImproveEngine()
    return _engine
