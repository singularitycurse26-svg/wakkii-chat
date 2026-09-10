# Aceline Installer — One-Click Setup
# This script handles Windows SmartScreen blocking and sets up Aceline
# Usage: Right-click -> Run with PowerShell
# OR: powershell -ExecutionPolicy Bypass -File install.ps1

# Self-elevate to admin for Defender exclusion
if (-NOT ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host "Requesting admin rights for Windows Defender exclusion..." -ForegroundColor Yellow
    Start-Process powershell -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`"" -Verb RunAs
    exit
}

$ErrorActionPreference = "Continue"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  ACELINE INSTALLER" -ForegroundColor Cyan
Write-Host "  AI Agent Ecosystem" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Unblock all files (SmartScreen workaround)
Write-Host "[1/6] Unblocking downloaded files..." -ForegroundColor Yellow
Get-ChildItem -Path $ScriptDir -Recurse -File | Unblock-File -ErrorAction SilentlyContinue
Write-Host "  Done." -ForegroundColor Green

# Step 2: Add Defender exclusion
Write-Host "[2/6] Adding Windows Defender exclusion..." -ForegroundColor Yellow
Add-MpPreference -ExclusionPath $ScriptDir -ErrorAction SilentlyContinue
Write-Host "  Done." -ForegroundColor Green

# Step 3: Find Python
Write-Host "[3/6] Finding Python..." -ForegroundColor Yellow
$py = "C:\Users\hawpe\AppData\Roaming\uv\python\cpython-3.11.15-windows-x86_64-none\python.exe"
if (-not (Test-Path $py)) {
    $py = (Get-Command python -ErrorAction SilentlyContinue).Source
    if (-not $py) { $py = (Get-Command python3 -ErrorAction SilentlyContinue).Source }
}
if (-not $py) {
    Write-Host "  ERROR: Python not found. Install Python 3.11+ first." -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}
Write-Host "  Found: $py" -ForegroundColor Green

# Step 4: Install dependencies
Write-Host "[4/6] Installing dependencies..." -ForegroundColor Yellow
& $py -m pip install --break-system-packages -r "$ScriptDir\requirements.txt" --quiet 2>&1 | Out-Null
Write-Host "  Done." -ForegroundColor Green

# Step 5: Run setup wizard
Write-Host "[5/6] Running setup wizard..." -ForegroundColor Yellow
& $py "$ScriptDir\setup.py"
Write-Host "  Done." -ForegroundColor Green

# Step 6: Create desktop shortcut
Write-Host "[6/6] Creating desktop shortcut..." -ForegroundColor Yellow
$desktop = [Environment]::GetFolderPath("Desktop")
$shortcutPath = Join-Path $desktop "Aceline.lnk"
$WshShell = New-Object -comObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut($shortcutPath)
$Shortcut.TargetPath = $py
$Shortcut.Arguments = "`"$ScriptDir\desktop.py`""
$Shortcut.WorkingDirectory = $ScriptDir
$Shortcut.IconLocation = "$py,0"
$Shortcut.Description = "Aceline — AI Agent Ecosystem"
$Shortcut.Save()
Write-Host "  Shortcut created: $shortcutPath" -ForegroundColor Green

# Create Start Menu entry
$startMenu = [Environment]::GetFolderPath("Programs")
$acelineFolder = Join-Path $startMenu "Aceline"
New-Item -ItemType Directory -Path $acelineFolder -Force | Out-Null
$startShortcut = Join-Path $acelineFolder "Aceline.lnk"
$Shortcut2 = $WshShell.CreateShortcut($startShortcut)
$Shortcut2.TargetPath = $py
$Shortcut2.Arguments = "`"$ScriptDir\desktop.py`""
$Shortcut2.WorkingDirectory = $ScriptDir
$Shortcut2.IconLocation = "$py,0"
$Shortcut2.Description = "Aceline — AI Agent Ecosystem"
$Shortcut2.Save()
Write-Host "  Start Menu entry created" -ForegroundColor Green

# Add to PATH
$path = [Environment]::GetEnvironmentVariable("Path", "User")
if ($path -notlike "*$ScriptDir*") {
    [Environment]::SetEnvironmentVariable("Path", $path + ";$ScriptDir", "User")
    Write-Host "  Added to PATH" -ForegroundColor Green
}

# Registry entry
New-Item -Path "HKCU:\Software\Aceline" -Force | Out-Null
Set-ItemProperty -Path "HKCU:\Software\Aceline" -Name "InstallPath" -Value $ScriptDir
Set-ItemProperty -Path "HKCU:\Software\Aceline" -Name "ServerURL" -Value "http://127.0.0.1:8085"
Set-ItemProperty -Path "HKCU:\Software\Aceline" -Name "Version" -Value "1.0.0"
Write-Host "  Registry entry created" -ForegroundColor Green

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  INSTALL COMPLETE!" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Aceline is installed!" -ForegroundColor Green
Write-Host ""
Write-Host "  To start:" -ForegroundColor White
Write-Host "    - Double-click 'Aceline' on your Desktop"
Write-Host "    - OR find 'Aceline' in Start Menu"
Write-Host "    - OR run: python desktop.py"
Write-Host ""
Write-Host "  Server URL: http://127.0.0.1:8085" -ForegroundColor White
Write-Host ""
Write-Host "  If SmartScreen blocks Aceline:" -ForegroundColor Yellow
Write-Host "    1. Click 'More info' on the warning"
Write-Host "    2. Click 'Run anyway'"
Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan

$startNow = Read-Host "Start Aceline now? (Y/n)"
if ($startNow -ne "n") {
    Write-Host "Starting Aceline..." -ForegroundColor Green
    Start-Process $py -ArgumentList "`"$ScriptDir\desktop.py`" -NoNewWindow
}
