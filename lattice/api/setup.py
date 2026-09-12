import asyncio
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from pydantic import BaseModel
from fastapi import APIRouter

router = APIRouter()
_OS = platform.system()


def _env_path() -> Path:
    """Centralised .env location — delegates to settings module."""
    from config.settings import get_env_file_path
    return get_env_file_path()


@router.get("/status")
async def setup_status():
    import config.settings as settings_module
    settings = settings_module.get_settings()
    missing = [
        f for f in ["vault_path", "vault_files_path", "incoming_path", "db_path", "logs_path"]
        if not getattr(settings, f)
    ]
    return {"needs_setup": bool(missing), "missing": missing}


class BrowseRequest(BaseModel):
    title: str = "Select folder"


def _pick_folder_sync(title: str) -> str:
    """Native folder picker per OS. Returns path string or empty string on cancel."""
    if _OS == "Windows":
        # Title passed as a script argument ($args[0]), never interpolated into
        # the script text, so it can't break out and run arbitrary PowerShell.
        script = (
            "Add-Type -AssemblyName System.Windows.Forms; "
            "$f = New-Object System.Windows.Forms.FolderBrowserDialog; "
            "$f.Description = $args[0]; "
            "$f.ShowNewFolderButton = $true; "
            "[void]$f.ShowDialog(); "
            "$f.SelectedPath"
        )
        r = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", script, title],
            capture_output=True, text=True, timeout=120,
        )
        return r.stdout.strip()

    elif _OS == "Darwin":
        # Same idea via AppleScript's `on run argv` — title arrives as data, not code.
        script = (
            "on run argv\n"
            "POSIX path of (choose folder with prompt (item 1 of argv))\n"
            "end run"
        )
        r = subprocess.run(
            ["osascript", "-e", script, title],
            capture_output=True, text=True, timeout=120,
        )
        if r.returncode == 0:
            return r.stdout.strip().rstrip("/")
        return ""

    else:  # Linux
        for cmd in [
            ["zenity", "--file-selection", "--directory", f"--title={title}"],
            ["kdialog", "--getexistingdirectory", str(Path.home()), "--title", title],
            ["yad", "--file", "--directory", f"--title={title}"],
        ]:
            try:
                r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
                if r.returncode == 0:
                    return r.stdout.strip()
            except FileNotFoundError:
                continue
        # tkinter fallback (always available with CPython)
        try:
            import tkinter as tk
            from tkinter import filedialog
            root = tk.Tk()
            root.withdraw()
            root.wm_attributes("-topmost", True)
            path = filedialog.askdirectory(title=title)
            root.destroy()
            return path or ""
        except Exception:
            return ""


@router.post("/browse")
async def browse_folder(req: BrowseRequest = BrowseRequest()):
    """Open native folder picker (platform-aware: PowerShell / osascript / zenity / tkinter)."""
    def _pick():
        try:
            return _pick_folder_sync(req.title)
        except Exception as e:
            return f"__error__{e}"

    path = await asyncio.to_thread(_pick)
    if isinstance(path, str) and path.startswith("__error__"):
        return {"path": "", "error": path[9:]}
    return {"path": path or ""}


class SetupPaths(BaseModel):
    root_path: str


@router.post("/save")
async def save_setup(data: SetupPaths):
    """Derive all paths from root folder, write to .env, reload settings + DB."""
    from dotenv import set_key
    from storage.database import reset_engine, init_db
    import config.settings as settings_module

    root = Path(data.root_path)
    paths = {
        "VAULT_PATH": str(root / "vault"),
        "VAULT_FILES_PATH": str(root / "vault-files"),
        "INCOMING_PATH": str(root / "incoming"),
        "DB_PATH": str(root / "data" / "lattice.db"),
        "LOGS_PATH": str(root / "logs"),
    }

    env_path = _env_path()
    if not env_path.exists():
        # Seed from .env.example if available
        example_candidates = [
            env_path.parent / ".env.example",
            Path(__file__).parent.parent / ".env.example",
        ]
        for ex in example_candidates:
            if ex.exists():
                shutil.copy(ex, env_path)
                break
        else:
            env_path.touch()

    for key, value in paths.items():
        set_key(str(env_path), key, value)

    # Reset singletons so next call picks up new settings
    settings_module._settings = None
    reset_engine()

    new_settings = settings_module.get_settings()
    new_settings.ensure_dirs()
    init_db()

    return {"ok": True, "paths": paths}


@router.post("/restart")
async def restart_server():
    """Spawn fresh process then exit current one — works on all OSes including frozen Windows exe."""
    async def _do():
        await asyncio.sleep(0.5)
        kwargs = {}
        if sys.platform == "win32":
            kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
        subprocess.Popen([sys.executable] + sys.argv, close_fds=True, **kwargs)
        os._exit(0)

    asyncio.ensure_future(_do())
    return {"ok": True}
