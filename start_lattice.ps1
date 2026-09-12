# Lattice Startup Script — PowerShell version
# Usage: Right-click → Run with PowerShell, OR add to Task Scheduler

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$LatticeDir = Join-Path $ScriptDir "lattice"
$FrontendDist = Join-Path $ScriptDir "frontend\dist"

Write-Host ""
Write-Host "  Lattice v2.0.0" -ForegroundColor Cyan
Write-Host "  Local AI Knowledge OS — Your Second Brain" -ForegroundColor Cyan
Write-Host "  ─────────────────────────────────────────" -ForegroundColor DarkCyan
Write-Host ""

# Resolve Python — prefer venv if present
$VenvPython = Join-Path $ScriptDir "venv\Scripts\python.exe"
$VenvPython2 = Join-Path $ScriptDir ".venv\Scripts\python.exe"
if (Test-Path $VenvPython) {
    $PythonExe = $VenvPython
    Write-Host "  [OK] Using venv: $VenvPython" -ForegroundColor Green
} elseif (Test-Path $VenvPython2) {
    $PythonExe = $VenvPython2
    Write-Host "  [OK] Using venv: $VenvPython2" -ForegroundColor Green
} else {
    try {
        $pyVersion = & python --version 2>&1
        $PythonExe = "python"
        Write-Host "  [OK] $pyVersion (global)" -ForegroundColor Green
    } catch {
        Write-Host "  [ERROR] Python not found. Install Python 3.11+ or create a venv." -ForegroundColor Red
        pause
        exit 1
    }
}

# Check Ollama
try {
    $ollamaCheck = Invoke-RestMethod -Uri "http://localhost:11434/api/version" -TimeoutSec 15
    Write-Host "  [OK] Ollama running: $($ollamaCheck.version)" -ForegroundColor Green
} catch {
    Write-Host "  [WARN] Ollama not running — LLM features unavailable" -ForegroundColor Yellow
    Write-Host "         Start with: ollama serve" -ForegroundColor DarkYellow
}

# Check frontend build
if (-not (Test-Path $FrontendDist)) {
    Write-Host ""
    Write-Host "  [WARN] Frontend not built — running build now..." -ForegroundColor Yellow
    $FrontendDir = Join-Path $ScriptDir "frontend"
    try {
        Push-Location $FrontendDir
        & npm run build
        Pop-Location
        Write-Host "  [OK] Frontend built" -ForegroundColor Green
    } catch {
        Pop-Location
        Write-Host "  [ERROR] Frontend build failed. Run manually: cd frontend && npm run build" -ForegroundColor Red
        pause
        exit 1
    }
} else {
    Write-Host "  [OK] Frontend dist found" -ForegroundColor Green
}

Write-Host ""
Write-Host "  Starting Lattice on http://localhost:8080" -ForegroundColor Cyan
try {
    $localIP = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -notlike '*Loopback*' } | Select-Object -First 1).IPAddress
    Write-Host "  LAN access: http://${localIP}:8080" -ForegroundColor DarkCyan
} catch {}
Write-Host ""

Set-Location $LatticeDir
& $PythonExe main.py
