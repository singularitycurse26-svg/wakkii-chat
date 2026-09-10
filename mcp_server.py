"""
MCP Coordination Server — Split-brain agent coordination

Agents connect to this server to coordinate:
- File locking (don't edit same file)
- Agent status board (who's doing what)
- Inter-agent messaging
- Task claiming (don't work on same task)
- Suggestion queue

Runs on port 8086 alongside the chat server (8085).
Uses Flask for simplicity (no FastMCP dependency needed).
"""
import json
import os
import time
import threading
from datetime import datetime
from flask import Flask, jsonify, request

app = Flask(__name__)

# In-memory state (thread-safe with locks)
_state_lock = threading.Lock()
_agents = {}        # {agent_id: {project, room, status, last_seen, current_task}}
_file_locks = {}    # {file_path: {agent_id, locked_at, expires_at}}
_agent_msgs = {}    # {agent_id: [{from, message, timestamp}]}
_tasks = {}         # {task_id: {agent_id, desc, status, claimed_at}}
_suggestions = []   # [{type, description, action, timestamp, status}]

LOCK_TIMEOUT = 300  # 5 minutes

def now():
    return datetime.now().isoformat()

def cleanup_expired_locks():
    current = time.time()
    expired = [p for p, lock in _file_locks.items() if lock.get("expires_at", 0) < current]
    for p in expired:
        del _file_locks[p]

@app.route("/mcp/register_agent", methods=["POST"])
def register_agent():
    data = request.json or {}
    agent_id = data.get("agent_id", "")
    with _state_lock:
        _agents[agent_id] = {
            "project": data.get("project", ""),
            "room": data.get("room", ""),
            "status": "idle",
            "last_seen": now(),
            "current_task": "",
        }
        if agent_id not in _agent_msgs:
            _agent_msgs[agent_id] = []
    return jsonify({"status": "ok", "agent_id": agent_id})

@app.route("/mcp/lock_file", methods=["POST"])
def lock_file():
    data = request.json or {}
    agent_id = data.get("agent_id", "")
    file_path = data.get("file_path", "")
    with _state_lock:
        cleanup_expired_locks()
        if file_path in _file_locks:
            if _file_locks[file_path]["agent_id"] == agent_id:
                _file_locks[file_path]["expires_at"] = time.time() + LOCK_TIMEOUT
                return jsonify({"status": "ok", "locked": True, "owner": agent_id})
            return jsonify({"status": "locked", "locked": False, "owner": _file_locks[file_path]["agent_id"]})
        _file_locks[file_path] = {
            "agent_id": agent_id,
            "locked_at": now(),
            "expires_at": time.time() + LOCK_TIMEOUT,
        }
    return jsonify({"status": "ok", "locked": True, "owner": agent_id})

@app.route("/mcp/unlock_file", methods=["POST"])
def unlock_file():
    data = request.json or {}
    agent_id = data.get("agent_id", "")
    file_path = data.get("file_path", "")
    with _state_lock:
        if file_path in _file_locks and _file_locks[file_path]["agent_id"] == agent_id:
            del _file_locks[file_path]
            return jsonify({"status": "ok"})
        return jsonify({"status": "not_owner"})

@app.route("/mcp/get_locked_files", methods=["GET"])
def get_locked_files():
    with _state_lock:
        cleanup_expired_locks()
        return jsonify({"locked_files": _file_locks})

@app.route("/mcp/get_agent_status", methods=["GET"])
def get_agent_status():
    with _state_lock:
        return jsonify({"agents": _agents})

@app.route("/mcp/update_status", methods=["POST"])
def update_status():
    data = request.json or {}
    agent_id = data.get("agent_id", "")
    with _state_lock:
        if agent_id in _agents:
            _agents[agent_id]["status"] = data.get("status", "idle")
            _agents[agent_id]["current_task"] = data.get("current_task", "")
            _agents[agent_id]["last_seen"] = now()
    return jsonify({"status": "ok"})

@app.route("/mcp/send_agent_message", methods=["POST"])
def send_agent_message():
    data = request.json or {}
    to_id = data.get("to_agent_id", "")
    from_id = data.get("from_agent_id", "")
    message = data.get("message", "")
    with _state_lock:
        if to_id not in _agent_msgs:
            _agent_msgs[to_id] = []
        _agent_msgs[to_id].append({
            "from": from_id,
            "message": message,
            "timestamp": now(),
        })
    return jsonify({"status": "ok"})

@app.route("/mcp/get_agent_messages/<agent_id>", methods=["GET"])
def get_agent_messages(agent_id):
    with _state_lock:
        msgs = _agent_msgs.get(agent_id, [])
        _agent_msgs[agent_id] = []  # Clear after reading
    return jsonify({"messages": msgs})

@app.route("/mcp/claim_task", methods=["POST"])
def claim_task():
    data = request.json or {}
    agent_id = data.get("agent_id", "")
    task_desc = data.get("task_desc", "")
    task_id = f"task-{int(time.time())}-{agent_id}"
    with _state_lock:
        for tid, task in _tasks.items():
            if task["desc"] == task_desc and task["status"] == "claimed":
                return jsonify({"status": "already_claimed", "owner": task["agent_id"]})
        _tasks[task_id] = {
            "agent_id": agent_id,
            "desc": task_desc,
            "status": "claimed",
            "claimed_at": now(),
        }
    return jsonify({"status": "ok", "task_id": task_id})

@app.route("/mcp/get_active_tasks", methods=["GET"])
def get_active_tasks():
    with _state_lock:
        active = {tid: t for tid, t in _tasks.items() if t["status"] == "claimed"}
    return jsonify({"tasks": active})

@app.route("/mcp/complete_task", methods=["POST"])
def complete_task():
    data = request.json or {}
    task_id = data.get("task_id", "")
    with _state_lock:
        if task_id in _tasks:
            _tasks[task_id]["status"] = "complete"
            return jsonify({"status": "ok"})
    return jsonify({"status": "not_found"})

@app.route("/mcp/post_suggestion", methods=["POST"])
def post_suggestion():
    data = request.json or {}
    with _state_lock:
        _suggestions.append({
            "type": data.get("type", ""),
            "description": data.get("description", ""),
            "action": data.get("action", ""),
            "timestamp": now(),
            "status": "pending",
        })
    return jsonify({"status": "ok"})

@app.route("/mcp/get_suggestions", methods=["GET"])
def get_suggestions():
    with _state_lock:
        pending = [s for s in _suggestions if s["status"] == "pending"]
    return jsonify({"suggestions": pending})

@app.route("/mcp/health")
def health():
    return jsonify({
        "status": "ok",
        "service": "mcp-coordination",
        "agents": len(_agents),
        "locked_files": len(_file_locks),
        "active_tasks": sum(1 for t in _tasks.values() if t["status"] == "claimed"),
        "pending_suggestions": sum(1 for s in _suggestions if s["status"] == "pending"),
    })

if __name__ == "__main__":
    port = int(os.environ.get("MCP_PORT", "8086"))
    print(f"MCP Coordination Server starting on port {port}")
    app.run(host="0.0.0.0", port=port, debug=False)
