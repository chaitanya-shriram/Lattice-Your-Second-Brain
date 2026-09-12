#!/usr/bin/env bash
# Lattice Production Build Script — Linux & macOS
# Output: dist/Lattice/Lattice (Linux) or dist/Lattice.app (macOS)
# Usage: chmod +x build.sh && ./build.sh

set -euo pipefail

OS="$(uname -s)"   # Linux | Darwin
ARCH="$(uname -m)" # x86_64 | arm64

echo "================================================"
echo " Lattice Build  |  OS: $OS  |  Arch: $ARCH"
echo "================================================"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# ── 1. Python virtual environment ─────────────────────────────────────────────
VENV=""
if   [ -d "venv" ];  then VENV="venv/bin/python"
elif [ -d ".venv" ]; then VENV=".venv/bin/python"
fi

if [ -z "$VENV" ]; then
    echo "[1/5] Creating virtual environment..."
    python3 -m venv venv
    VENV="venv/bin/python"
fi

PIP="$VENV -m pip"
echo "[1/5] Using Python: $($VENV --version)"

# ── 2. Install Python deps ────────────────────────────────────────────────────
echo "[2/5] Installing Python dependencies..."
$PIP install --upgrade pip --quiet
$PIP install -r lattice/requirements.txt --quiet

# pystray needs GTK/AppIndicator on Linux; user must install system libs
if [ "$OS" = "Linux" ]; then
    echo "  [info] Linux tray needs: libgirepository1.0-dev gir1.2-appindicator3-0.1"
    echo "         Run: sudo apt install python3-gi gir1.2-appindicator3-0.1  (Debian/Ubuntu)"
    echo "              sudo dnf install python3-gobject libappindicator-gtk3  (Fedora)"
fi

$PIP install pyinstaller --quiet

# ── 3. Build frontend ─────────────────────────────────────────────────────────
echo "[3/5] Building frontend..."
if ! command -v node &>/dev/null; then
    echo "  [ERROR] Node.js not found. Install from https://nodejs.org"
    exit 1
fi
echo "  Node: $(node --version)  |  npm: $(npm --version)"

cd frontend
npm install --silent
npm run build --silent
cd "$SCRIPT_DIR"
echo "  Frontend built → frontend/dist"

# ── 4. PyInstaller ────────────────────────────────────────────────────────────
echo "[4/5] Running PyInstaller..."
"$VENV" -m PyInstaller lattice.spec --clean --noconfirm

# ── 5. Archive ────────────────────────────────────────────────────────────────
echo "[5/5] Creating archive..."
cd dist

if [ "$OS" = "Darwin" ]; then
    # Bundle both the .app AND the raw binary folder for non-GUI installs
    ARCHIVE="Lattice-macos-${ARCH}.zip"
    zip -r "$ARCHIVE" Lattice.app Lattice/ 2>/dev/null || zip -r "$ARCHIVE" Lattice/
    echo ""
    echo "  Built: dist/$ARCHIVE"
    echo ""
    echo "  ┌── macOS install notes ────────────────────────────────────────────────"
    echo "  │  1. Move Lattice.app to /Applications"
    echo "  │  2. On first launch: right-click → Open (bypass Gatekeeper)"
    echo "  │  3. For code signing: codesign --deep -s <identity> dist/Lattice.app"
    echo "  └───────────────────────────────────────────────────────────────────────"
else
    ARCHIVE="Lattice-linux-${ARCH}.tar.gz"
    tar -czf "$ARCHIVE" Lattice/
    echo ""
    echo "  Built: dist/$ARCHIVE"
    echo ""
    echo "  ┌── Linux install notes ────────────────────────────────────────────────"
    echo "  │  1. Extract: tar xzf $ARCHIVE"
    echo "  │  2. Run: ./Lattice/Lattice"
    echo "  │  3. For system tray: ensure libappindicator3 or zenity is installed"
    echo "  │  4. For autostart without tray: add to ~/.config/systemd/user/ (see docs)"
    echo "  └───────────────────────────────────────────────────────────────────────"
fi

cd "$SCRIPT_DIR"
echo ""
echo "  Done! Check dist/ folder."
