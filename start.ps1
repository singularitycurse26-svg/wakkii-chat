# Wakkii Chat — Start Script
# Starts both the chat server and the agent
# Usage: .\start.ps1

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "Starting Wakkii Chat..." -ForegroundColor Cyan

# Find Python
$py = "python"
try { $null = & python --version 2>&1 } catch { $py = "python3" }

# Install dependencies
Write-Host "Installing dependencies..." -ForegroundColor Yellow
& $py -m pip install -r "$ScriptDir\requirements.txt" --quiet 2>&1 | Out-Null

# Start chat server
Write-Host "Starting chat server on port 8085..." -ForegroundColor Green
$server = Start-Process -FilePath $py -ArgumentList "$ScriptDir\server.py" -PassThru -WindowStyle Minimized

Start-Sleep -Seconds 2

# Start agent
Write-Host "Starting Wakkii Agent..." -ForegroundColor Green
$env:WAKKII_API = "http://127.0.0.1:8085"
$agent = Start-Process -FilePath $py -ArgumentList "$ScriptDir\agent.py" -PassThru -WindowStyle Minimized

Write-Host ""
Write-Host "Wakkii Chat is running!" -ForegroundColor Cyan
Write-Host "  Chat UI: http://localhost:8085" -ForegroundColor White
Write-Host "  Health:  http://localhost:8085/health" -ForegroundColor White
Write-Host ""
Write-Host "Press Ctrl+C to stop." -ForegroundColor Gray

try {
    while ($true) { Start-Sleep -Seconds 1 }
} finally {
    Stop-Process -Id $server.Id -Force -ErrorAction SilentlyContinue
    Stop-Process -Id $agent.Id -Force -ErrorAction SilentlyContinue
}
