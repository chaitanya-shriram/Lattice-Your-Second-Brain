# Lattice Startup Script — PowerShell version
# Usage: Right-click → Run with PowerShell, OR add to Task Scheduler

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$LatticeDir = Join-Path $ScriptDir "lattice"

Write-Host ""
Write-Host "  Lattice v2.0.0" -ForegroundColor Cyan
Write-Host "  Local AI Knowledge OS — Your Second Brain" -ForegroundColor Cyan
Write-Host "  ─────────────────────────────────────────" -ForegroundColor DarkCyan
Write-Host ""

# Check Python
try {
    $pyVersion = & python --version 2>&1
    Write-Host "  [OK] $pyVersion" -ForegroundColor Green
} catch {
    Write-Host "  [ERROR] Python not found. Install Python 3.11+" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# Check Ollama
try {
    $ollamaCheck = Invoke-RestMethod -Uri "http://localhost:11434/api/version" -TimeoutSec 2
    Write-Host "  [OK] Ollama running: $($ollamaCheck.version)" -ForegroundColor Green
} catch {
    Write-Host "  [WARN] Ollama not running — LLM features unavailable" -ForegroundColor Yellow
    Write-Host "         Start with: ollama serve" -ForegroundColor DarkYellow
}

Write-Host ""
Write-Host "  Starting Lattice on http://localhost:8080" -ForegroundColor Cyan
Write-Host "  LAN access: http://$($(Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -notlike '*Loopback*' } | Select-Object -First 1).IPAddress):8080" -ForegroundColor DarkCyan
Write-Host ""

Set-Location $LatticeDir
& python main.py
