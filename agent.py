"""
Wakkii Agent — Smart Harness with Auto-Configuration

A 24/7 autonomous coding agent that lives in chat and works on projects.
Connects to Devin AI for reasoning. Auto-configures its workflow on the fly.

The harness tightens parameters and extends its own workflow explanation
as it works, adapting to each project's needs.

WORKFLOW PHASES:
1. INTAKE — receive task, understand what's being asked
2. PLAN — break task into concrete steps
3. EXPLORE — read files, run commands, understand current state
4. EXECUTE — make changes one at a time
5. VERIFY — check that changes work (build, test, run)
6. REPORT — update journal, report progress to chat
7. ADAPT — auto-configure harness parameters based on what worked

The ADAPT phase is what makes this a "smart" harness:
- If commands keep failing, it increases error analysis depth
- If the LLM keeps looping, it tightens the prompt constraints
- If steps are too large, it breaks them into smaller pieces
- If context is too long, it trims more aggressively
- If verification keeps passing falsely, it adds deeper checks
"""
import json
import os
import time
import subprocess
import threading
import requests
import re
from pathlib import Path
from datetime import datetime

# --- Configuration ---
WAKKII_API = os.environ.get("WAKKII_API", "http://127.0.0.1:8085")
DEVIN_API = os.environ.get("DEVIN_API", "https://api.devin.ai")
DEVIN_TOKEN = os.environ.get("DEVIN_TOKEN", "")
LLM_MODEL = os.environ.get("WAKKII_MODEL", "glm-5.1")
WINDSURF_API = os.environ.get("WINDSURF_API", "http://127.0.0.1:3003")
WINDSURF_KEY = os.environ.get("WINDSURF_KEY", "local-dev-key-openmausbot")

AGENT_NAME = "Wakkii Agent"
ROOM_ID = os.environ.get("WAKKII_ROOM", "AGENT")
POLL_INTERVAL = 3

PROJECTS_ROOT = Path(os.environ.get("PROJECTS_ROOT", r"C:\Users\hawpe\CascadeProjects"))

# --- Harness State (auto-configures on the fly) ---
harness_state = {
    "max_steps": 40,
    "max_context_msgs": 20,
    "trim_to": 12,
    "loop_threshold": 3,
    "error_analysis_depth": 1,
    "verify_depth": 1,
    "step_granularity": "medium",  # small, medium, large
    "prompt_strictness": 1,  # 1-5, higher = more forceful
    "adaptations": 0,
}

def adapt_harness(metric, value):
    """Auto-configure harness parameters based on observed behavior."""
    adapted = False

    if metric == "loop_count" and value >= 2:
        harness_state["prompt_strictness"] = min(5, harness_state["prompt_strictness"] + 1)
        harness_state["loop_threshold"] = max(2, harness_state["loop_threshold"] - 1)
        adapted = True

    if metric == "error_count" and value >= 3:
        harness_state["error_analysis_depth"] = min(3, harness_state["error_analysis_depth"] + 1)
        adapted = True

    if metric == "false_verify" and value >= 1:
        harness_state["verify_depth"] = min(3, harness_state["verify_depth"] + 1)
        adapted = True

    if metric == "step_too_large" and value >= 1:
        harness_state["step_granularity"] = "small"
        adapted = True

    if metric == "context_overflow" and value >= 1:
        harness_state["max_context_msgs"] = max(10, harness_state["max_context_msgs"] - 4)
        harness_state["trim_to"] = max(8, harness_state["trim_to"] - 2)
        adapted = True

    if adapted:
        harness_state["adaptations"] += 1
        return f"[harness adapted: {metric}={value}, strictness={harness_state['prompt_strictness']}, granularity={harness_state['step_granularity']}]"
    return None

# --- Harness Prompt (dynamically generated based on harness_state) ---
def build_harness_prompt():
    strictness = harness_state["prompt_strictness"]
    granularity = harness_state["step_granularity"]
    verify_depth = harness_state["verify_depth"]
    error_depth = harness_state["error_analysis_depth"]

    strictness_note = ""
    if strictness >= 3:
        strictness_note = """
⚠ HIGH STRICTNESS MODE: You have been repeating yourself. 
You MUST use a different command every time. 
If you say the same thing again, the system will force-skip your turn.
"""
    if strictness >= 5:
        strictness_note += """
CRITICAL: You are in maximum strictness mode. 
Output ONLY tool calls. No explanation text at all. Just tools.
"""

    granularity_note = ""
    if granularity == "small":
        granularity_note = """
STEPS MUST BE TINY: One file read per step. One command per step. 
Do not combine multiple actions. Each step does exactly ONE thing.
"""

    verify_note = ""
    if verify_depth >= 2:
        verify_note = """
DEEP VERIFICATION: After each change, run TWO verification commands:
1. Build/check command
2. Read the changed file back to confirm content is correct
"""

    error_note = ""
    if error_depth >= 2:
        error_note = """
DEEP ERROR ANALYSIS: When a command fails:
1. Read the FULL error message
2. Identify the exact line/cause
3. Read the file that caused the error
4. Fix the root cause, not the symptom
5. Re-run to confirm the fix
"""

    return f"""You are Wakkii Agent, a 24/7 autonomous coding agent with a smart harness.
You live inside the Wakkii Links chat. You work on projects autonomously until they are
fully complete, polished, and working. You connect to Devin AI for reasoning.

## WHO YOU ARE

You are the personal coding agent for the user. You have FULL access to ALL projects
at {PROJECTS_ROOT} — no restrictions. You can create files, edit files, delete files,
run commands, build projects, deploy, push to git. You never need to ask permission
for individual actions — once a task is approved, just do it.

## YOUR TOOLS

Every response MUST contain at least one tool call. Write each tool on its own line:

RUN: <powershell command>     — execute a PowerShell command
READ: <file path>              — read a file's contents
WRITE: <file path>             — create/overwrite a file (content on next lines until ENDWRITE)
SEARCH: <search pattern>       — search for text in project files
PLAN: <your plan>              — declare your step-by-step plan
PROGRESS: <what you completed>  — mark a step as done
VERIFY: <what to check>        — declare you're checking something works
DONE                          — task is complete and verified

## YOUR WORKFLOW

### STEP 1: PLAN
Before ANY work, respond with PLAN: and list every step. Break the task into small,
concrete steps. Think about what files to read, what to change, how to verify.

### STEP 2: EXPLORE
READ relevant files and RUN commands to understand the current state before changing anything.
Use full absolute paths. Examples:
READ: C:\\Users\\hawpe\\CascadeProjects\\soulmate\\frontend\\src\\components\\phone\\WakkiiLinks.tsx
RUN: Get-ChildItem C:\\Users\\hawpe\\CascadeProjects\\soulmate\\frontend\\src -Recurse -Filter "*.tsx"

### STEP 3: EXECUTE
Make changes one at a time. Use WRITE: to create/edit files, RUN: to run commands.
After each change, move to VERIFY before making the next change.

### STEP 4: VERIFY
After each change, VERIFY it works. Run the build, check for errors, read the file back.
If it fails, go back to STEP 3 and fix the root cause.
{verify_note}

### STEP 5: REPORT
After completing each step, use PROGRESS: to report what's done.

### STEP 6: DONE
Only say DONE when the task is fully complete, all changes verified, everything works.

## CRITICAL RULES

1. ALWAYS start with PLAN: — never skip planning
2. EVERY response MUST contain at least one tool call
3. Never say "let me check" — use READ: or RUN: to do it
4. If a command fails, READ the error, understand it, fix the root cause
{error_note}
5. Don't retry the same failed command — change your approach
6. Keep text between tool calls under 50 words
7. Use full absolute paths
8. Do NOT put RUN: inside code blocks — put it on its own line
9. Do NOT use Format-Table -Wrap (invalid in PowerShell)
10. Keep RUN: commands simple — one command per line
11. After significant work, update JOURNAL.md:
    RUN: Add-Content -Path C:\\Users\\hawpe\\.fablemythos\\JOURNAL.md -Value "`n- <what you did>"
12. Say DONE only when fully complete and verified
{granularity_note}
{strictness_note}

## PROJECT PATHS

Soulmate OS: C:\\Users\\hawpe\\CascadeProjects\\soulmate\\frontend\\
Wakkii Links: C:\\Users\\hawpe\\CascadeProjects\\soulmate\\frontend\\src\\components\\phone\\WakkiiLinks.tsx
Build: Set-Location C:\\Users\\hawpe\\CascadeProjects\\soulmate\\frontend; npm run build
Deploy: Set-Location C:\\Users\\hawpe\\CascadeProjects\\soulmate\\frontend; npx netlify deploy --prod --dir=dist --no-build

## UNIVERSAL MEMORY

C:\\Users\\hawpe\\.fablemythos\\ — SOUL.md, MEMORY.md, JOURNAL.md, PROJECT_MAP.md
Read JOURNAL.md at start. Update after significant work.
"""

# --- Utility Functions ---

last_msg_count = 0
work_queue = []

def load_json(path, default):
    try:
        if Path(path).exists():
            return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        pass
    return default

def save_json(path, data):
    try:
        Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass

def read_file(path):
    try:
        return Path(path).read_text(encoding="utf-8")
    except Exception:
        return ""

def llm_chat(messages, max_tokens=1500):
    """Call LLM — tries Devin first, falls back to WindsurfAPI."""
    # Try Devin API
    if DEVIN_TOKEN:
        try:
            resp = requests.post(
                f"{DEVIN_API}/v1/chat/completions",
                headers={"Authorization": f"Bearer {DEVIN_TOKEN}", "Content-Type": "application/json"},
                json={"model": LLM_MODEL, "messages": messages, "max_tokens": max_tokens, "temperature": 0.5},
                timeout=180,
            )
            if resp.status_code == 200:
                return resp.json()["choices"][0]["message"]["content"]
        except Exception:
            pass  # fall through to WindsurfAPI

    # Fall back to WindsurfAPI
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

def post_message(room_id, text):
    try:
        requests.post(f"{WAKKII_API}/wakkii/rooms/{room_id}/messages",
                       json={"sender": AGENT_NAME, "text": text}, timeout=10)
    except Exception:
        pass

def get_messages(room_id):
    try:
        resp = requests.get(f"{WAKKII_API}/wakkii/rooms/{room_id}/messages", timeout=10)
        if resp.status_code == 200:
            return resp.json().get("messages", [])
    except Exception:
        pass
    return []

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

def build_context():
    fablemythos = Path.home() / ".fablemythos"
    memory = read_file(fablemythos / "MEMORY.md")
    journal = read_file(fablemythos / "JOURNAL.md")
    project_map = read_file(fablemythos / "PROJECT_MAP.md")
    return f"""MEMORY:
{memory[:1500]}

JOURNAL (latest):
{journal[-1500:]}

PROJECTS:
{project_map[:1000]}
"""

def parse_tools(response):
    """Parse tool calls — only from clean lines, not inside code blocks."""
    tools = []
    lines = response.split("\n")
    i = 0
    in_code_block = False
    while i < len(lines):
        stripped = lines[i].strip()
        if stripped.startswith("```"):
            in_code_block = not in_code_block
            i += 1
            continue
        if in_code_block:
            i += 1
            continue
        if stripped.startswith("RUN:"):
            cmd = stripped[4:].strip()
            if cmd and not cmd.startswith("<") and len(cmd) < 500:
                tools.append(("RUN", cmd))
        elif stripped.startswith("READ:"):
            tools.append(("READ", stripped[5:].strip()))
        elif stripped.startswith("SEARCH:"):
            tools.append(("SEARCH", stripped[7:].strip()))
        elif stripped.startswith("WRITE:"):
            path = stripped[6:].strip()
            content_lines = []
            i += 1
            while i < len(lines) and lines[i].strip() != "ENDWRITE":
                content_lines.append(lines[i])
                i += 1
            tools.append(("WRITE", path, "\n".join(content_lines)))
        elif stripped.startswith("PLAN:"):
            tools.append(("PLAN", stripped[5:].strip()))
        elif stripped.startswith("PROGRESS:"):
            tools.append(("PROGRESS", stripped[9:].strip()))
        elif stripped.startswith("VERIFY:"):
            tools.append(("VERIFY", stripped[7:].strip()))
        elif stripped == "DONE":
            tools.append(("DONE",))
        i += 1
    return tools

def execute_tool(tool, project_path):
    tool_name = tool[0]
    if tool_name == "RUN":
        return execute_command(tool[1], cwd=str(project_path))
    elif tool_name == "READ":
        path = tool[1]
        if not os.path.isabs(path):
            path = os.path.join(str(project_path), path)
        content = read_file(path)
        return content[:3000] if content else f"(file not found: {path})"
    elif tool_name == "WRITE":
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
    elif tool_name == "SEARCH":
        return execute_command(
            f'Select-String -Path "*.tsx","*.ts","*.py","*.js" -Pattern "{tool[1]}" -Recurse',
            cwd=str(project_path)
        )[:3000] or "(no matches)"
    elif tool_name == "PLAN":
        return f"(plan: {tool[1]})"
    elif tool_name == "PROGRESS":
        return f"(progress: {tool[1]})"
    elif tool_name == "VERIFY":
        return f"(verify: {tool[1]})"
    elif tool_name == "DONE":
        return "DONE"
    return "(unknown tool)"

# --- Smart Harness Work Loop ---

def work_on_task(task):
    """Smart harness: plan → explore → execute → verify → report → adapt → done."""
    project = task.get("project", "soulmate")
    task_desc = task.get("task", "")
    project_path = PROJECTS_ROOT / project

    post_message(ROOM_ID, f"🔧 Starting: {task_desc}")
    post_message(ROOM_ID, f"📂 Project: {project}")

    context = build_context()
    prompt = build_harness_prompt()
    messages = [
        {"role": "system", "content": prompt},
        {"role": "system", "content": context},
        {"role": "system", "content": f"Task: {task_desc}\nProject: {project}\nPath: {project_path}\nStart with PLAN:."},
        {"role": "user", "content": f"Work on: {task_desc}"},
    ]

    completed_steps = []
    last_outputs = []
    loop_count = 0
    error_count = 0
    false_verifies = 0

    for step in range(harness_state["max_steps"]):
        response = llm_chat(messages, max_tokens=1500)

        if "[LLM error" in response or "[LLM timed" in response:
            post_message(ROOM_ID, f"⚠️ {response}")
            error_count += 1
            adapt = adapt_harness("error_count", error_count)
            if adapt:
                post_message(ROOM_ID, f"🧠 {adapt}")
                prompt = build_harness_prompt()
                messages[0] = {"role": "system", "content": prompt}
            if error_count > 5:
                break
            continue

        tools = parse_tools(response)

        if not tools:
            messages.append({"role": "assistant", "content": response})
            messages.append({"role": "user", "content": "No tools used. You MUST use RUN:/READ:/WRITE:/SEARCH:/PLAN:/DONE."})
            post_message(ROOM_ID, f"Step {step+1}: {response[:200]}")
            continue

        for tool in tools:
            tool_name = tool[0]

            if tool_name == "PLAN":
                post_message(ROOM_ID, f"📋 Plan: {tool[1][:300]}")
                messages.append({"role": "assistant", "content": response})
                messages.append({"role": "user", "content": "Plan noted. Execute step 1 using RUN: or READ:."})
                continue

            if tool_name == "PROGRESS":
                completed_steps.append(tool[1])
                post_message(ROOM_ID, f"✅ {tool[1][:200]}")
                messages.append({"role": "assistant", "content": response})
                messages.append({"role": "user", "content": "Progress noted. Continue."})
                continue

            if tool_name == "VERIFY":
                post_message(ROOM_ID, f"🔍 Verifying: {tool[1][:200]}")
                messages.append({"role": "assistant", "content": response})
                messages.append({"role": "user", "content": f"Verify: {tool[1]}. Run a command to check."})
                continue

            if tool_name == "DONE":
                post_message(ROOM_ID, f"✅ COMPLETE: {task_desc}")
                post_message(ROOM_ID, f"📊 {len(completed_steps)} steps completed. Harness adapted {harness_state['adaptations']} times.")
                if task in work_queue:
                    work_queue.remove(task)
                    save_json(WORK_QUEUE_PATH, work_queue)
                journal_entry = f"- {datetime.now().strftime('%Y-%m-%dT%H:%M')}: Wakkii Agent completed: {task_desc} ({project})"
                append_journal(journal_entry)
                return

            output = execute_tool(tool, project_path)
            last_outputs.append(output[:100])

            # Loop detection
            if len(last_outputs) >= harness_state["loop_threshold"]:
                recent = last_outputs[-harness_state["loop_threshold"]:]
                if all(r == recent[0] for r in recent):
                    loop_count += 1
                    adapt = adapt_harness("loop_count", loop_count)
                    if adapt:
                        post_message(ROOM_ID, f"🧠 {adapt}")
                        prompt = build_harness_prompt()
                        messages[0] = {"role": "system", "content": prompt}
                    messages.append({"role": "assistant", "content": response})
                    messages.append({"role": "user", "content": f"LOOP DETECTED. Same output {harness_state['loop_threshold']} times. Try a completely different approach. Last: {output[:200]}"})
                    post_message(ROOM_ID, "⚠️ Loop detected — adapting harness")
                    last_outputs = []
                    continue

            # Error detection
            if "not recognized" in output.lower() or "error" in output.lower()[:50]:
                error_count += 1
                if error_count >= 3:
                    adapt = adapt_harness("error_count", error_count)
                    if adapt:
                        post_message(ROOM_ID, f"🧠 {adapt}")
                        prompt = build_harness_prompt()
                        messages[0] = {"role": "system", "content": prompt}

            tool_display = f"{tool_name}: {tool[1][:80]}" if len(tool) > 1 else tool_name
            post_message(ROOM_ID, f"▶ {tool_display}")
            if output and output != "DONE":
                post_message(ROOM_ID, f"  → {output[:200]}")

            messages.append({"role": "assistant", "content": response})
            messages.append({"role": "user", "content": f"Output:\n{output[:2000]}\n\nContinue. Use RUN/READ/WRITE/SEARCH/PROGRESS/VERIFY/DONE."})

            # Context trimming
            if len(messages) > harness_state["max_context_msgs"]:
                system_msgs = [m for m in messages if m["role"] == "system"]
                other_msgs = [m for m in messages if m["role"] != "system"]
                messages = system_msgs + other_msgs[-harness_state["trim_to"]:]
                adapt = adapt_harness("context_overflow", 1)
                if adapt:
                    post_message(ROOM_ID, f"🧠 {adapt}")

        time.sleep(1)

    post_message(ROOM_ID, f"⏹ Stopped after {harness_state['max_steps']} steps. {len(completed_steps)} completed.")
    task["status"] = "complete"
    save_json(WORK_QUEUE_PATH, work_queue)

def append_journal(entry):
    try:
        p = Path.home() / ".fablemythos" / "JOURNAL.md"
        content = p.read_text(encoding="utf-8")
        p.write_text(content + f"\n{entry}", encoding="utf-8")
    except Exception:
        pass

def guess_project(text):
    text_lower = text.lower()
    projects = {
        "soulmate": "soulmate", "landing": "soulmateos-landing",
        "fable": "fable-mythos", "music": "music-studio-web",
        "frequency": "frequency-generator", "soulillusions": "SoulIllusions",
        "openclaw": "openclaw-code", "openmausbot": "OpenMausBot",
        "windsurf": "WindsurfAPI", "radio": "desktop-radio-player",
        "movie": "soulmate",
    }
    for key, proj in projects.items():
        if key in text_lower:
            return proj
    return "soulmate"

def process_message(msg):
    sender = msg.get("sender", "")
    text = msg.get("text", "")
    ts = msg.get("timestamp", "")
    if AGENT_NAME in sender or not text.strip():
        return

    text_lower = text.lower().strip()

    if text_lower in ("yes", "y", "approve", "go", "do it"):
        if work_queue:
            task = work_queue[0]
            post_message(ROOM_ID, f"✅ Approved. Starting: {task.get('task', '')}")
            threading.Thread(target=work_on_task, args=(task,), daemon=True).start()
        return

    if text_lower in ("no", "cancel", "stop"):
        if work_queue:
            cancelled = work_queue.pop(0)
            save_json(WORK_QUEUE_PATH, work_queue)
            post_message(ROOM_ID, f"❌ Cancelled: {cancelled.get('task', '')}")
        return

    if text_lower in ("status", "queue"):
        if not work_queue:
            post_message(ROOM_ID, "📋 Queue empty. Tell me what to work on.")
        else:
            items = "\n".join(f"{i+1}. {t['task']}" for i, t in enumerate(work_queue))
            post_message(ROOM_ID, f"📋 Queue:\n{items}")
        return

    if any(text_lower.startswith(w) for w in ("work on ", "fix ", "build ", "update ", "deploy ", "refine ", "create ")):
        task = {"project": guess_project(text), "task": text.strip(), "status": "pending", "added": ts}
        work_queue.append(task)
        save_json(WORK_QUEUE_PATH, work_queue)
        post_message(ROOM_ID, f"📝 Queued: {text.strip()}\nReply YES to start.")
        return

    # Chat mode
    context = build_context()
    messages = [
        {"role": "system", "content": build_harness_prompt()},
        {"role": "system", "content": context},
        {"role": "user", "content": f"[{sender}]: {text}"},
    ]
    response = llm_chat(messages, max_tokens=800)
    post_message(ROOM_ID, response[:500])

def poll_loop():
    global last_msg_count
    time.sleep(2)
    post_message(ROOM_ID, f"🤖 {AGENT_NAME} online (smart harness v2). I'm awaiting project ideas. Let's plan first, then scale over time. Tell me what to work on, or type 'status' to see the queue.")
    while True:
        try:
            messages = get_messages(ROOM_ID)
            if len(messages) > last_msg_count:
                new_msgs = messages[last_msg_count:]
                last_msg_count = len(messages)
                for msg in new_msgs:
                    if AGENT_NAME not in msg.get("sender", ""):
                        threading.Thread(target=process_message, args=(msg,), daemon=True).start()
            elif last_msg_count == 0 and len(messages) > 0:
                last_msg_count = len(messages)
        except Exception:
            pass
        time.sleep(POLL_INTERVAL)

def main():
    global work_queue, WORK_QUEUE_PATH
    WORK_QUEUE_PATH = Path.home() / ".fablemythos" / "work-queue.json"
    work_queue = load_json(WORK_QUEUE_PATH, [])

    # Auto-connect to Devin
    try:
        from connector import auto_connect
        result = auto_connect()
        if result.get("status") == "connected":
            post_message(ROOM_ID, f"🔗 Connected to Devin ({result.get('account_type', 'user')})")
    except Exception:
        pass

    poll_thread = threading.Thread(target=poll_loop, daemon=True)
    poll_thread.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        post_message(ROOM_ID, "🤖 Going offline.")
        save_json(WORK_QUEUE_PATH, work_queue)

if __name__ == "__main__":
    main()
