"""
Lattice system tray entry point — cross-platform (Windows, macOS, Linux).
Starts FastAPI server in background thread, shows tray icon.
Double-click / "Open Lattice" → opens browser.

Auto-start:
  Windows  → HKCU registry Run key
  macOS    → ~/Library/LaunchAgents/com.lattice.app.plist
  Linux    → ~/.config/autostart/lattice.desktop
"""
import os
import sys
import platform
import subprocess
import threading
import webbrowser
from pathlib import Path
from datetime import datetime

# ── Path setup (works both dev and frozen PyInstaller) ────────────────────────
if getattr(sys, 'frozen', False):
    _ROOT = Path(sys.executable).parent
    _MEIPASS = Path(getattr(sys, '_MEIPASS', str(_ROOT)))
    _LATTICE_DIR = str(_MEIPASS / "lattice")
else:
    _ROOT = Path(__file__).parent
    _LATTICE_DIR = str(_ROOT / "lattice")

if _LATTICE_DIR not in sys.path:
    sys.path.insert(0, _LATTICE_DIR)

_OS = platform.system()           # 'Windows', 'Darwin', 'Linux'
_APP_NAME = "Lattice"
_APP_ID = "com.lattice.app"
_VERSION = "2.0.0"
# Set to your "owner/repo" to enable auto-update checks from GitHub Releases.
# Leave empty to disable.
_GITHUB_REPO = ""   # e.g. "chaitanyashriram/lattice"


# ── App data dir (platform-aware) ─────────────────────────────────────────────
def _app_data() -> Path:
    if _OS == "Windows":
        d = Path.home() / "AppData" / "Roaming" / "Lattice"
    elif _OS == "Darwin":
        d = Path.home() / "Library" / "Application Support" / "Lattice"
    else:
        xdg = os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))
        d = Path(xdg) / "lattice"
    d.mkdir(parents=True, exist_ok=True)
    return d


# ── Crash / startup logging ───────────────────────────────────────────────────
def _log(msg: str):
    try:
        with open(_app_data() / "startup.log", "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().isoformat()}] {msg}\n")
    except Exception:
        pass


# ── Tray icon (generated, no external .ico/.icns needed) ─────────────────────
def _make_icon():
    from PIL import Image, ImageDraw
    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, size, size], fill=(15, 17, 23, 255))
    margin, grid, radius = 9, 4, 4
    step = (size - 2 * margin) // (grid - 1)
    bright = (92, 124, 250, 255)
    dim = (92, 124, 250, 120)
    for i in range(grid):
        for j in range(grid):
            x = margin + i * step
            y = margin + j * step
            color = bright if (i + j) % 2 == 0 else dim
            draw.ellipse([x - radius, y - radius, x + radius, y + radius], fill=color)
    return img


# ── Auto-start helpers ────────────────────────────────────────────────────────
def _exe_path() -> str:
    if getattr(sys, 'frozen', False):
        return f'"{sys.executable}"'
    return f'"{sys.executable}" "{Path(__file__).resolve()}"'


def is_autostart() -> bool:
    if _OS == "Windows":
        import winreg
        try:
            k = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run"
            )
            winreg.QueryValueEx(k, _APP_NAME)
            winreg.CloseKey(k)
            return True
        except (FileNotFoundError, OSError):
            return False
    elif _OS == "Darwin":
        return _macos_plist_path().exists()
    else:
        return _linux_desktop_path().exists()


def set_autostart(enable: bool):
    if _OS == "Windows":
        _win_autostart(enable)
    elif _OS == "Darwin":
        _macos_autostart(enable)
    else:
        _linux_autostart(enable)


def _win_autostart(enable: bool):
    import winreg
    try:
        k = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_SET_VALUE,
        )
        if enable:
            winreg.SetValueEx(k, _APP_NAME, 0, winreg.REG_SZ,
                              f"{_exe_path()} --minimized")
        else:
            try:
                winreg.DeleteValue(k, _APP_NAME)
            except FileNotFoundError:
                pass
        winreg.CloseKey(k)
    except OSError as e:
        _log(f"Windows autostart error: {e}")


def _macos_plist_path() -> Path:
    return Path.home() / "Library" / "LaunchAgents" / f"{_APP_ID}.plist"


def _macos_autostart(enable: bool):
    plist = _macos_plist_path()
    if enable:
        plist.parent.mkdir(parents=True, exist_ok=True)
        plist.write_text(f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>{_APP_ID}</string>
  <key>ProgramArguments</key>
  <array>
    <string>{sys.executable}</string>
    <string>--minimized</string>
  </array>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><false/>
</dict>
</plist>
""")
    else:
        plist.unlink(missing_ok=True)


def _linux_desktop_path() -> Path:
    xdg = os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))
    return Path(xdg) / "autostart" / "lattice.desktop"


def _linux_autostart(enable: bool):
    desktop = _linux_desktop_path()
    if enable:
        desktop.parent.mkdir(parents=True, exist_ok=True)
        desktop.write_text(
            f"[Desktop Entry]\n"
            f"Type=Application\n"
            f"Name={_APP_NAME}\n"
            f"Exec={_exe_path()} --minimized\n"
            f"Hidden=false\n"
            f"NoDisplay=false\n"
            f"X-GNOME-Autostart-enabled=true\n"
        )
    else:
        desktop.unlink(missing_ok=True)


# ── Local IP helper ──────────────────────────────────────────────────────────
def _local_ip() -> str:
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        try:
            s.close()
        except Exception:
            pass


# ── Clipboard helper ──────────────────────────────────────────────────────────
def _copy_to_clipboard(text: str):
    try:
        if _OS == "Windows":
            subprocess.run(f"echo {text}| clip", shell=True, check=False)
        elif _OS == "Darwin":
            subprocess.run(["pbcopy"], input=text.encode(), check=False)
        else:
            for cmd in [["xclip", "-selection", "clipboard"], ["xsel", "--clipboard", "--input"]]:
                try:
                    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
                    p.communicate(text.encode())
                    return
                except FileNotFoundError:
                    continue
    except Exception as e:
        _log(f"Clipboard error: {e}")


# ── Auto-update check ─────────────────────────────────────────────────────────
_update_version: str = ""   # set to latest tag when newer version found


def _check_for_update():
    global _update_version
    if not _GITHUB_REPO:
        return
    try:
        import urllib.request
        import json
        url = f"https://api.github.com/repos/{_GITHUB_REPO}/releases/latest"
        with urllib.request.urlopen(url, timeout=10) as r:
            data = json.loads(r.read())
        latest = data.get("tag_name", "").lstrip("v")
        if latest and latest != _VERSION:
            _update_version = latest
            _log(f"Update available: v{latest}")
            try:
                from plyer import notification
                notification.notify(
                    title="Lattice update available",
                    message=f"v{latest} is out — click tray icon to download",
                    app_name="Lattice",
                    timeout=8,
                )
            except Exception:
                pass
    except Exception as e:
        _log(f"Update check failed: {e}")


# ── Server thread ─────────────────────────────────────────────────────────────
def _run_server():
    try:
        import uvicorn
        from main import app
        from config.settings import get_settings
        settings = get_settings()
        _log(f"Server starting {settings.api_host}:{settings.api_port}")
        uvicorn.run(
            app,
            host=settings.api_host,
            port=settings.api_port,
            reload=False,
            log_level="warning",
        )
    except Exception as e:
        import traceback
        _log(f"Server error: {e}\n{traceback.format_exc()}")


# ── Tray (with headless fallback for Linux servers) ───────────────────────────
def _run_tray(url: str, port: int):
    try:
        import pystray
    except ImportError:
        _log("pystray not available — running headless (server only)")
        _log(f"Lattice running at {url}")
        _log("Ctrl+C to quit")
        threading.Event().wait()
        return

    def on_open(icon, item):
        webbrowser.open(url)

    def on_toggle_autostart(icon, item):
        set_autostart(not is_autostart())

    def on_copy_lan(icon, item):
        lan_url = f"http://{_local_ip()}:{port}"
        _copy_to_clipboard(lan_url)

    def on_update(icon, item):
        if _GITHUB_REPO:
            webbrowser.open(f"https://github.com/{_GITHUB_REPO}/releases/latest")

    def on_quit(icon, item):
        _log("User quit")
        icon.stop()
        os._exit(0)

    def _build_menu():
        # Returns a plain iterable of items, not a Menu — pystray.Menu(single_callable)
        # below calls this on every open to rebuild the list dynamically (e.g. once
        # an update becomes available). Passing a Menu here instead would make
        # Icon.__init__ try to do Menu(*_build_menu), which fails: a bare function
        # isn't iterable.
        items = [pystray.MenuItem("Open Lattice", on_open, default=True)]

        if _update_version:
            items += [
                pystray.Menu.SEPARATOR,
                pystray.MenuItem(f"⬆  Update v{_update_version} available", on_update),
            ]

        items += [
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                "Auto-start on login",
                on_toggle_autostart,
                checked=lambda _: is_autostart(),
            ),
            pystray.MenuItem("Copy LAN URL", on_copy_lan),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(f"Listening on {url}", None, enabled=False),
            pystray.MenuItem(f"v{_VERSION}", None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit", on_quit),
        ]
        return items

    try:
        icon = pystray.Icon(
            _APP_NAME, _make_icon(), "Lattice — Your Second Brain", pystray.Menu(_build_menu)
        )
        # Check for updates ~15s after startup in background
        if _GITHUB_REPO:
            t = threading.Timer(15.0, _check_for_update)
            t.daemon = True
            t.start()
        icon.run()
    except Exception as e:
        _log(f"Tray error (no display?): {e} — running headless")
        _log(f"Lattice running at {url} (no tray: {e})")
        threading.Event().wait()


def main():
    minimized = "--minimized" in sys.argv

    port = 8080
    try:
        from config.settings import get_settings
        port = get_settings().api_port
    except Exception:
        pass
    url = f"http://localhost:{port}"

    server_thread = threading.Thread(target=_run_server, daemon=True, name="lattice-server")
    server_thread.start()
    _log(f"Tray started, server thread launched (OS={_OS})")

    if not minimized:
        import time
        time.sleep(2.0)
        webbrowser.open(url)

    _run_tray(url, port)


if __name__ == "__main__":
    main()
