"""
Git Engine: auto-commits vault changes for knowledge versioning.
Uses GitPython. Creates a git repo in vault/ if not present.
"""
import uuid
from pathlib import Path
from datetime import datetime

from config.settings import get_settings
from storage.database import get_db
from storage.models import GitCommit
from utils.logger import get_logger

log = get_logger("engines.git_engine")


class GitEngine:
    def __init__(self):
        self.settings = get_settings()
        self._repo = None

    def _get_repo(self):
        if self._repo is not None:
            return self._repo
        try:
            from git import Repo, InvalidGitRepositoryError
            vault = str(self.settings.vault_path)
            try:
                self._repo = Repo(vault)
            except InvalidGitRepositoryError:
                self._repo = Repo.init(vault)
                log.info(f"Git repo initialized in vault: {vault}")
                self._write_gitignore()
            return self._repo
        except ImportError:
            log.warning("gitpython not installed. pip install gitpython")
            return None
        except Exception as e:
            log.warning(f"Git repo unavailable: {e}")
            return None

    def _write_gitignore(self):
        gi = self.settings.vault_path / ".gitignore"
        if not gi.exists():
            gi.write_text("*.pyc\n__pycache__/\n.DS_Store\n", encoding="utf-8")

    def auto_commit(self, message: str = None) -> dict:
        """Stage all changes in vault and create a commit."""
        if not self.settings.git_versioning_enabled:
            return {"skipped": True, "reason": "git versioning disabled"}

        repo = self._get_repo()
        if not repo:
            return {"skipped": True, "reason": "git unavailable"}

        try:
            # Stage all changes
            repo.git.add(A=True)

            if not repo.is_dirty(index=True):
                return {"skipped": True, "reason": "nothing to commit"}

            now = datetime.utcnow().isoformat()
            if not message:
                changed = [item.a_path for item in repo.index.diff("HEAD")]
                message = f"auto: {len(changed)} files — {now[:16]}"

            commit = repo.index.commit(message)
            sha = commit.hexsha[:8]

            try:
                n_changed = len(repo.index.diff("HEAD~1")) if len(repo.git.log("--oneline").splitlines()) > 1 else 0
            except Exception:
                n_changed = 0

            with get_db() as db:
                gc = GitCommit(
                    id=str(uuid.uuid4()),
                    commit_hash=sha,
                    commit_message=message,
                    files_changed=n_changed,
                    trigger="auto",
                    created_at=now,
                )
                db.add(gc)

            log.info(f"Git commit: {sha} — {message}")
            return {"sha": sha, "message": message, "committed_at": now}

        except Exception as e:
            log.error(f"Git commit failed: {e}")
            return {"error": str(e)}

    def get_history(self, max_commits: int = 20) -> list[dict]:
        """Return recent commit history."""
        repo = self._get_repo()
        if not repo:
            return []
        try:
            commits = []
            for commit in repo.iter_commits(max_count=max_commits):
                commits.append({
                    "sha": commit.hexsha[:8],
                    "message": commit.message.strip()[:80],
                    "author": str(commit.author),
                    "date": datetime.fromtimestamp(commit.committed_date).isoformat(),
                    "files": len(commit.stats.files),
                })
            return commits
        except Exception as e:
            log.warning(f"Git history failed: {e}")
            return []

    def get_diff(self) -> str:
        """Return current uncommitted diff."""
        repo = self._get_repo()
        if not repo:
            return ""
        try:
            return repo.git.diff()
        except Exception:
            return ""


_engine: GitEngine | None = None


def get_git_engine() -> GitEngine:
    global _engine
    if _engine is None:
        _engine = GitEngine()
    return _engine
