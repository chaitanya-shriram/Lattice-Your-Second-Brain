@echo off
title Lattice - Local AI Knowledge OS
echo.
echo  Lattice
echo  Local AI Knowledge OS v2.0.0
echo  Your Second Brain, fully offline.
echo  ─────────────────────────────────────────────────
echo.

cd /d "%~dp0lattice"

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Install Python 3.11+ from python.org
    pause
    exit /b 1
)

:: Check if dependencies installed
python -c "import fastapi" >nul 2>&1
if errorlevel 1 (
    echo [INFO] Installing dependencies...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] Failed to install dependencies
        pause
        exit /b 1
    )
)

:: Check if Ollama is running
curl -s http://localhost:11434/api/version >nul 2>&1
if errorlevel 1 (
    echo [WARN] Ollama not running. LLM features will be unavailable.
    echo        Start Ollama: ollama serve
    echo.
)

echo [INFO] Starting Lattice on http://localhost:8080
echo [INFO] LAN access: http://[your-ip]:8080
echo.
echo  Press Ctrl+C to stop
echo.

python main.py

pause
