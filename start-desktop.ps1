# Wakkii Chat Desktop — Start Script
# Detects Windows version, starts servers, launches desktop UI
# Usage: .\start-desktop.ps1

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  WAKKII CHAT DESKTOP — Windows UI" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Find Python
$py = "C:\Users\hawpe\AppData\Roaming\uv\python\cpython-3.11.15-windows-x86_64-none\python.exe"
if (-not (Test-Path $py)) {
    $py = "python"
    try { $null = & python --version 2>&1 } catch { $py = "python3" }
}

# Install dependencies
Write-Host "[1/2] Installing dependencies..." -ForegroundColor Yellow
& $py -m pip install --break-system-packages -r "$ScriptDir\requirements.txt" --quiet 2>&1 | Out-Null

# Start desktop app
Write-Host "[2/2] Starting Wakkii Chat Desktop..." -ForegroundColor Green
& $py "$ScriptDir\desktop.py"

Write-Host ""
Write-Host "Wakkii Chat Desktop closed." -ForegroundColor Gray
