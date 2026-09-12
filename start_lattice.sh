#!/usr/bin/env bash
# Lattice dev launcher — Linux & macOS
# Starts the FastAPI server directly from source (no build needed for dev).
# For production, use build.sh to produce a standalone binary.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# ── Find Python ───────────────────────────────────────────────────────────────
PYTHON=""
for candidate in "venv/bin/python" ".venv/bin/python" "python3" "python"; do
    if command -v "$candidate" &>/dev/null || [ -x "$candidate" ]; then
        PYTHON="$candidate"
        break
    fi
done

if [ -z "$PYTHON" ]; then
    echo "[ERROR] Python not found. Install Python 3.10+ first."
    exit 1
fi

echo "Using Python: $($PYTHON --version)"

# ── Build frontend if dist missing ───────────────────────────────────────────
if [ ! -f "frontend/dist/index.html" ]; then
    echo "Frontend not built — building now..."
    cd frontend
    npm install --silent
    npm run build --silent
    cd "$SCRIPT_DIR"
fi

# ── Launch ───────────────────────────────────────────────────────────────────
echo "Starting Lattice..."
echo "  Open http://localhost:8080 in your browser"
echo "  Ctrl+C to stop"
echo ""

cd lattice
exec "$PYTHON" main.py "$@"
