"""
Wakkii Chat Desktop — Windows UI Software

A custom-built desktop application that:
- Detects Windows version and adapts UI accordingly
- Works on all Windows versions (7, 8, 10, 11)
- Has smart detection of Windows features (rounded corners, dark mode, etc.)
- Embeds the full chat UI with auth, wallet, radio, and multi-agent rooms
- Auto-starts the server if not running
- Connects to the chat server locally

Built with Tkinter + WebView2 (edge browser) for full HTML/JS/CSS support.
"""
import os
import sys
import json
import time
import platform
import subprocess
import threading
import requests
from pathlib import Path
from datetime import datetime

# --- Windows Version Detection ---
def detect_windows_version():
    """Detect Windows version and return detailed info."""
    info = {
        "version": platform.version(),
        "release": platform.release(),
        "edition": "Unknown",
        "build": "",
        "is_windows": sys.platform == "win32",
        "supports_dark_mode": False,
        "supports_rounded_corners": False,
        "supports_acrylic": False,
        "supports_webview2": False,
        "ui_mode": "classic",
    }

    if not info["is_windows"]:
        info["ui_mode"] = "non_windows"
        return info

    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "(Get-WmiObject Win32_OperatingSystem).Caption"],
            capture_output=True, text=True, timeout=10
        )
        info["edition"] = result.stdout.strip()
    except Exception:
        pass

    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "(Get-ItemProperty 'HKLM:\\SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion').DisplayVersion"],
            capture_output=True, text=True, timeout=10
        )
        info["build"] = result.stdout.strip()
    except Exception:
        pass

    release = info["release"]
    version_num = info["version"]

    # Windows 11 (10.0.22000+)
    if release == "10" and int(version_num.split(".")[-1]) >= 22000:
        info["ui_mode"] = "win11"
        info["supports_dark_mode"] = True
        info["supports_rounded_corners"] = True
        info["supports_acrylic"] = True
        info["supports_webview2"] = True
    # Windows 10 (10.0.10240+)
    elif release == "10":
        info["ui_mode"] = "win10"
        info["supports_dark_mode"] = True
        info["supports_rounded_corners"] = False
        info["supports_acrylic"] = True
        info["supports_webview2"] = True
    # Windows 8/8.1
    elif release in ("8", "8.1"):
        info["ui_mode"] = "win8"
        info["supports_dark_mode"] = False
        info["supports_rounded_corners"] = False
        info["supports_acrylic"] = False
        info["supports_webview2"] = True
    # Windows 7
    elif release == "7":
        info["ui_mode"] = "win7"
        info["supports_dark_mode"] = False
        info["supports_rounded_corners"] = False
        info["supports_acrylic"] = False
        info["supports_webview2"] = False
    else:
        info["ui_mode"] = "classic"

    return info

def check_webview2_available():
    """Check if WebView2 runtime is installed."""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-ItemProperty 'HKLM:\\SOFTWARE\\WOW6432Node\\Microsoft\\EdgeUpdate\\Clients\\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}' -ErrorAction SilentlyContinue"],
            capture_output=True, text=True, timeout=10
        )
        return "pv" in result.stdout.lower()
    except Exception:
        return False

# --- Server Management ---
SCRIPT_DIR = Path(__file__).parent
SERVER_PORT = 8085
MCP_PORT = 8086

def is_server_running(port=SERVER_PORT):
    try:
        resp = requests.get(f"http://127.0.0.1:{port}/health", timeout=2)
        return resp.status_code == 200
    except Exception:
        return False

def start_server():
    """Start the chat server, MCP server, and multi-agent manager."""
    py = sys.executable

    # Start MCP server
    if not is_server_running(MCP_PORT):
        subprocess.Popen(
            [py, str(SCRIPT_DIR / "mcp_server.py")],
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        time.sleep(2)

    # Start chat server
    if not is_server_running(SERVER_PORT):
        subprocess.Popen(
            [py, str(SCRIPT_DIR / "server.py")],
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        time.sleep(2)

    # Start multi-agent manager
    subprocess.Popen(
        [py, str(SCRIPT_DIR / "multi_agent.py")],
        env={**os.environ, "WAKKII_API": f"http://127.0.0.1:{SERVER_PORT}",
             "MCP_API": f"http://127.0.0.1:{MCP_PORT}"},
        creationflags=subprocess.CREATE_NO_WINDOW
    )

def wait_for_server(timeout=30):
    """Wait for server to be ready."""
    start = time.time()
    while time.time() - start < timeout:
        if is_server_running():
            return True
        time.sleep(1)
    return False

# --- Desktop UI ---
def build_desktop_app():
    """Build the desktop application using the best available method."""
    win_info = detect_windows_version()
    has_webview2 = check_webview2_available()

    print(f"Windows detected: {win_info['edition']} ({win_info['ui_mode']})")
    print(f"WebView2 available: {has_webview2}")
    print(f"Build: {win_info['build']}")

    # Try WebView2 first (best experience — full HTML/JS/CSS)
    if has_webview2 or win_info["supports_webview2"]:
        try:
            return build_webview2_app(win_info)
        except ImportError:
            pass

    # Fall back to Tkinter with embedded browser
    return build_tkinter_app(win_info)

def build_webview2_app(win_info):
    """Build desktop app using webview2 (pywebview)."""
    import webview

    # Adapt window style based on Windows version
    if win_info["supports_rounded_corners"]:
        # Windows 11 — modern style
        window_config = {
            "title": "Wakkii Chat — AI Agent Ecosystem",
            "width": 1200,
            "height": 800,
            "min_size": (800, 600),
            "frame": True,
            "easy_drag": False,
        }
    else:
        # Windows 10/8/7 — classic style
        window_config = {
            "title": "Wakkii Chat",
            "width": 1000,
            "height": 700,
            "min_size": (600, 500),
            "frame": True,
        }

    # Start server if not running
    if not is_server_running():
        print("Starting Wakkii Chat server...")
        start_server()

    if not wait_for_server():
        print("ERROR: Server failed to start")
        return

    url = f"http://127.0.0.1:{SERVER_PORT}"
    print(f"Opening Wakkii Chat at {url}")

    # Create window
    window = webview.create_window(**window_config, url=url)

    # Set window icon if available
    try:
        icon_path = SCRIPT_DIR / "ui" / "icon.ico"
        if icon_path.exists():
            pass  # webview handles icons differently per platform
    except Exception:
        pass

    webview.start(debug=False)

def build_tkinter_app(win_info):
    """Build desktop app using Tkinter with embedded browser (fallback)."""
    import tkinter as tk
    from tkinter import ttk, font as tkfont

    COLORS = {
        "bg": "#0a0a0f",
        "surface": "#1a1a2e",
        "accent": "#E91E63",
        "accent2": "#9C27B0",
        "text": "#ffffff",
        "muted": "#8888aa",
        "success": "#00e676",
        "gold": "#FFD700",
    }

    # Adapt colors based on Windows version
    if win_info["ui_mode"] == "win11":
        # Windows 11 — modern dark with acrylic-like effect
        COLORS["bg"] = "#0a0a0f"
        COLORS["surface"] = "#1a1a2e"
        window_title = "Wakkii Chat — AI Agent Ecosystem"
        window_size = "1200x800"
    elif win_info["ui_mode"] == "win10":
        # Windows 10 — dark mode
        window_title = "Wakkii Chat"
        window_size = "1000x700"
    else:
        # Windows 8/7 — classic
        COLORS["bg"] = "#1a1a2e"
        COLORS["surface"] = "#252540"
        window_title = "Wakkii Chat"
        window_size = "900x650"

    root = tk.Tk()
    root.title(window_title)
    root.geometry(window_size)
    root.configure(bg=COLORS["bg"])
    root.minsize(600, 500)

    # Header
    header = tk.Frame(root, bg=COLORS["accent"], height=50)
    header.pack(fill="x", side="top")
    header.pack_propagate(False)

    title_label = tk.Label(
        header, text="🤖 Wakkii Chat",
        bg=COLORS["accent"], fg="white",
        font=(tkfont.Font(family="Segoe UI", size=14, weight="bold"))
    )
    title_label.pack(side="left", padx=15, pady=10)

    win_label = tk.Label(
        header, text=f"{win_info['edition']} • {win_info['ui_mode'].upper()}",
        bg=COLORS["accent"], fg="white",
        font=(tkfont.Font(family="Segoe UI", size=9))
    )
    win_label.pack(side="right", padx=15, pady=10)

    # Status bar
    status_frame = tk.Frame(root, bg=COLORS["surface"], height=30)
    status_frame.pack(fill="x", side="bottom")
    status_frame.pack_propagate(False)

    status_label = tk.Label(
        status_frame, text="Starting server...",
        bg=COLORS["surface"], fg=COLORS["muted"],
        font=(tkfont.Font(family="Segoe UI", size=9)),
        anchor="w"
    )
    status_label.pack(side="left", padx=10, pady=5)

    open_browser_btn = tk.Button(
        status_frame, text="Open in Browser",
        bg=COLORS["accent"], fg="white",
        font=(tkfont.Font(family="Segoe UI", size=9)),
        relief="flat", cursor="hand2",
        command=lambda: open_browser()
    )
    open_browser_btn.pack(side="right", padx=10, pady=3)

    # Main content — info + open button
    content = tk.Frame(root, bg=COLORS["bg"])
    content.pack(fill="both", expand=True, padx=20, pady=20)

    info_text = tk.Label(
        content,
        text="Wakkii Chat Desktop\n\nAI Agent Ecosystem\nCline + Multi-Agent + MCP + Devin + Radio\n\n",
        bg=COLORS["bg"], fg=COLORS["text"],
        font=(tkfont.Font(family="Segoe UI", size=16, weight="bold")),
        justify="center"
    )
    info_text.pack(pady=20)

    win_info_text = tk.Label(
        content,
        text=f"Detected: {win_info['edition']}\nMode: {win_info['ui_mode'].upper()}\nBuild: {win_info['build']}\nWebView2: {'Yes' if win_info['supports_webview2'] else 'No'}",
        bg=COLORS["bg"], fg=COLORS["muted"],
        font=(tkfont.Font(family="Segoe UI", size=10)),
        justify="left"
    )
    win_info_text.pack(pady=10)

    open_btn = tk.Button(
        content, text="🚀 Open Wakkii Chat",
        bg=COLORS["accent"], fg="white",
        font=(tkfont.Font(family="Segoe UI", size=14, weight="bold")),
        relief="flat", cursor="hand2", padx=30, pady=12,
        command=lambda: open_browser()
    )
    open_btn.pack(pady=30)

    wallet_btn = tk.Button(
        content, text="💰 Wallet",
        bg=COLORS["surface"], fg=COLORS["gold"],
        font=(tkfont.Font(family="Segoe UI", size=11)),
        relief="flat", cursor="hand2", padx=20, pady=8,
        command=lambda: show_wallet()
    )
    wallet_btn.pack(pady=5)

    def update_status(text):
        status_label.config(text=text)

    def open_browser():
        import webbrowser
        url = f"http://127.0.0.1:{SERVER_PORT}"
        webbrowser.open(url)
        update_status(f"Opened in browser: {url}")

    def show_wallet():
        try:
            sys.path.insert(0, str(SCRIPT_DIR))
            from wallet import get_wallet_info, ensure_wallet_exists
            ensure_wallet_exists()
            info = get_wallet_info()
            if info:
                import tkinter.messagebox as mb
                mb.showinfo("Incentives Inc. Wallet",
                    f"Wallet Address: {info['address']}\n"
                    f"Network: {info['network']}\n"
                    f"Token: {info['token_name']} ({info['token_symbol']})\n"
                    f"Max Supply: {info['token_max_supply']:,}")
            else:
                update_status("No wallet found")
        except Exception as e:
            update_status(f"Wallet error: {e}")

    # Start server in background
    def server_thread():
        if not is_server_running():
            update_status("Starting server...")
            start_server()
        if wait_for_server():
            update_status(f"✅ Server running — http://127.0.0.1:{SERVER_PORT}")
            open_browser()
        else:
            update_status("❌ Server failed to start")

    threading.Thread(target=server_thread, daemon=True).start()

    root.mainloop()

def main():
    """Main entry point."""
    print("=" * 60)
    print("  WAKKII CHAT DESKTOP — Windows UI Software")
    print("=" * 60)
    print()

    win_info = detect_windows_version()
    print(f"  Windows: {win_info['edition']}")
    print(f"  Mode:    {win_info['ui_mode'].upper()}")
    print(f"  Build:   {win_info['build']}")
    print(f"  Dark:    {win_info['supports_dark_mode']}")
    print(f"  Rounded: {win_info['supports_rounded_corners']}")
    print(f"  Acrylic: {win_info['supports_acrylic']}")
    print(f"  WebView2: {win_info['supports_webview2']}")
    print()

    # Check if pywebview is available
    try:
        import webview
        print("  Using: WebView2 (modern browser embedded)")
    except ImportError:
        print("  Using: Tkinter (fallback)")
        print("  Install pywebview for better experience: pip install pywebview")
    print()

    build_desktop_app()

if __name__ == "__main__":
    main()
