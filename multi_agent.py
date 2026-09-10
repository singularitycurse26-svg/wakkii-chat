"""
Multi-Agent Launcher — starts Cline + multiple Wakkii agents

Reads config from ~/.wakkii-chat/agents.json and launches all agents.
Each agent runs in its own thread with its own room and project.
All agents share the LLM connector and MCP coordination server.
"""
import json
import os
import time
import threading
import requests
from pathlib import Path

WAKKII_API = os.environ.get("WAKKII_API", "http://127.0.0.1:8085")
MCP_API = os.environ.get("MCP_API", "http://127.0.0.1:8086")
CONFIG_DIR = Path.home() / ".wakkii-chat"
AGENTS_CONFIG = CONFIG_DIR / "agents.json"

DEFAULT_CONFIG = {
    "cline": {"enabled": True, "room": "CLINE"},
    "suggestions": {"enabled": True, "interval": 900, "max": 10},
    "agents": [
        {"id": "agent-1", "room": "AGENT-1", "project": "soulmate", "name": "Soulmate Agent"},
        {"id": "agent-2", "room": "AGENT-2", "project": "music-studio-web", "name": "Music Agent"},
    ]
}

def load_config():
    if AGENTS_CONFIG.exists():
        try:
            return json.loads(AGENTS_CONFIG.read_text(encoding="utf-8"))
        except Exception:
            pass
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    AGENTS_CONFIG.write_text(json.dumps(DEFAULT_CONFIG, indent=2), encoding="utf-8")
    return DEFAULT_CONFIG

def register_with_mcp(agent_id, project, room):
    try:
        requests.post(f"{MCP_API}/mcp/register_agent",
                       json={"agent_id": agent_id, "project": project, "room": room}, timeout=5)
    except Exception:
        pass

def main():
    config = load_config()

    print("="*60)
    print("  WAKKII CHAT — MULTI-AGENT LAUNCHER")
    print("="*60)
    print()

    # Start Cline
    if config.get("cline", {}).get("enabled", True):
        print("  Starting Cline (front desk assistant)...")
        from cline_agent import start as start_cline
        start_cline()
        register_with_mcp("cline", "all", config["cline"]["room"])
        print(f"  ✅ Cline online in room: {config['cline']['room']}")

    # Start suggestion engine
    if config.get("suggestions", {}).get("enabled", True):
        print("  Starting suggestion engine (10 per 15 min)...")
        from suggestions import start as start_suggestions
        start_suggestions()
        print("  ✅ Suggestion engine running")

    # Start Wakkii agents
    for agent_config in config.get("agents", []):
        agent_id = agent_config["id"]
        room = agent_config["room"]
        project = agent_config["project"]
        name = agent_config["name"]

        print(f"  Starting {name} (room: {room}, project: {project})...")

        os.environ["WAKKII_ROOM"] = room
        os.environ["AGENT_ID"] = agent_id

        from agent import start_agent
        t = threading.Thread(target=start_agent, args=(agent_id, room, project, name), daemon=True)
        t.start()

        register_with_mcp(agent_id, project, room)
        print(f"  ✅ {name} online in room: {room}")

    print()
    print("  All agents running!")
    print(f"  Chat UI: http://localhost:8085")
    print(f"  MCP:     http://localhost:8086/mcp/health")
    print()
    print("  Press Ctrl+C to stop.")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n  Stopping all agents...")
        print("  Goodbye!")

if __name__ == "__main__":
    main()
