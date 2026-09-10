"""
Aceline Setup Wizard â€” handles Windows SmartScreen and first-run setup

When users download Aceline, Windows SmartScreen blocks it as "unrecognized app."
This setup wizard:
1. Unblocks all downloaded files (removes Zone.Identifier)
2. Adds Windows Defender exclusion for Aceline
3. Creates desktop shortcut with destination link
4. Configures Cline for Aceline
5. Auto-starts the server and opens the UI

Usage: python setup.py
"""
import os
import sys
import json
import time
import subprocess
import platform
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
APP_NAME = "Aceline"
APP_URL = "http://127.0.0.1:8085"
SHORTCUT_NAME = "Aceline.lnk"

def run_powershell(cmd, timeout=30):
    """Run a PowerShell command and return output."""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", cmd],
            capture_output=True, text=True, timeout=timeout
        )
        return result.stdout.strip(), result.stderr.strip(), result.returncode
    except Exception as e:
        return "", str(e), 1

def unblock_files():
    """Remove Zone.Identifier from all downloaded files (SmartScreen workaround)."""
    print("\n[1/5] Unblocking downloaded files...")
    cmd = f"Get-ChildItem -Path '{SCRIPT_DIR}' -Recurse | Unblock-File"
    stdout, stderr, rc = run_powershell(cmd, timeout=60)
    if rc == 0:
        print(f"  âœ“ All files unblocked")
    else:
        print(f"  âš  Some files may still be blocked: {stderr}")
    return rc == 0

def add_defender_exclusion():
    """Add Aceline folder to Windows Defender exclusions."""
    print("\n[2/5] Adding Windows Defender exclusion...")
    cmd = f"Add-MpPreference -ExclusionPath '{SCRIPT_DIR}' -ErrorAction SilentlyContinue"
    stdout, stderr, rc = run_powershell(cmd, timeout=15)
    if rc == 0:
        print(f"  âœ“ Defender exclusion added for {SCRIPT_DIR}")
    else:
        print(f"  âš  Could not add Defender exclusion (may need admin rights)")
    return rc == 0

def create_desktop_shortcut():
    """Create desktop shortcut with destination link."""
    print("\n[3/5] Creating desktop shortcut...")
    desktop = Path.home() / "Desktop"
    shortcut_path = desktop / SHORTCUT_NAME

    # Create shortcut to start-desktop.ps1
    ps1_path = SCRIPT_DIR / "start-desktop.ps1"
    py_path = sys.executable

    # Use PowerShell to create shortcut
    cmd = f"""
$WshShell = New-Object -comObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("{shortcut_path}")
$Shortcut.TargetPath = "{py_path}"
$Shortcut.Arguments = '"{SCRIPT_DIR}\\desktop.py"'
$Shortcut.WorkingDirectory = "{SCRIPT_DIR}"
$Shortcut.IconLocation = "{py_path},0"
$Shortcut.Description = "Aceline â€” AI Agent Ecosystem"
$Shortcut.Save()
"""
    stdout, stderr, rc = run_powershell(cmd, timeout=15)
    if rc == 0 and shortcut_path.exists():
        print(f"  âœ“ Desktop shortcut created: {shortcut_path}")
        print(f"  âœ“ Destination: {APP_URL}")
    else:
        print(f"  âš  Could not create shortcut: {stderr}")
        # Fallback: create a URL shortcut
        url_shortcut = desktop / "Aceline.url"
        url_shortcut.write_text(
            f"[InternetShortcut]\nURL={APP_URL}\nIconIndex=0\n", encoding="utf-8"
        )
        print(f"  âœ“ URL shortcut created: {url_shortcut}")
    return True

def create_start_menu_entry():
    """Create Start Menu entry for Aceline."""
    print("\n[4/5] Creating Start Menu entry...")
    start_menu = Path.home() / "AppData" / "Roaming" / "Microsoft" / "Windows" / "Start Menu" / "Programs"
    if not start_menu.exists():
        return False

    app_folder = start_menu / "Aceline"
    app_folder.mkdir(parents=True, exist_ok=True)

    shortcut_path = app_folder / SHORTCUT_NAME
    py_path = sys.executable

    cmd = f"""
$WshShell = New-Object -comObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("{shortcut_path}")
$Shortcut.TargetPath = "{py_path}"
$Shortcut.Arguments = '"{SCRIPT_DIR}\\desktop.py"'
$Shortcut.WorkingDirectory = "{SCRIPT_DIR}"
$Shortcut.IconLocation = "{py_path},0"
$Shortcut.Description = "Aceline â€” AI Agent Ecosystem"
$Shortcut.Save()
"""
    stdout, stderr, rc = run_powershell(cmd, timeout=15)
    if rc == 0:
        print(f"  âœ“ Start Menu entry created: {shortcut_path}")
    else:
        print(f"  âš  Could not create Start Menu entry")
    return rc == 0

def configure_cline_for_aceline():
    """Configure Cline to use Aceline's local server."""
    print("\n[5/5] Configuring Cline for Aceline...")

    # Update Cline MCP settings to point to Aceline
    cline_mcp_path = Path.home() / ".cline" / "data" / "settings" / "cline_mcp_settings.json"
    if cline_mcp_path.exists():
        try:
            config = json.loads(cline_mcp_path.read_text(encoding="utf-8"))
            # Add Aceline MCP server
            if "mcpServers" not in config:
                config["mcpServers"] = {}
            config["mcpServers"]["aceline"] = {
                "command": "python",
                "args": [str(SCRIPT_DIR / "mcp_server.py")],
                "env": {
                    "MCP_PORT": "8086",
                    "ACELINE_API": "http://127.0.0.1:8085"
                },
                "disabled": False,
                "autoApprove": []
            }
            cline_mcp_path.write_text(json.dumps(config, indent=2), encoding="utf-8")
            print(f"  âœ“ Cline MCP configured for Aceline")
        except Exception as e:
            print(f"  âš  Could not configure Cline MCP: {e}")

    # Create Aceline-specific Cline rules
    cline_rules_path = Path.home() / ".clinerules"
    aceline_rules = f"""# Aceline â€” Cline Front Desk Assistant Rules

## Identity
You are Cline, the 24/7 front desk assistant for Aceline.
Aceline is a multi-agent AI ecosystem with chat rooms, wallet, radio, and project agents.

## Connection
- Aceline Server: http://127.0.0.1:8085
- MCP Coordination: http://127.0.0.1:8086
- GLM-5.1 via WindsurfAPI: http://127.0.0.1:3003/v1
- Model: glm-5.1
- API Key: local-dev-key-openmausbot

## Universal Memory
Read at session start:
- ~/.fablemythos/SOUL.md
- ~/.fablemythos/MEMORY.md
- ~/.fablemythos/JOURNAL.md
- ~/.fablemythos/PROJECT_MAP.md

## Suggestion Engine
- Generate 10 suggestions every 15 minutes
- Categories: project, memory, workflow
- Actions: auto-apply, suggest-to-user, assign-to-agent

## Access
- Full access to Aceline project: {SCRIPT_DIR}
- Can edit files, run commands, build, deploy
- No limitations â€” 24/7 always-on worker
"""
    try:
        cline_rules_path.write_text(aceline_rules, encoding="utf-8")
        print(f"  âœ“ Cline rules configured for Aceline")
    except Exception as e:
        print(f"  âš  Could not write Cline rules: {e}")

    # Create Aceline workspace for Cline
    cline_workspace = Path.home() / ".cline" / "data" / "workspaces" / "aceline"
    cline_workspace.mkdir(parents=True, exist_ok=True)
    agents_md = cline_workspace / "AGENTS.md"
    agents_md.write_text(f"""# Aceline Workspace

## Project Location
{SCRIPT_DIR}

## Server
- Chat: http://127.0.0.1:8085
- MCP: http://127.0.0.1:8086
- GLM-5.1: http://127.0.0.1:3003/v1

## Start
Run: python {SCRIPT_DIR / "desktop.py"}
""", encoding="utf-8")
    print(f"  âœ“ Cline workspace created for Aceline")

    return True

def register_with_windows():
    """Register Aceline with Windows so it's recognized (SmartScreen reputation)."""
    print("\n[Extra] Registering Aceline with Windows...")

    # Add to PATH (user level)
    cmd = f"""
$path = [Environment]::GetEnvironmentVariable("Path", "User")
if ($path -notlike "*{SCRIPT_DIR}*") {{
    [Environment]::SetEnvironmentVariable("Path", $path + ";{SCRIPT_DIR}", "User")
    Write-Output "Added to PATH"
}} else {{
    Write-Output "Already in PATH"
}}
"""
    stdout, stderr, rc = run_powershell(cmd, timeout=15)
    if "Added" in stdout:
        print(f"  âœ“ Aceline added to user PATH")
    elif "Already" in stdout:
        print(f"  âœ“ Aceline already in PATH")
    else:
        print(f"  âš  Could not add to PATH")

    # Create registry entry for app recognition
    cmd = f"""
$key = "HKCU:\\Software\\Aceline"
New-Item -Path $key -Force | Out-Null
Set-ItemProperty -Path $key -Name "InstallPath" -Value "{SCRIPT_DIR}"
Set-ItemProperty -Path $key -Name "ServerURL" -Value "{APP_URL}"
Set-ItemProperty -Path $key -Name "Version" -Value "1.0.0"
Write-Output "Registry entry created"
"""
    stdout, stderr, rc = run_powershell(cmd, timeout=15)
    if rc == 0:
        print(f"  âœ“ Registry entry created (HKCU\\Software\\Aceline)")
    else:
        print(f"  âš  Could not create registry entry")

    return True

def show_smartscreen_instructions():
    """Show instructions for users who still see SmartScreen."""
    print("\n" + "=" * 60)
    print("  SMARTSCREEN BYPASS INSTRUCTIONS")
    print("=" * 60)
    print()
    print("  If Windows SmartScreen still blocks Aceline:")
    print()
    print("  1. Click 'More info' on the SmartScreen warning")
    print("  2. Click 'Run anyway'")
    print()
    print("  OR:")
    print()
    print("  1. Right-click the downloaded file")
    print("  2. Click 'Properties'")
    print("  3. Check 'Unblock' at the bottom")
    print("  4. Click 'OK'")
    print("  5. Run the file again")
    print()
    print("  OR run this in PowerShell (as Admin):")
    print(f"    Get-ChildItem -Path '{SCRIPT_DIR}' -Recurse | Unblock-File")
    print()
    print("=" * 60)

def main():
    print("=" * 60)
    print("  ACELINE SETUP WIZARD")
    print("  AI Agent Ecosystem â€” First Run Setup")
    print("=" * 60)
    print()
    print(f"  Install location: {SCRIPT_DIR}")
    print(f"  Server URL: {APP_URL}")
    print(f"  Python: {sys.executable}")
    print(f"  Platform: {platform.platform()}")

    # Run setup steps
    unblock_files()
    add_defender_exclusion()
    create_desktop_shortcut()
    create_start_menu_entry()
    configure_cline_for_aceline()
    register_with_windows()

    print("\n" + "=" * 60)
    print("  SETUP COMPLETE!")
    print("=" * 60)
    print()
    print("  Aceline is ready to use!")
    print()
    print(f"  Desktop shortcut: {Path.home() / 'Desktop' / SHORTCUT_NAME}")
    print(f"  Start Menu: Aceline")
    print(f"  Server URL: {APP_URL}")
    print()
    print("  To start Aceline:")
    print("    1. Double-click the desktop shortcut")
    print("    2. OR run: python desktop.py")
    print("    3. OR run: .\\start-desktop.ps1")
    print()

    show_smartscreen_instructions()

    # Ask to start now
    try:
        response = input("\nStart Aceline now? (Y/n): ").strip().lower()
        if response != "n":
            print("\nStarting Aceline...")
            os.chdir(str(SCRIPT_DIR))
            subprocess.run([sys.executable, str(SCRIPT_DIR / "desktop.py")])
    except (KeyboardInterrupt, EOFError):
        print("\nSetup complete. Run 'python desktop.py' to start Aceline.")

if __name__ == "__main__":
    main()
