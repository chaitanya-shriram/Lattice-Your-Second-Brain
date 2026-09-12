# Run this once as Administrator to whitelist Lattice from Windows Defender.
# Required because PyInstaller bundles Python into an exe, which triggers heuristics.

$DistPath = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "dist\Lattice"
$ExePath  = Join-Path $DistPath "Lattice.exe"

$principal = [Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltinRole]::Administrator)) {
    Write-Host "  [ERROR] Must run as Administrator. Right-click → Run as administrator." -ForegroundColor Red
    pause
    exit 1
}

Write-Host "  Adding Windows Defender exclusions for Lattice..." -ForegroundColor Cyan

# Exclude the entire dist/Lattice folder (covers all DLLs + the exe)
Add-MpPreference -ExclusionPath $DistPath -ErrorAction SilentlyContinue
Write-Host "  [OK] Excluded folder: $DistPath" -ForegroundColor Green

# Also exclude the AppData/Roaming/Lattice folder (where .env + logs live)
$AppData = Join-Path $env:APPDATA "Lattice"
New-Item -ItemType Directory -Force $AppData | Out-Null
Add-MpPreference -ExclusionPath $AppData -ErrorAction SilentlyContinue
Write-Host "  [OK] Excluded app data: $AppData" -ForegroundColor Green

Write-Host ""
Write-Host "  Defender exclusions added. You can now run Lattice.exe without false positives." -ForegroundColor Cyan
Write-Host ""
pause
