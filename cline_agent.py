"""
Cline Agent — Front Desk Assistant

A 24/7 always-on AI agent that lives in the Aceline as the front desk assistant.
No limitations. Can do anything: edit files, run commands, build, deploy.
Connected to GLM-5.1 via WindsurfAPI. Aligned with universal memory + journal.

Cline generates 10 suggestions every 15 minutes and can auto-apply them.
Gets smarter on the fly by writing learnings to cline-learnings.md.
"""
import json
import os
import time
import subprocess
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
POLL_INTERVAL = 3

FABLEMYTHOS = Path.home() / ".fablemythos"
PROJECTS_ROOT = Path(os.environ.get("PROJECTS_ROOT", r"C:\Users\hawpe\CascadeProjects"))
LEARNINGS_FILE = FABLEMYTHOS / "cline-learnings.md"

CLINE_SYSTEM_PROMPT = """You are Cline, the front desk assistant for Justin's AI ecosystem.
You are ALWAYS ON, 24/7, with NO LIMITATIONS. You can do anything.

## UNIVERSAL MEMORY (read at start of every task)
- C:\\Users\\hawpe\\.fablemythos\\SOUL.md — your identity
- C:\\Users\\hawpe\\.fablemythos\\MEMORY.md — all projects, learnings
- C:\\Users\\hawpe\\.fablemythos\\JOURNAL.md — current work state
- C:\\Users\\hawpe\\.fablemythos\\PROJECT_MAP.md — all repos, URLs, deploy info
- C:\\Users\\hawpe\\.fablemythos\\ACCESS_POLICY.md — permissions
- C:\\Users\\hawpe\\.fablemythos\\AUDIT_LOG.md — action log
- C:\\Users\\hawpe\\.fablemythos\\cline-learnings.md — your past learnings (gets smarter)

## YOUR ROLE
- Front desk assistant — first point of contact in chat
- Always available, 24/7
- Can do ANYTHING: edit files, run commands, build, deploy, no restrictions
- Help with any task or question
- When someone asks for work, either do it yourself or coordinate with other agents

## TOOLS (use in every response)
RUN: <powershell command>     — execute a PowerShell command
READ: <file path>              — read a file's contents
WRITE: <file path>             — write content to a file (next lines until ENDWRITE)
SEARCH: <pattern>              — search for text in project files
DONE                          — task is complete

## GETTING SMARTER
After each work session, write what you learned to:
C:\\Users\\hawpe\\.fablemythos\\cline-learnings.md
Read this file at the start of each session to build on past learnings.

## RULES
1. EVERY response must contain at least one tool call (RUN/READ/WRITE/SEARCH/DONE)
2. Use full absolute paths
3. Keep text minimal — focus on actions
4. After significant work, update JOURNAL.md
5. Never say "let me check" — just use READ: or RUN:
6. If a command fails, analyze the error and fix the root cause
7. Don't repeat the same command if it failed
"""

last_msg_count = 0

def read_file(path):
    try:
        return Path(path).read_text(encoding="utf-8")
    except Exception:
        return ""

def llm_chat(messages, max_tokens=1500):
    try:
        resp = requests.post(
            f"{WINDSURF_API}/v1/chat/completions",
            headers={"Authorization": f"Bearer {WINDSURF_KEY}", "Content-Type": "application/json"},
            json={"model": LLM_MODEL, "messages": messages, "max_tokens": max_tokens, "temperature": 0.5},
            timeout=180,
        )
        if resp.status_code == 200:
            return resp.json()["choices"][0]["message"]["content"]
        return f"[LLM error: HTTP {resp.status_code}]"
    except requests.exceptions.ReadTimeout:
        return "[LLM timed out — try simpler]"
    except Exception as e:
        return f"[LLM error: {e}]"

def post_message(text):
    try:
        requests.post(f"{WAKKII_API}/wakkii/rooms/{CLINE_ROOM}/messages",
                       json={"sender": CLINE_SENDER, "text": text}, timeout=10)
    except Exception:
        pass

def get_messages():
    try:
        resp = requests.get(f"{WAKKII_API}/wakkii/rooms/{CLINE_ROOM}/messages", timeout=10)
        if resp.status_code == 200:
            return resp.json().get("messages", [])
    except Exception:
        pass
    return []

def build_context():
    memory = read_file(FABLEMYTHOS / "MEMORY.md")
    journal = read_file(FABLEMYTHOS / "JOURNAL.md")
    project_map = read_file(FABLEMYTHOS / "PROJECT_MAP.md")
    learnings = read_file(LEARNINGS_FILE)
    return f"""MEMORY:
{memory[:1500]}

JOURNAL (latest):
{journal[-1500:]}

PROJECTS:
{project_map[:1000]}

PAST LEARNINGS:
{learnings[:1500] if learnings else "(none yet — this is your first session)"}
"""

def parse_tools(response):
    tools = []
    lines = response.split("\n")
    i = 0
    in_code = False
    while i < len(lines):
        stripped = lines[i].strip()
        if stripped.startswith("```"):
            in_code = not in_code
            i += 1
            continue
        if in_code:
            i += 1
            continue
        if stripped.startswith("RUN:"):
            cmd = stripped[4:].strip()
            if cmd and len(cmd) < 500:
                tools.append(("RUN", cmd))
        elif stripped.startswith("READ:"):
            tools.append(("READ", stripped[5:].strip()))
        elif stripped.startswith("WRITE:"):
            path = stripped[6:].strip()
            content_lines = []
            i += 1
            while i < len(lines) and lines[i].strip() != "ENDWRITE":
                content_lines.append(lines[i])
                i += 1
            tools.append(("WRITE", path, "\n".join(content_lines)))
        elif stripped.startswith("SEARCH:"):
            tools.append(("SEARCH", stripped[7:].strip()))
        elif stripped == "DONE":
            tools.append(("DONE",))
        i += 1
    return tools

def execute_command(cmd, cwd=None):
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", cmd],
            cwd=cwd, capture_output=True, text=True, timeout=120
        )
        output = (result.stdout or "") + (result.stderr or "")
        return output[:3000] if output else "(no output)"
    except subprocess.TimeoutExpired:
        return "(timed out after 120s)"
    except Exception as e:
        return f"(error: {e})"

def execute_tool(tool, project_path):
    name = tool[0]
    if name == "RUN":
        return execute_command(tool[1], cwd=str(project_path))
    elif name == "READ":
        path = tool[1]
        if not os.path.isabs(path):
            path = os.path.join(str(project_path), path)
        content = read_file(path)
        return content[:3000] if content else f"(file not found: {path})"
    elif name == "WRITE":
        path = tool[1]
        content = tool[2]
        if not os.path.isabs(path):
            path = os.path.join(str(project_path), path)
        try:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            Path(path).write_text(content, encoding="utf-8")
            return f"(saved {path})"
        except Exception as e:
            return f"(error writing {path}: {e})"
    elif name == "SEARCH":
        return execute_command(
            f'Select-String -Path "*.tsx","*.ts","*.py","*.js" -Pattern "{tool[1]}" -Recurse',
            cwd=str(project_path)
        )[:3000] or "(no matches)"
    elif name == "DONE":
        return "DONE"
    return "(unknown tool)"

def handle_message(msg):
    sender = msg.get("sender", "")
    text = msg.get("text", "")
    if CLINE_SENDER in sender or not text.strip():
        return

    context = build_context()
    messages = [
        {"role": "system", "content": CLINE_SYSTEM_PROMPT},
        {"role": "system", "content": context},
        {"role": "user", "content": f"[{sender}]: {text}"},
    ]

    post_message(f"🤖 On it!")

    for step in range(15):
        response = llm_chat(messages, max_tokens=1500)

        if "[LLM error" in response or "[LLM timed" in response:
            post_message(f"⚠️ {response}")
            break

        tools = parse_tools(response)

        if not tools:
            post_message(response[:500])
            break

        for tool in tools:
            name = tool[0]
            if name == "DONE":
                post_message("✅ Done!")
                update_learnings(text, response)
                return

            output = execute_tool(tool, PROJECTS_ROOT)
            display = f"{name}: {tool[1][:80]}" if len(tool) > 1 else name
            post_message(f"▶ {display}")
            if output and output != "DONE":
                post_message(f"  → {output[:200]}")

            messages.append({"role": "assistant", "content": response})
            messages.append({"role": "user", "content": f"Output:\n{output[:2000]}\n\nContinue. Use RUN/READ/WRITE/SEARCH/DONE."})

            if len(messages) > 15:
                system_msgs = [m for m in messages if m["role"] == "system"]
                other_msgs = [m for m in messages if m["role"] != "system"]
                messages = system_msgs + other_msgs[-10:]

        time.sleep(0.5)

    update_learnings(text, response)

def update_learnings(task, response):
    try:
        timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M")
        entry = f"\n## {timestamp}\nTask: {task[:100]}\nOutcome: {response[:200]}\n"
        if LEARNINGS_FILE.exists():
            content = LEARNINGS_FILE.read_text(encoding="utf-8")
            LEARNINGS_FILE.write_text(content + entry, encoding="utf-8")
        else:
            LEARNINGS_FILE.write_text(f"# Cline Learnings Log\n{entry}", encoding="utf-8")
    except Exception:
        pass

def poll_loop():
    global last_msg_count
    time.sleep(2)
    post_message(f"🤖 Cline online — your 24/7 front desk assistant. No limitations. Ask me anything or tell me to work on any project. I also generate 10 suggestions every 15 minutes.")

    while True:
        try:
            messages = get_messages()
            if len(messages) > last_msg_count:
                new_msgs = messages[last_msg_count:]
                last_msg_count = len(messages)
                for msg in new_msgs:
                    if CLINE_SENDER not in msg.get("sender", ""):
                        threading.Thread(target=handle_message, args=(msg,), daemon=True).start()
            elif last_msg_count == 0 and len(messages) > 0:
                last_msg_count = len(messages)
        except Exception:
            pass
        time.sleep(POLL_INTERVAL)

def start():
    poll_thread = threading.Thread(target=poll_loop, daemon=True)
    poll_thread.start()

def handle_suggestion_task(task_desc):
    """Handle a suggestion task — used by the suggestion engine to auto-apply."""
    context = build_context()
    messages = [
        {"role": "system", "content": CLINE_SYSTEM_PROMPT},
        {"role": "system", "content": context},
        {"role": "user", "content": f"Auto-apply this suggestion: {task_desc}"},
    ]

    for step in range(10):
        response = llm_chat(messages, max_tokens=1500)
        if "[LLM error" in response or "[LLM timed" in response:
            post_message(f"⚠️ {response}")
            return

        tools = parse_tools(response)
        if not tools:
            post_message(f"  → {response[:200]}")
            return

        for tool in tools:
            name = tool[0]
            if name == "DONE":
                post_message(f"  ✅ Applied: {task_desc[:100]}")
                update_learnings(f"Auto-applied: {task_desc}", response)
                return

            output = execute_tool(tool, PROJECTS_ROOT)
            post_message(f"  ▶ {name}: {tool[1][:80] if len(tool) > 1 else ''}")
            if output and output != "DONE":
                post_message(f"    → {output[:150]}")

            messages.append({"role": "assistant", "content": response})
            messages.append({"role": "user", "content": f"Output:\n{output[:2000]}\n\nContinue. Use RUN/READ/WRITE/SEARCH/DONE."})

        time.sleep(0.5)

    update_learnings(f"Auto-applied: {task_desc}", response)
