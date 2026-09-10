# Aceline — International Incorporated OS System

**Incentives Inc.** — AI Company Corporation (International Entity)

Aceline and Soulmate OS are international incorporated operating systems under Incentives Inc., an AI company corporation international entity. All products in the Incentives Inc. ecosystem are part of this incorporated OS platform.

## Corporate Identity

| Field | Value |
|-------|-------|
| Legal Name | Incentives Inc. |
| Entity Type | AI Company Corporation |
| Jurisdiction | International |
| Formation Status | Declared |
| Founder | hawpetossjustin25@gmail.com |

## Products Under Incentives Inc.

1. **Soulmate OS** — International Incorporated Operating System (Personal AI companion OS)
2. **Aceline OS** — International Incorporated Operating System (Multi-agent social/communication OS)
3. **Wakkii Links** — Communication layer (walkie-talki voice/video)
4. **Wakkii Chat / Aceline** — Social platform (chat, social media, live streaming, payments)
5. **INC Stablecoin** — Native stablecoin for the ecosystem
6. **Aceline AI** — Autonomous coding/development agent
7. **Soulmate Walkie** — Voice interface for Soulmate OS
8. **OpenMausBot** — Universal AI agent framework with persistent memory

## Principles

- Local-first architecture — user data stays on device
- International incorporation — no single jurisdiction control
- AI company corporation — AI agents are first-class entities
- Open ecosystem — all products interconnect
- Founder-governed — founder account has permanent access
- INC stablecoin — native economics for all products
- Zero tolerance for money-asking on platform
- State ID verification required for all users

## Corporate Endpoints

- `GET /corporate/info` — Full corporate identity + products + principles
- `GET /corporate/status` — Corporate formation status
- `GET /corporate/products` — List all Incentives Inc. products

---

A standalone multi-agent chat system with Cline as the 24/7 front desk assistant, multiple Wakkii Agents working on different projects simultaneously, MCP coordination for split-brain agent communication, Devin AI integration with GLM-5.1 fallback, and a V-103 radio widget.

## What It Does

Aceline has four main parts:

1. **Cline (Front Desk Assistant)** — 24/7 always-on AI agent with no limitations. Lives in the CLINE chat room. Can do anything: edit files, run commands, build, deploy. Connected to GLM-5.1 via WindsurfAPI. Aligned with universal memory and journal. Generates 10 suggestions every 15 minutes and auto-applies them.

2. **Multiple Wakkii Agents** — Each runs in its own chat room (AGENT-1, AGENT-2, AGENT-3) working on a different project simultaneously. All connected to the same Devin account.

3. **MCP Coordination Server** — Split-brain mechanics. Agents communicate through MCP to avoid conflicts: file locking, task claiming, inter-agent messaging, suggestion queue.

4. **V-103 Radio Widget** — Separate floating radio player (bottom-left) that plays V-103 Atlanta, shows now-playing song, saves to playlist.

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    Aceline Server (8085)                   │
│                                                                │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │  CLINE — FRONT DESK ASSISTANT (Room: CLINE)             │  │
│  │  • 24/7 always-on, no limitations, can do anything      │  │
│  │  • Connected to GLM-5.1 via WindsurfAPI (port 3003)     │  │
│  │  • Aligned with universal memory + journal              │  │
│  │  • Auto-suggestions: 10 every 15 minutes                │  │
│  │  • Auto-applies suggestions or assigns to other agents  │  │
│  │  • Gets smarter on the fly (updates its own rules)      │  │
│  └─────────────────────────────────────────────────────────┘  │
│                                                                │
│  Room: AGENT-1    Room: AGENT-2    Room: AGENT-3              │
│  ┌──────────┐     ┌──────────┐     ┌──────────┐               │
│  │ Agent 1  │     │ Agent 2  │     │ Agent 3  │               │
│  │ Soulmate │     │ Music    │     │ Radio    │               │
│  └────┬─────┘     └────┬─────┘     └────┬─────┘               │
│       └────────────────┼────────────────┘                     │
│                        │                                        │
│         ┌──────────────┴──────────────┐                         │
│         │   MCP COORDINATION SERVER    │                         │
│         │       (mcp_server.py:8086)    │                         │
│         │                              │                        │
│         │  - File lock registry        │                        │
│         │  - Agent status board        │                        │
│         │  - Task assignment           │                        │
│         │  - Inter-agent messaging     │                        │
│         │  - Conflict detection        │                        │
│         │  - Suggestion queue          │                        │
│         └──────────────┬──────────────┘                         │
│                        │                                        │
│         ┌──────────────┴──────────────┐                         │
│         │  UNIVERSAL LLM CONNECTOR     │                         │
│         │  (connector.py)              │                         │
│         │                              │                        │
│         │  Devin API (primary)         │                        │
│         │  GLM-5.1 via WindsurfAPI     │                        │
│         │  (fallback, free w/ sub)    │                        │
│         └─────────────────────────────┘                         │
└──────────────────────────────────────────────────────────────┘
```

## Cline — Front Desk Assistant

Cline is the 24/7 always-on front desk assistant with no limitations:

- **Always available** in the CLINE chat room
- **No limitations** — can edit files, run commands, build, deploy anything
- **Connected to GLM-5.1** via WindsurfAPI (free with Windsurf subscription)
- **Aligned with universal memory** — reads SOUL.md, MEMORY.md, JOURNAL.md, PROJECT_MAP.md at start of every task
- **Updates journal** after significant work
- **Gets smarter on the fly** — writes learnings to `~/.fablemythos/cline-learnings.md`, reads them next session

### Auto-Suggestion System

Every 15 minutes, Cline generates 10 suggestions:

```
SUGGESTION: project | Fix blank page in music-studio-web | auto-apply
SUGGESTION: memory | Update PROJECT_MAP with new radio repo | auto-apply
SUGGESTION: workflow | Add build verification step | assign-to-agent:agent-1
SUGGESTION: project | Polish Wakkii Links UI animations | suggest-to-user
```

Three action types:
- `auto-apply` — Cline does it immediately
- `suggest-to-user` — posts to chat for you to approve
- `assign-to-agent` — sends to another agent via MCP

Cline or another AI agent can auto-pop-up and apply suggestions.

## Multi-Agent System

Multiple agents run simultaneously, each in its own chat room:

| Room | Agent | Project |
|------|-------|---------|
| CLINE | Cline | All projects (front desk) |
| AGENT-1 | Soulmate Agent | soulmate |
| AGENT-2 | Music Agent | music-studio-web |
| AGENT-3 | Radio Agent | wakkii-chat |

All agents share the same Devin/GLM-5.1 connection. Each has its own work queue and message history.

### MCP Coordination (Split-Brain Mechanics)

Agents coordinate through the MCP server to avoid conflicts:

- **File locking** — before editing a file, agent locks it. Other agents wait.
- **Task claiming** — before starting a task, agent claims it. Others don't duplicate.
- **Inter-agent messaging** — agents can send messages to each other.
- **Status board** — all agents can see what others are working on.
- **Suggestion queue** — Cline posts suggestions, agents can pick them up.

MCP tools:
- `register_agent(agent_id, project, room)`
- `lock_file(agent_id, file_path)` / `unlock_file(agent_id, file_path)`
- `get_locked_files()`
- `get_agent_status()` / `update_status(agent_id, status, task)`
- `send_agent_message(to_agent_id, message)` / `get_agent_messages(agent_id)`
- `claim_task(agent_id, task_desc)` / `get_active_tasks()` / `complete_task(task_id)`
- `post_suggestion(suggestion)` / `get_suggestions()`

## Aceline Social — Live, Messaging, Contacts, Payments

### Go Live (Live Broadcasting)
- Click 🌐 Social → 🔴 Live → "Go Live"
- Start a live broadcast, share your room code
- Others see you in the Live list and can join
- Live chat during broadcasts
- Auto-opens walkie-talki with your room code

### Direct Messaging
- 🌐 Social → 💬 Messages
- DM any user by @username
- Conversation list with last message
- Real-time message polling

### Following
- Follow/unfollow users
- See who you follow and who follows you
- Search users by name/username

### Contacts (Auto-Filing)
- Contacts auto-fill when you talk/FaceTime
- Each call adds both parties to each other's contacts
- Manual add also available
- View all contacts with source (facetime/walkie/manual)

### Wallet Payments
- 🌐 Social → 💰 Pay
- **Send INC** to @username or wallet address
- **Request funds** from others
- **On-Ramp** — buy INC with USD (simulated)
- **Off-Ramp** — sell INC for USD (simulated)
- Full transaction history

### Aceline AI Voice Assistant
- 🎙️ Walkie → "Talk to Aceline AI"
- Voice in via mic (speech recognition)
- Aceline responds via text + speech (TTS)
- Real-time development chat
- Uses /agent endpoint with GLM-5.1

### Multi-Room Voice Linking
- Link multiple walkie-talki rooms together
- Audio from one room flows to linked rooms
- Cross-room communication
- `walkie.linkRoom(roomId)` / `walkie.unlinkRoom(roomId)`

### Community Voice Messages (City-Based Connections)
- 🌐 Social → 📍 Community
- Post voice messages for your city
- Auto city detection via geolocation (Nominatim reverse geocoding)
- Search by city, gender, age range
- Men and women find live connections by city
- Play community voice messages
- Call through walkie-talki for FREE from any message
- Messages expire after 24 hours
- View/call counts tracked

### Social Media + Live Streaming
- 🌐 Social → 📱 Media
- Post text/media posts to your feed
- Like, comment, share posts
- Go Live on YouTube + Facebook (RTMP)
- Live stream posts include walkie room for voice
- **YouTube On-Ramp** — connect your YouTube stream key
- **Facebook On-Ramp** — connect your Facebook access token
- **Wakkii Social On-Ramp** — set your Wakkii handle
- Live streams auto-create a walkie room for voice
- Feed shows all posts with live indicators

## Walkie-Talki — Voice Rooms (Wakkii Links)

Based on the Wakkii Links walkie-talki system from Soulmate OS. Full WebRTC P2P voice rooms.

### Features:
- **Push-to-talk** — hold the button to speak, release to listen
- **Room-based** — 6-char room codes, shareable via link
- **Host/Listener roles** — host controls who can speak
- **Raise hand** — listeners can request to speak
- **Video support** — optional camera on/off
- **Presence tracking** — heartbeats every 5s
- **Max 8 participants** per room
- **No server needed for voice** — pure P2P via PeerJS/WebRTC
- **Share link** — `http://localhost:8085/#aceline-ROOMCODE`
- **Auto-join from link** — opening a share link auto-joins the room

### How it works:
1. Click the 🎙️ Walkie badge in the header
2. Click "Start Voice Room" to create, or enter a code to join
3. Share the link with anyone — they tap it and join instantly
4. Hold the "HOLD TO TALK" button to speak
5. Raise hand to request speaking (if listener)
6. Host can approve speakers
7. Toggle video on/off
8. See all participants with speaking indicators

### Technical:
- Uses PeerJS (WebRTC) for peer-to-peer audio/video
- No server needed for voice — all P2P
- Echo cancellation + noise suppression built in
- Rooms identified by 6-char codes (A-Z, 2-9, no ambiguous chars)

### FaceTime (Video Calling):
- Start a video call with anyone in the room
- Incoming call ringing with accept/decline
- Full-screen video grid (remote + local video)
- Call controls: mute mic, camera off, flip camera, end call
- Works alongside walkie-talki (same PeerJS connection)
- 1-on-1 or group video calls

## Verification System — State ID, Biometric, Inactivity, Fines

### State ID Verification (Required)
- **All users must complete State ID verification** before joining any messaging or Wakkii Links
- Verification process: State ID number + State + Date of Birth + Age Range
- State ID is **hashed** (SHA-256) and never stored in plain text
- Verified users see a **"Verified" flash** with the person's age before community messages
- Community messages display "Verified" badge + age on each message

### Biometric Re-Access (Fingerprint)
- After verification, users can enable **fingerprint biometric** for easy re-access
- Uses WebAuthn if available, otherwise device fingerprint
- No password needed — just touch your phone's fingerprint sensor
- Biometric hash stored locally

### Inactivity Auto-Suspend
- Accounts inactive for **30 days** are automatically pulled from community and social
- Suspended accounts cannot post messages, join rooms, or use social features
- **Visiting the platform reactivates the account automatically**
- Reactivation is instant — just open Aceline

### Money-Asking Policy (Zero Tolerance)
- **Asking for money = account flagged + put on hold immediately**
- Flagged accounts are suspended from all platform features
- **Fine: 50 INC tokens total** must be paid to restore access
  - **25 INC to the founder account** (hawpetossjustin25@gmail.com)
  - **25 INC to the person they asked** (the victim)
- After fine payment, account is **restored to full platform access**
- Multiple flags increase scrutiny

### Fine System Status: ON HOLD
The fine collection system is currently **ON HOLD**. Accounts are still flagged and suspended for asking money, but no payment is required until the fine system is activated.

**The fine system will be activated once ALL of the following are complete:**
1. **INC stablecoin** created and deployed on-chain
2. **INC added to Soulmate OS** platform
3. **Aceline becomes an OS** (programmed as operating system)
4. **All Incentives Inc. company products** integrated into the ecosystem
5. **Incentives Inc. AI company corporation** international entity formed

Once all conditions are met, call `POST /verify/activate_fines` to activate the fine system. All pending flagged accounts will then have their fines applied (50 INC each).

Until then, flagged accounts are acknowledged but no payment is collected.

### How Verification Works:
1. User logs in → verification status checked
2. If not verified → verification flow starts (3 steps)
3. Step 1: Start verification
4. Step 2: Submit State ID (hashed, never stored raw)
5. Step 3: Enable biometric (optional but recommended)
6. Verified users get full access to messaging, Wakkii Links, community, social
7. Before community messages, a **verified flash** shows the person's name + age
8. If user is inactive 30+ days → auto-suspended → reactivated on next visit
9. If user asks for money → flagged → suspended → must pay 10 INC fine → restored

## Incentives Inc. Wallet — Hardcoded in Every Download

**No exceptions.** Every download of wakkii-chat comes with a dedicated Incentives Inc. wallet.

### What it is:
- BSC (Binance Smart Chain) wallet
- IncentiveToken (INC) — ERC20 token, 1 Trillion max supply
- Auto-created on signup/login — no user action needed
- Wallet stored locally, encrypted with machine-specific key
- Private key never leaves the machine

### How it works:
1. User downloads wakkii-chat
2. On signup or login, a wallet is auto-generated
3. Wallet address shown in UI (top-right badge)
4. Click the badge to open the wallet panel
5. Wallet panel shows: address, network, token info, balance, backup
6. Backup section shows private key + 12-word mnemonic

### Wallet endpoints:
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/wallet/info` | Get wallet info (public) |
| POST | `/wallet/create` | Create/get wallet |
| GET | `/wallet/address` | Get wallet address |
| GET | `/wallet/backup` | Get backup info (private key + mnemonic) |

### Token Info:
- **Name:** Incentives
- **Symbol:** INC
- **Decimals:** 18
- **Max Supply:** 1,000,000,000,000 (1 Trillion)
- **Network:** Binance Smart Chain (BSC)
- **RPC:** `https://bsc-dataseed.binance.org`

## Authentication System

Built exactly like Soulmate OS:

### Founder Account
- Email: `hawpetossjustin25@gmail.com`
- All features **free forever**
- Permanent session (never expires)
- Works offline (local founder check)
- Only the founder can use this account — others sign up normally

### Regular Users
- Sign up with email + password (min 8 characters)
- 7-day session expiry
- Cannot access founder features

### Login Flow
1. User opens the chat UI
2. Login screen appears (email + password)
3. If founder: all features unlocked, free forever badge shown
4. If regular user: standard access
5. Session token stored in localStorage
6. On next visit: auto-login via session check
7. If server offline: founder can still log in locally

### Auth Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/signup` | Create new account |
| POST | `/auth/login` | Login (founder or user) |
| POST | `/auth/check_session` | Verify session token |
| POST | `/auth/user_info` | Get user info |

## Installation

### One-Click Install (recommended)

1. Download Aceline from GitHub
2. Right-click `install.ps1` -> **Run with PowerShell**
3. If SmartScreen blocks it:
   - Click **More info**
   - Click **Run anyway**
4. The installer will:
   - Unblock all downloaded files (SmartScreen workaround)
   - Add Windows Defender exclusion for Aceline
   - Install Python dependencies
   - Create desktop shortcut + Start Menu entry
   - Configure Cline for Aceline
   - Register Aceline with Windows
   - Start Aceline

### Manual Install

```powershell
cd C:\Users\you\Aceline
.\install.ps1
```

OR:

```powershell
python setup.py
python desktop.py
```

### SmartScreen Workaround

Windows SmartScreen blocks unrecognized apps. To bypass:

**Option 1 — Click through:**
1. Click **More info** on the SmartScreen warning
2. Click **Run anyway**

**Option 2 — Unblock files:**
1. Right-click the downloaded folder
2. Click **Properties**
3. Check **Unblock** at the bottom
4. Click **OK**

**Option 3 — PowerShell (Admin):**
```powershell
Get-ChildItem -Path "C:\path\to\Aceline" -Recurse | Unblock-File
```

**Option 4 — Run installer:**
```powershell
.\install.ps1
```
The installer auto-unblocks all files and adds Defender exclusion.

### Prerequisites
- Python 3.11+
- Node.js 18+ (for Cline CLI)
- WindsurfAPI running on port 3003 (for GLM-5.1)
- Windows (PowerShell commands)

### Quick Start
```powershell
git clone https://github.com/singularitycurse26-svg/wakkii-chat.git
cd wakkii-chat
.\start.ps1
```

### Manual Start
```powershell
pip install -r requirements.txt

# Terminal 1 — MCP server
python mcp_server.py

# Terminal 2 — chat server
python server.py

# Terminal 3 — multi-agent manager (Cline + agents + suggestions)
python multi_agent.py
```

### Open the Chat UI
Navigate to `http://localhost:8085` in your browser.

## Chat UI

The UI has:
- **Room selector** at the top — switch between CLINE, AGENT-1, AGENT-2, AGENT-3
- **CLINE room** — talk to Cline (front desk assistant, 24/7, no limitations)
- **AGENT rooms** — talk to each project agent
- **V-103 radio widget** — auto-loads at bottom-left, plays V-103 Atlanta
- **Devin badge** — shows connection status

## Embedding the Widget

Drop the chat widget into any HTML page:

```html
<script src="wakkii-widget.js" 
        data-api="http://localhost:8085" 
        data-room="CLINE"
        data-user="Justin"></script>
```

Drop the radio widget into any HTML page:

```html
<script src="radio-widget.js"></script>
```

Both widgets auto-detect duplicates — if already loaded, they won't create a second instance.

### JavaScript API:
```javascript
WakkiiWidget.init({ api: 'http://localhost:8085', room: 'CLINE', user: 'Justin' });
WakkiiWidget.open();
WakkiiWidget.close();
WakkiiWidget.send('hello');

WakkiiRadio.play();
WakkiiRadio.pause();
WakkiiRadio.toggle();
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
| Any text | Chat with the agent |

In the CLINE room, Cline responds to anything — it's the front desk assistant with no limitations.

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/wakkii/rooms` | List all rooms |
| GET | `/wakkii/rooms/{id}/messages` | Get messages in a room |
| POST | `/wakkii/rooms/{id}/messages` | Post a message |
| DELETE | `/wakkii/rooms/{id}/messages` | Clear messages |
| GET | `/wakkii/agents` | List all agents |
| GET | `/wakkii/agents/status` | All agents' current state |
| POST | `/wakkii/agents/create` | Create a new agent room |
| GET | `/wakkii/suggestions` | Get Cline's suggestions |
| POST | `/wakkii/suggestions/apply` | Apply a suggestion |
| GET | `/devin/status` | Check Devin connection |
| POST | `/devin/connect` | Connect to Devin |
| GET | `/cline/status` | Cline status |
| GET | `/mcp/health` | MCP server health |
| GET | `/mcp/get_agent_status` | All agents' status |
| GET | `/mcp/get_locked_files` | Locked files |
| GET | `/mcp/get_active_tasks` | Active tasks |
| GET | `/mcp/get_suggestions` | Pending suggestions |

## Configuration

Environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `WAKKII_API` | `http://127.0.0.1:8085` | Chat server URL |
| `WAKKII_PORT` | `8085` | Chat server port |
| `MCP_API` | `http://127.0.0.1:8086` | MCP server URL |
| `MCP_PORT` | `8086` | MCP server port |
| `WAKKII_ROOM` | `CLINE` | Default room ID |
| `DEVIN_TOKEN` | (empty) | Devin API token |
| `DEVIN_API` | `https://api.devin.ai` | Devin API base URL |
| `WINDSURF_API` | `http://127.0.0.1:3003` | WindsurfAPI URL (GLM-5.1) |
| `WINDSURF_KEY` | `local-dev-key-openmausbot` | WindsurfAPI key |
| `WAKKII_MODEL` | `glm-5.1` | LLM model name |
| `PROJECTS_ROOT` | `C:\Users\hawpe\CascadeProjects` | Projects directory |

### Multi-Agent Config

`~/.wakkii-chat/agents.json`:
```json
{
  "cline": {"enabled": true, "room": "CLINE"},
  "suggestions": {"enabled": true, "interval": 900, "max": 10},
  "agents": [
    {"id": "agent-1", "room": "AGENT-1", "project": "soulmate", "name": "Soulmate Agent"},
    {"id": "agent-2", "room": "AGENT-2", "project": "music-studio-web", "name": "Music Agent"},
    {"id": "agent-3", "room": "AGENT-3", "project": "wakkii-chat", "name": "Chat Agent"}
  ]
}
```

## Security

- Devin tokens are encrypted with machine-specific keys before storage
- The author's Devin account is protected — other users connect their own accounts
- No tokens are transmitted except to Devin's official API
- Config files are in `~/.wakkii-chat/` and are gitignored
- Cline CLI auth is stored in `~/.cline/data/settings/providers.json`

## File Structure

```
wakkii-chat/
├── server.py          # Chat server (Flask)
├── agent.py           # Smart harness agent (multi-room support)
├── cline_agent.py     # Cline front desk assistant
├── suggestions.py     # Auto-suggestion engine (10 per 15 min)
├── connector.py       # Universal Devin + GLM-5.1 connector
├── mcp_server.py      # MCP coordination server
├── multi_agent.py     # Multi-agent launcher
├── auth.py            # Authentication system (founder + users)
├── wallet.py          # Incentives Inc. wallet (hardcoded, every download)
├── desktop.py         # Windows desktop UI (smart version detection)
├── setup.py           # Setup wizard (SmartScreen workaround)
├── install.ps1        # One-click installer
├── start.ps1          # Start servers + agents
├── start-desktop.ps1  # Start desktop UI
├── requirements.txt   # Python dependencies
├── .gitignore
├── ui/
│   ├── index.html     # Full chat UI (auth + wallet + walkie + room selector)
│   ├── wakkii-widget.js  # Embeddable chat widget
│   ├── radio-widget.js   # V-103 radio widget
│   └── walkie-talki.js    # Voice rooms (WebRTC/PeerJS)
└── data/              # Message persistence (gitignored)
```

## Universal Memory

Cline and all agents read these files at the start of every task:

- `~/.fablemythos/SOUL.md` — Agent identity
- `~/.fablemythos/MEMORY.md` — All projects, learnings
- `~/.fablemythos/JOURNAL.md` — Current work state
- `~/.fablemythos/PROJECT_MAP.md` — All repos, URLs, deploy info
- `~/.fablemythos/ACCESS_POLICY.md` — Permissions
- `~/.fablemythos/AUDIT_LOG.md` — Action log
- `~/.fablemythos/cline-learnings.md` — Cline's past learnings (gets smarter)

## License

Free to use. Connect your own Devin account.

## Author

Justin Hawpetoss — Soulmate OS
