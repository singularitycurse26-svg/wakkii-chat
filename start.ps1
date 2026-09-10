# Aceline — Start Script
# Starts MCP server, chat server, and multi-agent manager (Cline + agents)
# Usage: .\start.ps1

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  Aceline — Multi-Agent + Cline + MCP" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Find Python
$py = "python"
try { $null = & python --version 2>&1 } catch { $py = "python3" }

# Install Python dependencies
Write-Host "[1/5] Installing Python dependencies..." -ForegroundColor Yellow
& $py -m pip install -r "$ScriptDir\requirements.txt" --quiet 2>&1 | Out-Null

# Install Cline CLI if not present
Write-Host "[2/5] Checking Cline CLI..." -ForegroundColor Yellow
$clinePath = Get-Command cline -ErrorAction SilentlyContinue
if (-not $clinePath) {
    Write-Host "  Installing Cline CLI..." -ForegroundColor Yellow
    npm install -g cline 2>&1 | Out-Null
}

# Start MCP server
Write-Host "[3/5] Starting MCP coordination server (port 8086)..." -ForegroundColor Green
$mcp = Start-Process -FilePath $py -ArgumentList "$ScriptDir\mcp_server.py" -PassThru -WindowStyle Minimized
Start-Sleep -Seconds 2

# Start chat server
Write-Host "[4/5] Starting chat server (port 8085)..." -ForegroundColor Green
$server = Start-Process -FilePath $py -ArgumentList "$ScriptDir\server.py" -PassThru -WindowStyle Minimized
Start-Sleep -Seconds 2

# Start multi-agent manager (Cline + agents + suggestions)
Write-Host "[5/5] Starting multi-agent manager (Cline + agents)..." -ForegroundColor Green
$env:WAKKII_API = "http://127.0.0.1:8085"
$env:MCP_API = "http://127.0.0.1:8086"
$agent = Start-Process -FilePath $py -ArgumentList "$ScriptDir\multi_agent.py" -PassThru -WindowStyle Minimized

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  Aceline IS RUNNING!" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Chat UI:  http://localhost:8085" -ForegroundColor White
Write-Host "  Health:   http://localhost:8085/health" -ForegroundColor White
Write-Host "  MCP:      http://localhost:8086/mcp/health" -ForegroundColor White
Write-Host "  Cline:    http://localhost:8085/cline/status" -ForegroundColor White
Write-Host ""
Write-Host "  Rooms:" -ForegroundColor Gray
Write-Host "    CLINE    — Cline front desk assistant (24/7)" -ForegroundColor Gray
Write-Host "    AGENT-1  — Soulmate Agent" -ForegroundColor Gray
Write-Host "    AGENT-2  — Music Agent" -ForegroundColor Gray
Write-Host "    AGENT-3  — Radio Agent" -ForegroundColor Gray
Write-Host ""
Write-Host "  Radio widget auto-loads at bottom-left" -ForegroundColor Gray
Write-Host "  Suggestions: 10 every 15 minutes" -ForegroundColor Gray
Write-Host ""
Write-Host "  Press Ctrl+C to stop." -ForegroundColor Gray

try {
    while ($true) { Start-Sleep -Seconds 1 }
} finally {
    Stop-Process -Id $mcp.Id -Force -ErrorAction SilentlyContinue
    Stop-Process -Id $server.Id -Force -ErrorAction SilentlyContinue
    Stop-Process -Id $agent.Id -Force -ErrorAction SilentlyContinue
}
