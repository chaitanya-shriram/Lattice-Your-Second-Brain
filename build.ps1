# Lattice Production Build Script — Windows
# Output: dist\Lattice\Lattice.exe  +  dist\Lattice.zip (portable archive)
# Usage: Right-click → Run with PowerShell
#
# Linux / macOS: run build.sh instead
# CI (all 3 platforms): .github/workflows/build.yml (triggered by git tags)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host ""
Write-Host "  Lattice Production Build" -ForegroundColor Cyan
Write-Host "  ════════════════════════════════════════" -ForegroundColor DarkCyan
Write-Host ""

Set-Location $ScriptDir

# ── 1. Python venv ────────────────────────────────────────────────────────────
$VenvDir    = Join-Path $ScriptDir "venv"
$VenvPython = Join-Path $VenvDir "Scripts\python.exe"
$VenvPip    = Join-Path $VenvDir "Scripts\pip.exe"
$VenvPyI    = Join-Path $VenvDir "Scripts\pyinstaller.exe"

if (-not (Test-Path $VenvPython)) {
    Write-Host "  Creating Python venv..." -ForegroundColor Yellow
    python -m venv venv
}

Write-Host "  Installing Python dependencies (this may take a while)..." -ForegroundColor Yellow
& $VenvPip install -r lattice/requirements.txt -q --disable-pip-version-check
& $VenvPip install pyinstaller -q --disable-pip-version-check
Write-Host "  [OK] Python deps ready" -ForegroundColor Green

# ── 2. Frontend build ─────────────────────────────────────────────────────────
Write-Host "  Building frontend..." -ForegroundColor Yellow
Push-Location (Join-Path $ScriptDir "frontend")
npm install --silent 2>$null
npm run build
Pop-Location
if (-not (Test-Path (Join-Path $ScriptDir "frontend\dist\index.html"))) {
    Write-Host "  [ERROR] Frontend build failed — index.html missing" -ForegroundColor Red
    exit 1
}
Write-Host "  [OK] Frontend built" -ForegroundColor Green

# ── 3. PyInstaller package ────────────────────────────────────────────────────
Write-Host "  Packaging with PyInstaller (--onedir, no UPX)..." -ForegroundColor Yellow
Write-Host "  Note: first build takes 3-5 minutes to collect all packages" -ForegroundColor DarkCyan

# Clean previous build artifacts
if (Test-Path "build\Lattice")   { Remove-Item -Recurse -Force "build\Lattice" }
if (Test-Path "dist\Lattice")    { Remove-Item -Recurse -Force "dist\Lattice" }

& $VenvPyI lattice.spec --clean --noconfirm --log-level WARN

$ExePath = Join-Path $ScriptDir "dist\Lattice\Lattice.exe"
if (-not (Test-Path $ExePath)) {
    Write-Host "  [ERROR] Build failed — Lattice.exe not found" -ForegroundColor Red
    exit 1
}
Write-Host "  [OK] Packaged: dist\Lattice\Lattice.exe" -ForegroundColor Green

# ── 4. Defender exclusion hint (cannot add programmatically without admin) ────
Write-Host ""
Write-Host "  ─── Windows Defender Note ───────────────────────────────────────" -ForegroundColor Yellow
Write-Host "  PyInstaller exes may be flagged. To whitelist (run as admin):" -ForegroundColor Yellow
Write-Host "    Add-MpPreference -ExclusionPath '$ScriptDir\dist\Lattice'" -ForegroundColor White
Write-Host "  Or submit dist\Lattice\Lattice.exe to security.microsoft.com" -ForegroundColor DarkYellow
Write-Host "  ─────────────────────────────────────────────────────────────────" -ForegroundColor Yellow
Write-Host ""

# ── 5. Create portable zip ────────────────────────────────────────────────────
Write-Host "  Creating Lattice.zip (portable archive)..." -ForegroundColor Yellow
$ZipPath = Join-Path $ScriptDir "dist\Lattice.zip"
if (Test-Path $ZipPath) { Remove-Item $ZipPath }
Compress-Archive -Path "dist\Lattice\*" -DestinationPath $ZipPath
Write-Host "  [OK] Archive: dist\Lattice.zip ($([math]::Round((Get-Item $ZipPath).Length/1MB,1)) MB)" -ForegroundColor Green

# ── 6. Summary ────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "  BUILD COMPLETE" -ForegroundColor Cyan
Write-Host "  Executable : dist\Lattice\Lattice.exe" -ForegroundColor White
Write-Host "  Portable   : dist\Lattice.zip" -ForegroundColor White
Write-Host ""
Write-Host "  To run     : double-click dist\Lattice\Lattice.exe" -ForegroundColor DarkCyan
Write-Host "  First run  : setup wizard opens in browser, tray icon appears" -ForegroundColor DarkCyan
Write-Host "  Auto-start : right-click tray icon → Auto-start on login" -ForegroundColor DarkCyan
Write-Host ""
