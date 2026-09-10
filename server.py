"""
Wakkii Chat Server — Standalone room-based chat backend
Stores messages in memory (with optional file persistence).
Zero dependencies beyond Python stdlib + Flask.
"""
import json
import os
import time
from datetime import datetime
from flask import Flask, jsonify, request, send_file, send_from_directory

app = Flask(__name__, static_folder="ui")

# In-memory message store: {room_id: [messages]}
rooms = {}
# Optional file persistence
DATA_DIR = os.environ.get("WAKKII_DATA", os.path.join(os.path.dirname(__file__), "data"))
os.makedirs(DATA_DIR, exist_ok=True)

def persist_room(room_id):
    try:
        path = os.path.join(DATA_DIR, f"{room_id}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(rooms.get(room_id, []), f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def load_room(room_id):
    try:
        path = os.path.join(DATA_DIR, f"{room_id}.json")
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                rooms[room_id] = json.load(f)
    except Exception:
        pass

@app.route("/health")
def health():
    return jsonify({"status": "ok", "service": "wakkii-chat", "time": datetime.now().isoformat()})

@app.route("/devin/status")
def devin_status():
    try:
        from connector import check_devin_connection, is_configured
        if not is_configured():
            return jsonify({"connected": False, "reason": "not_configured"})
        result = check_devin_connection()
        return jsonify(result)
    except Exception as e:
        return jsonify({"connected": False, "reason": str(e)})

@app.route("/devin/connect", methods=["POST"])
def devin_connect():
    try:
        from connector import store_token, auto_connect
        body = request.json or {}
        token = body.get("token", "")
        if token:
            store_token(token, account_type="user")
            return jsonify({"status": "connected", "account_type": "user"})
        result = auto_connect()
        return jsonify(result)
    except Exception as e:
        return jsonify({"status": "error", "reason": str(e)})

@app.route("/wakkii/rooms")
def list_rooms():
    return jsonify({"rooms": list(rooms.keys())})

@app.route("/wakkii/rooms/<room_id>/messages", methods=["GET"])
def get_messages(room_id):
    if room_id not in rooms:
        load_room(room_id)
    return jsonify({"messages": rooms.get(room_id, [])})

@app.route("/wakkii/rooms/<room_id>/messages", methods=["POST"])
def post_message(room_id):
    if room_id not in rooms:
        load_room(room_id)
        if room_id not in rooms:
            rooms[room_id] = []
    body = request.json or {}
    msg = {
        "sender": body.get("sender", "unknown"),
        "text": body.get("text", ""),
        "timestamp": body.get("timestamp", datetime.now().isoformat()),
    }
    rooms[room_id].append(msg)
    persist_room(room_id)
    return jsonify({"status": "ok", "message": msg})

@app.route("/wakkii/rooms/<room_id>/messages", methods=["DELETE"])
def clear_messages(room_id):
    rooms[room_id] = []
    persist_room(room_id)
    return jsonify({"status": "ok"})

@app.route("/wakkii/agents")
def list_agents():
    try:
        import requests
        resp = requests.get("http://127.0.0.1:8086/mcp/get_agent_status", timeout=5)
        if resp.status_code == 200:
            return jsonify(resp.json())
    except Exception:
        pass
    return jsonify({"agents": {}})

@app.route("/wakkii/agents/status")
def agents_status():
    try:
        import requests
        resp = requests.get("http://127.0.0.1:8086/mcp/get_agent_status", timeout=5)
        if resp.status_code == 200:
            return jsonify(resp.json())
    except Exception:
        pass
    return jsonify({"agents": {}})

@app.route("/wakkii/agents/create", methods=["POST"])
def create_agent():
    body = request.json or {}
    room = body.get("room", f"AGENT-{int(time.time())}")
    project = body.get("project", "soulmate")
    name = body.get("name", f"Agent ({project})")
    return jsonify({"status": "ok", "room": room, "project": project, "name": name})

@app.route("/wakkii/suggestions")
def get_suggestions():
    try:
        import requests
        resp = requests.get("http://127.0.0.1:8086/mcp/get_suggestions", timeout=5)
        if resp.status_code == 200:
            return jsonify(resp.json())
    except Exception:
        pass
    return jsonify({"suggestions": []})

@app.route("/wakkii/suggestions/apply", methods=["POST"])
def apply_suggestion():
    body = request.json or {}
    desc = body.get("description", "")
    return jsonify({"status": "ok", "message": f"Applying: {desc}"})

@app.route("/cline/status")
def cline_status():
    return jsonify({
        "online": True,
        "room": "CLINE",
        "model": "glm-5.1",
        "backend": "WindsurfAPI",
        "suggestions_interval": 900,
        "max_suggestions": 10
    })

# --- Auth endpoints (built like Soulmate OS) ---

@app.route("/auth/signup", methods=["POST"])
def auth_signup():
    try:
        from auth import signup
        body = request.json or {}
        result = signup(body.get("email", ""), body.get("password", ""))
        return jsonify(result)
    except Exception as e:
        return jsonify({"status": "error", "detail": str(e)})

@app.route("/auth/login", methods=["POST"])
def auth_login():
    try:
        from auth import login
        body = request.json or {}
        result = login(body.get("email", ""), body.get("password", ""))
        return jsonify(result)
    except Exception as e:
        return jsonify({"status": "error", "detail": str(e)})

@app.route("/auth/check_session", methods=["POST"])
def auth_check_session():
    try:
        from auth import check_session
        body = request.json or {}
        token = body.get("session_token", "") or request.headers.get("Authorization", "").replace("Bearer ", "")
        result = check_session(token)
        return jsonify(result)
    except Exception as e:
        return jsonify({"status": "invalid"})

@app.route("/auth/user_info", methods=["POST"])
def auth_user_info():
    try:
        from auth import get_user_info
        body = request.json or {}
        token = body.get("session_token", "") or request.headers.get("Authorization", "").replace("Bearer ", "")
        result = get_user_info(token)
        return jsonify(result)
    except Exception as e:
        return jsonify({"status": "error", "detail": str(e)})

@app.route("/")
def serve_ui():
    return send_file(os.path.join("ui", "index.html"))

@app.route("/<path:path>")
def serve_static(path):
    return send_from_directory("ui", path)

if __name__ == "__main__":
    port = int(os.environ.get("WAKKII_PORT", "8085"))
    host = os.environ.get("WAKKII_HOST", "0.0.0.0")
    print(f"Wakkii Chat Server starting on {host}:{port}")
    print(f"UI: http://localhost:{port}")
    print(f"Health: http://localhost:{port}/health")
    app.run(host=host, port=port, debug=False)
