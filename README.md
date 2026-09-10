# Wakkii Chat

A standalone room-based chat system with a 24/7 autonomous coding agent that connects to Devin AI.

## What It Does

Wakkii Chat is a self-contained chat platform with three parts:

1. **Chat Server** (`server.py`) — A lightweight Flask server that hosts room-based chat with message persistence
2. **Smart Agent** (`agent.py`) — A 24/7 autonomous coding agent with a self-adapting harness that lives in the chat and works on projects
3. **Chat UI** (`ui/`) — A web-based chat interface that can be embedded into any application

The agent lives inside the chat room, polls for messages, and responds to commands. It can:
- Create, edit, and delete files
- Run PowerShell commands
- Build and deploy projects
- Search codebases
- Plan tasks step-by-step
- Verify its own work
- Update a universal journal
- Auto-configure its workflow on the fly

## How It Connects to Devin

Wakkii Chat uses a **Universal Devin Connector** (`connector.py`) that:

### For the original author (Justin):
- Auto-detects the author's machine
- Auto-configures with a pre-registered Devin token
- The author's Devin account is protected — no one else can access it

### For other users:
- Runs an interactive setup flow on first launch
- Asks for a Devin API key from https://devin.ai/settings
- Encrypts and stores the token locally using machine-specific encryption
- The token never leaves the machine except to talk to Devin's official API
- Each user connects their own Devin account

### Connection flow:
```
Download → start.ps1 → connector.py runs → 
  If author machine: auto-connect with pre-configured token
  If new user: prompt for Devin API key → encrypt and store → connect
→ Agent comes online in chat → UI auto-creates at bottom → 
  Agent says: "Hi! I'm awaiting project ideas. Let's plan first, then scale over time."
```

## The Smart Harness

The agent uses a **self-adapting smart harness** that auto-configures on the fly:

### How it works:
The harness monitors the agent's behavior and adjusts its parameters:

| Metric | What triggers adaptation | What changes |
|--------|------------------------|-------------|
| Loop count | Agent repeats same output 2+ times | Increases prompt strictness, reduces loop threshold |
| Error count | 3+ command failures | Increases error analysis depth |
| False verify | Verification passes but work is broken | Increases verification depth |
| Step too large | Steps cause too many errors | Switches to smaller step granularity |
| Context overflow | Conversation too long | Trims context more aggressively |

### Workflow phases:
1. **INTAKE** — receive task, understand what's being asked
2. **PLAN** — break task into concrete steps
3. **EXPLORE** — read files, run commands, understand current state
4. **EXECUTE** — make changes one at a time
5. **VERIFY** — check that changes work (build, test, run)
6. **REPORT** — update journal, report progress to chat
7. **ADAPT** — auto-configure harness parameters based on what worked

### Tools the agent uses:
- `RUN: <command>` — execute a PowerShell command
- `READ: <file>` — read a file's contents
- `WRITE: <file>` — create/overwrite a file
- `SEARCH: <pattern>` — search for text in project files
- `PLAN: <description>` — declare a step-by-step plan
- `PROGRESS: <what's done>` — mark a step as complete
- `VERIFY: <what to check>` — declare verification
- `DONE` — task is complete

## Installation

### Prerequisites
- Python 3.11+
- Windows (PowerShell commands)
- A Devin AI account (for the agent's reasoning) — optional, agent can fall back to local LLM

### Quick Start
```powershell
git clone https://github.com/singularitycurse26-svg/wakkii-chat.git
cd wakkii-chat
.\start.ps1
```

### Manual Start
```powershell
pip install -r requirements.txt

# Terminal 1 — start chat server
python server.py

# Terminal 2 — start agent
python agent.py
```

### Open the Chat UI
Navigate to `http://localhost:8085` in your browser.

## Embedding the Widget

Drop the widget into any HTML page:

```html
<script src="wakkii-widget.js" 
        data-api="http://localhost:8085" 
        data-room="AGENT"
        data-user="Justin"></script>
```

The widget auto-creates a floating chat button at the bottom-right of the page.
Click it to open the chat panel. On first load, it auto-opens and the agent greets you.

### JavaScript API:
```javascript
WakkiiWidget.init({ api: 'http://localhost:8085', room: 'AGENT', user: 'Justin' });
WakkiiWidget.open();   // open the chat panel
WakkiiWidget.close();  // close the chat panel
WakkiiWidget.send('hello');  // send a message
```

## Chat Commands

| Command | What it does |
|---------|-------------|
| `work on <task>` | Queue a task for the agent |
| `fix <thing>` | Queue a fix task |
| `build <feature>` | Queue a build task |
| `yes` / `go` | Approve queued task — agent starts working |
| `no` / `cancel` | Cancel queued task |
| `status` | Show current work queue |
| `add goal: <text>` | Add a long-term goal |
| Any other text | Chat with the agent |

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/wakkii/rooms` | List all rooms |
| GET | `/wakkii/rooms/{id}/messages` | Get messages in a room |
| POST | `/wakkii/rooms/{id}/messages` | Post a message |
| DELETE | `/wakkii/rooms/{id}/messages` | Clear messages |
| GET | `/devin/status` | Check Devin connection |
| POST | `/devin/connect` | Connect to Devin |

## Configuration

Environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `WAKKII_API` | `http://127.0.0.1:8085` | Chat server URL |
| `WAKKII_PORT` | `8085` | Server port |
| `WAKKII_HOST` | `0.0.0.0` | Server bind address |
| `WAKKII_ROOM` | `AGENT` | Default room ID |
| `DEVIN_TOKEN` | (empty) | Devin API token |
| `DEVIN_API` | `https://api.devin.ai` | Devin API base URL |
| `WINDSURF_API` | `http://127.0.0.1:3003` | Fallback LLM API |
| `WINDSURF_KEY` | `local-dev-key-openmausbot` | Fallback LLM key |
| `WAKKII_MODEL` | `glm-5.1` | LLM model name |
| `PROJECTS_ROOT` | `C:\Users\hawpe\CascadeProjects` | Projects directory |

## Security

- Devin tokens are encrypted with machine-specific keys before storage
- The author's Devin account is protected — other users connect their own accounts
- No tokens are transmitted except to Devin's official API
- Config files are in `~/.wakkii-chat/` and are gitignored

## File Structure

```
wakkii-chat/
├── server.py          # Chat server (Flask)
├── agent.py           # Smart harness agent
├── connector.py       # Universal Devin connector
├── start.ps1          # One-click start script
├── requirements.txt   # Python dependencies
├── .gitignore
├── ui/
│   ├── index.html     # Full-page chat UI
│   └── wakkii-widget.js  # Embeddable widget
└── data/              # Message persistence (gitignored)
```

## License

Free to use. Connect your own Devin account.

## Author

Justin Hawpetoss — Soulmate OS
