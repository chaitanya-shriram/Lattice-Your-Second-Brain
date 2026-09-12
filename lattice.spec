# -*- mode: python ; coding: utf-8 -*-
"""
Lattice — cross-platform PyInstaller spec.
Run on each target OS to produce a native binary.

  Windows : dist/Lattice/Lattice.exe   (no tty popup, system tray)
  macOS   : dist/Lattice.app + dist/Lattice/Lattice
  Linux   : dist/Lattice/Lattice       (ELF, tray if desktop / headless otherwise)

Build:
  pyinstaller lattice.spec --clean --noconfirm
"""

import platform
from PyInstaller.utils.hooks import collect_all

_OS = platform.system()   # 'Windows', 'Darwin', 'Linux'

# ── Collect whole packages (data + binaries + hidden) ────────────────────────
uvicorn_datas,  uvicorn_bins,  uvicorn_hidden  = collect_all('uvicorn')
pydantic_datas, pydantic_bins, pydantic_hidden = collect_all('pydantic')
pydantic_settings_datas, _, pydantic_settings_hidden = collect_all('pydantic_settings')

block_cipher = None

# ── Platform-specific hidden imports ─────────────────────────────────────────
_watchdog_hidden = {
    "Windows": ["watchdog.observers.winapi", "watchdog.observers.read_directory_changes"],
    "Darwin":  ["watchdog.observers.fsevents", "watchdog.observers.kqueue"],
    "Linux":   ["watchdog.observers.inotify", "watchdog.observers.inotify_buffer"],
}.get(_OS, [])

_pystray_hidden = {
    "Windows": ["pystray._win32"],
    "Darwin":  ["pystray._darwin"],
    "Linux":   ["pystray._gtk", "pystray._appindicator"],
}.get(_OS, [])

_os_hidden = {
    "Windows": ["winreg"],
    "Darwin":  ["Foundation", "objc"],
    "Linux":   [],
}.get(_OS, [])

# tkinter excluded on Windows (we use PowerShell picker); kept on macOS/Linux
_excludes = [
    "pytest", "test", "tests", "unittest",
    "matplotlib", "IPython", "notebook", "jupyter",
    "sphinx", "black", "mypy", "pylint",
]
if _OS == "Windows":
    _excludes.append("tkinter")

# ── Analysis ──────────────────────────────────────────────────────────────────
a = Analysis(
    ["tray.py"],
    pathex=[".", "lattice"],
    binaries=uvicorn_bins + pydantic_bins,
    datas=[
        ("lattice",        "lattice"),
        ("frontend/dist",  "frontend/dist"),
        ("lattice/.env.example", "lattice"),
    ] + uvicorn_datas + pydantic_datas + pydantic_settings_datas,
    hiddenimports=[
        # Uvicorn internals
        "uvicorn.logging",
        "uvicorn.loops", "uvicorn.loops.auto", "uvicorn.loops.asyncio",
        "uvicorn.protocols", "uvicorn.protocols.http", "uvicorn.protocols.http.auto",
        "uvicorn.protocols.http.h11_impl",
        "uvicorn.protocols.websockets", "uvicorn.protocols.websockets.auto",
        "uvicorn.lifespan", "uvicorn.lifespan.on",
        # FastAPI / Starlette
        "fastapi", "fastapi.routing", "fastapi.middleware.cors",
        "starlette.routing", "starlette.staticfiles", "starlette.responses",
        "starlette.middleware.cors",
        # SQLAlchemy SQLite
        "sqlalchemy.dialects.sqlite",
        "sqlalchemy.dialects.sqlite.pysqlite",
        "sqlalchemy.orm",
        "sqlalchemy.ext.declarative",
        # Pydantic / Settings
        "pydantic_settings",
        "pydantic.deprecated.class_validators",
        # APScheduler
        "apscheduler.schedulers.asyncio",
        "apscheduler.triggers.cron",
        "apscheduler.triggers.interval",
        "apscheduler.executors.asyncio",
        # Watchdog
        "watchdog.observers",
        "watchdog.events",
        # pystray + PIL
        "pystray",
        "PIL", "PIL.Image", "PIL.ImageDraw",
        # Networking
        "h11", "anyio", "anyio.abc", "anyio._backends._asyncio",
        "httpcore", "httpx",
        # File handling
        "multipart", "multipart.multipart", "python_multipart",
        # Logging
        "loguru",
        # dotenv
        "dotenv", "dotenv.main",
        # Other
        "git", "gitdb",
        "apscheduler",
        "markdown_it",
    ] + uvicorn_hidden + pydantic_hidden + pydantic_settings_hidden
      + _watchdog_hidden + _pystray_hidden + _os_hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=_excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Lattice",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,            # No UPX — avoids AV false positives
    console=False,        # No terminal popup on any OS
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="Lattice",
)

# macOS .app bundle — only generated when building on macOS
if _OS == "Darwin":
    app = BUNDLE(
        coll,
        name="Lattice.app",
        icon=None,
        bundle_identifier="com.lattice.app",
        info_plist={
            "NSHighResolutionCapable": True,
            "LSBackgroundOnly": True,       # menu-bar / tray-only app
            "CFBundleShortVersionString": "2.0.0",
            "CFBundleName": "Lattice",
            "CFBundleDisplayName": "Lattice",
            "CFBundleVersion": "2.0.0",
            "NSAppleEventsUsageDescription":
                "Lattice uses Apple Events for native folder picking.",
        },
    )
