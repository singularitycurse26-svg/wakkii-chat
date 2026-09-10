"""
Auto-Suggestion Engine — 10 suggestions every 15 minutes

Cline analyzes universal memory + journal + projects and generates 10 suggestions.
Suggestions can be: auto-applied by Cline, suggested to user, or assigned to other agents.
Cline or another AI agent can auto-pop-up and apply suggestions.
"""
import json
import os
import time
import threading
import requests
from pathlib import Path
from datetime import datetime

WAKKII_API = os.environ.get("WAKKII_API", "http://127.0.0.1:8085")
WINDSURF_API = os.environ.get("WINDSURF_API", "http://127.0.0.1:3003")
WINDSURF_KEY = os.environ.get("WINDSURF_KEY", "local-dev-key-openmausbot")
LLM_MODEL = os.environ.get("WAKKII_MODEL", "glm-5.1")

CLINE_ROOM = os.environ.get("CLINE_ROOM", "CLINE")
CLINE_SENDER = "Cline"

FABLEMYTHOS = Path.home() / ".fablemythos"
PROJECTS_ROOT = Path(os.environ.get("PROJECTS_ROOT", r"C:\Users\hawpe\CascadeProjects"))

SUGGESTION_INTERVAL = 900  # 15 minutes
MAX_SUGGESTIONS = 10

SUGGESTION_PROMPT = """You are Cline's suggestion engine. Analyze the current state and generate exactly 10 suggestions.

Read the memory, journal, and project map below. Then suggest 10 improvements.

Format each suggestion on its own line:
SUGGESTION: <type> | <description> | <action>

Types: project, memory, workflow
Actions: auto-apply, suggest-to-user, assign-to-agent

Examples:
SUGGESTION: project | Fix blank page in music-studio-web | auto-apply
SUGGESTION: memory | Update PROJECT_MAP with new radio repo | auto-apply
SUGGESTION: workflow | Add build verification step before deploy | assign-to-agent
SUGGESTION: project | Polish Wakkii Links UI animations | suggest-to-user

Generate exactly 10 suggestions. Be specific and actionable.
"""

def read_file(path):
    try:
        return Path(path).read_text(encoding="utf-8")
    except Exception:
        return ""

def llm_chat(messages, max_tokens=2000):
    try:
        resp = requests.post(
            f"{WINDSURF_API}/v1/chat/completions",
            headers={"Authorization": f"Bearer {WINDSURF_KEY}", "Content-Type": "application/json"},
            json={"model": LLM_MODEL, "messages": messages, "max_tokens": max_tokens, "temperature": 0.7},
            timeout=180,
        )
        if resp.status_code == 200:
            return resp.json()["choices"][0]["message"]["content"]
        return ""
    except Exception:
        return ""

def post_message(text):
    try:
        requests.post(f"{WAKKII_API}/wakkii/rooms/{CLINE_ROOM}/messages",
                       json={"sender": CLINE_SENDER, "text": text}, timeout=10)
    except Exception:
        pass

def parse_suggestions(response):
    suggestions = []
    for line in response.split("\n"):
        line = line.strip()
        if line.startswith("SUGGESTION:"):
            parts = line[len("SUGGESTION:"):].strip().split("|")
            if len(parts) >= 3:
                suggestions.append({
                    "type": parts[0].strip(),
                    "description": parts[1].strip(),
                    "action": parts[2].strip(),
                    "timestamp": datetime.now().isoformat(),
                })
    return suggestions[:MAX_SUGGESTIONS]

def generate_suggestions():
    memory = read_file(FABLEMYTHOS / "MEMORY.md")
    journal = read_file(FABLEMYTHOS / "JOURNAL.md")
    project_map = read_file(FABLEMYTHOS / "PROJECT_MAP.md")
    learnings = read_file(FABLEMYTHOS / "cline-learnings.md")

    context = f"""MEMORY:
{memory[:2000]}

JOURNAL (latest):
{journal[-2000:]}

PROJECTS:
{project_map[:1500]}

PAST LEARNINGS:
{learnings[:1000] if learnings else "(none)"}
"""

    messages = [
        {"role": "system", "content": SUGGESTION_PROMPT},
        {"role": "system", "content": context},
        {"role": "user", "content": "Generate 10 suggestions based on the current state."},
    ]

    response = llm_chat(messages, max_tokens=2000)
    if not response:
        return []

    return parse_suggestions(response)

def apply_suggestion(suggestion):
    desc = suggestion["description"]
    action = suggestion["action"]

    if action == "auto-apply":
        post_message(f"🔧 Auto-applying: {desc}")
        from cline_agent import handle_suggestion_task
        handle_suggestion_task(desc)
    elif action == "suggest-to-user":
        post_message(f"💡 Suggestion: {desc}")
    elif action.startswith("assign-to-agent"):
        agent = action.split(":")[-1].strip() if ":" in action else "agent-1"
        post_message(f"📋 Assigned to {agent}: {desc}")

def suggestion_loop():
    time.sleep(30)  # Wait 30s after startup before first cycle

    while True:
        try:
            post_message(f"🔄 Generating 10 suggestions...")

            suggestions = generate_suggestions()

            if not suggestions:
                post_message("No suggestions generated this cycle.")
                time.sleep(SUGGESTION_INTERVAL)
                continue

            post_message(f"📋 {len(suggestions)} suggestions:")

            for i, s in enumerate(suggestions, 1):
                post_message(f"  {i}. [{s['type']}] {s['description']} → {s['action']}")

            auto_count = sum(1 for s in suggestions if s["action"] == "auto-apply")
            if auto_count > 0:
                post_message(f"🔧 Auto-applying {auto_count} suggestions...")

            for s in suggestions:
                try:
                    apply_suggestion(s)
                except Exception as e:
                    post_message(f"⚠️ Failed to apply: {s['description']} ({e})")

            post_message(f"✅ Suggestion cycle complete. Next cycle in 15 minutes.")

        except Exception as e:
            post_message(f"⚠️ Suggestion engine error: {e}")

        time.sleep(SUGGESTION_INTERVAL)

def start():
    thread = threading.Thread(target=suggestion_loop, daemon=True)
    thread.start()
