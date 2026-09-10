"""
Aceline Server — Standalone room-based chat backend
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

# --- Incentives Inc. Wallet endpoints (hardcoded — every download gets one) ---

@app.route("/wallet/info")
def wallet_info():
    """Get wallet info (public — no private key exposed)."""
    try:
        from wallet import get_wallet_info, ensure_wallet_exists
        ensure_wallet_exists()  # Auto-create if missing — no exceptions
        info = get_wallet_info()
        if info:
            return jsonify({"status": "ok", "wallet": info})
        return jsonify({"status": "error", "detail": "Wallet not found"})
    except Exception as e:
        return jsonify({"status": "error", "detail": str(e)})

@app.route("/wallet/create", methods=["POST"])
def wallet_create():
    """Create a new wallet (or return existing one)."""
    try:
        from wallet import get_or_create_wallet
        body = request.json or {}
        user_id = body.get("user_id", "default")
        wallet = get_or_create_wallet(user_id)
        return jsonify({
            "status": "ok",
            "address": wallet["address"],
            "mnemonic": wallet.get("mnemonic", ""),
            "created_at": wallet.get("created_at", ""),
            "network": "BSC",
            "token": "INC"
        })
    except Exception as e:
        return jsonify({"status": "error", "detail": str(e)})

@app.route("/wallet/address")
def wallet_address():
    """Get just the wallet address."""
    try:
        from wallet import get_wallet_address, ensure_wallet_exists
        ensure_wallet_exists()
        addr = get_wallet_address()
        if addr:
            return jsonify({"status": "ok", "address": addr})
        return jsonify({"status": "error", "detail": "No wallet"})
    except Exception as e:
        return jsonify({"status": "error", "detail": str(e)})

@app.route("/wallet/backup")
def wallet_backup():
    """Get wallet backup info (mnemonic + private key — for backup only)."""
    try:
        from wallet import load_wallet, ensure_wallet_exists
        ensure_wallet_exists()
        wallet = load_wallet()
        if wallet:
            return jsonify({
                "status": "ok",
                "address": wallet["address"],
                "private_key": wallet["privateKey"],
                "mnemonic": wallet.get("mnemonic", ""),
                "warning": "Keep this safe! Never share your private key or mnemonic."
            })
        return jsonify({"status": "error", "detail": "No wallet"})
    except Exception as e:
        return jsonify({"status": "error", "detail": str(e)})

# --- Social: Profiles, Following, Contacts, Messaging, Live ---

@app.route("/social/profile", methods=["POST"])
def social_profile():
    from social import create_or_update_profile
    body = request.json or {}
    result = create_or_update_profile(body.get("user_id",""), body.get("username",""),
        body.get("display_name"), body.get("bio"), body.get("avatar"))
    return jsonify(result or {"status": "error"})

@app.route("/social/profile/<user_id>")
def social_get_profile(user_id):
    from social import get_profile
    return jsonify(get_profile(user_id) or {"status": "error", "detail": "Not found"})

@app.route("/social/profile/by_username/<username>")
def social_get_by_username(username):
    from social import get_profile_by_username
    return jsonify(get_profile_by_username(username) or {"status": "error", "detail": "Not found"})

@app.route("/social/search")
def social_search():
    from social import search_users
    q = request.args.get("q", "")
    return jsonify({"results": search_users(q)})

@app.route("/social/follow", methods=["POST"])
def social_follow():
    from social import follow_user
    body = request.json or {}
    return jsonify(follow_user(body.get("follower_id",""), body.get("following_id","")))

@app.route("/social/unfollow", methods=["POST"])
def social_unfollow():
    from social import unfollow_user
    body = request.json or {}
    return jsonify(unfollow_user(body.get("follower_id",""), body.get("following_id","")))

@app.route("/social/following/<user_id>")
def social_get_following(user_id):
    from social import get_following
    return jsonify({"following": get_following(user_id)})

@app.route("/social/followers/<user_id>")
def social_get_followers(user_id):
    from social import get_followers
    return jsonify({"followers": get_followers(user_id)})

@app.route("/social/contacts/<owner_id>")
def social_get_contacts(owner_id):
    from social import get_contacts
    return jsonify({"contacts": get_contacts(owner_id)})

@app.route("/social/contacts/add", methods=["POST"])
def social_add_contact():
    from social import add_contact
    body = request.json or {}
    return jsonify(add_contact(body.get("owner_id",""), body.get("contact_id",""),
        body.get("contact_name",""), body.get("contact_username"), body.get("source","manual"), body.get("notes","")))

@app.route("/social/contacts/auto", methods=["POST"])
def social_auto_contact():
    from social import auto_add_contact_from_call
    body = request.json or {}
    auto_add_contact_from_call(body.get("owner_id",""), body.get("owner_name",""),
        body.get("contact_id",""), body.get("contact_name",""),
        body.get("contact_username",""), body.get("call_type","facetime"))
    return jsonify({"status": "ok"})

@app.route("/social/messages/send", methods=["POST"])
def social_send_msg():
    from social import send_message
    body = request.json or {}
    return jsonify(send_message(body.get("sender_id",""), body.get("receiver_id",""), body.get("text","")))

@app.route("/social/messages/<user_id>/<other_id>")
def social_get_msgs(user_id, other_id):
    from social import get_messages
    return jsonify({"messages": get_messages(user_id, other_id)})

@app.route("/social/conversations/<user_id>")
def social_get_convs(user_id):
    from social import get_conversations
    return jsonify({"conversations": get_conversations(user_id)})

@app.route("/social/unread/<user_id>")
def social_unread(user_id):
    from social import get_unread_count
    return jsonify({"count": get_unread_count(user_id)})

# --- Live Broadcasting ---

@app.route("/live/go_live", methods=["POST"])
def live_go():
    from social import go_live
    body = request.json or {}
    return jsonify(go_live(body.get("user_id",""), body.get("title","Live"), body.get("description",""), body.get("room_id")))

@app.route("/live/end", methods=["POST"])
def live_end():
    from social import end_live
    body = request.json or {}
    return jsonify(end_live(body.get("user_id","")))

@app.route("/live/broadcasts")
def live_list():
    from social import get_live_broadcasts
    return jsonify({"broadcasts": get_live_broadcasts()})

@app.route("/live/chat/send", methods=["POST"])
def live_chat_send():
    from social import send_live_chat
    body = request.json or {}
    return jsonify(send_live_chat(body.get("room_id",""), body.get("sender_id",""), body.get("sender_name",""), body.get("text","")))

@app.route("/live/chat/<room_id>")
def live_chat_get(room_id):
    from social import get_live_chat
    return jsonify({"messages": get_live_chat(room_id)})

# --- Payments ---

@app.route("/payments/send", methods=["POST"])
def pay_send():
    from payments import send_funds
    body = request.json or {}
    return jsonify(send_funds(body.get("sender_id",""), body.get("sender_address",""),
        body.get("receiver_id"), body.get("receiver_address"), body.get("amount",0),
        body.get("token","INC"), body.get("memo","")))

@app.route("/payments/request", methods=["POST"])
def pay_request():
    from payments import request_funds
    body = request.json or {}
    return jsonify(request_funds(body.get("requester_id",""), body.get("requester_address",""),
        body.get("amount",0), body.get("token","INC"), body.get("memo","")))

@app.route("/payments/requests/<user_id>")
def pay_get_requests(user_id):
    from payments import get_fund_requests
    return jsonify({"requests": get_fund_requests(user_id)})

@app.route("/payments/onramp", methods=["POST"])
def pay_onramp():
    from payments import onramp
    body = request.json or {}
    return jsonify(onramp(body.get("user_id",""), body.get("user_address",""),
        body.get("fiat_amount",0), body.get("fiat_currency","USD")))

@app.route("/payments/offramp", methods=["POST"])
def pay_offramp():
    from payments import offramp
    body = request.json or {}
    return jsonify(offramp(body.get("user_id",""), body.get("user_address",""),
        body.get("crypto_amount",0), body.get("crypto_token","INC")))

@app.route("/payments/history/<user_id>")
def pay_history(user_id):
    from payments import get_transaction_history
    return jsonify({"transactions": get_transaction_history(user_id)})

# --- Community Voice Messages ---

@app.route("/community/post", methods=["POST"])
def community_post():
    from community import post_message
    body = request.json or {}
    return jsonify(post_message(
        body.get("user_id",""), body.get("username",""), body.get("display_name",""),
        body.get("city",""), body.get("gender"), body.get("age_range"),
        body.get("state"), body.get("country","US"), body.get("lat"), body.get("lon"),
        body.get("title",""), body.get("description",""),
        body.get("audio_data"), body.get("duration",0), body.get("room_id")
    ))

@app.route("/community/messages")
def community_messages():
    from community import get_messages
    city = request.args.get("city")
    gender = request.args.get("gender")
    age_range = request.args.get("age_range")
    limit = int(request.args.get("limit", 50))
    offset = int(request.args.get("offset", 0))
    return jsonify({"messages": get_messages(city, gender, age_range, limit, offset)})

@app.route("/community/message/<msg_id>")
def community_get_msg(msg_id):
    from community import get_message
    return jsonify(get_message(msg_id) or {"status": "error", "detail": "Not found"})

@app.route("/community/call/<msg_id>", methods=["POST"])
def community_call(msg_id):
    from community import increment_calls
    return jsonify(increment_calls(msg_id))

@app.route("/community/delete/<msg_id>", methods=["POST"])
def community_delete(msg_id):
    from community import delete_message
    body = request.json or {}
    return jsonify(delete_message(msg_id, body.get("user_id","")))

@app.route("/community/cities")
def community_cities():
    from community import get_cities
    return jsonify({"cities": get_cities()})

@app.route("/community/my_messages/<user_id>")
def community_my_msgs(user_id):
    from community import get_user_messages
    return jsonify({"messages": get_user_messages(user_id)})

# --- Social Media: Posts, Feed, Likes, Comments, Live Streaming ---

@app.route("/media/post", methods=["POST"])
def media_post():
    from media import create_post
    body = request.json or {}
    return jsonify(create_post(
        body.get("user_id",""), body.get("username",""), body.get("display_name",""),
        body.get("text",""), body.get("media_type"), body.get("media_data"),
        body.get("media_url"), body.get("walkie_room_id"),
        body.get("is_live",False), body.get("live_platform"), body.get("live_url")
    ))

@app.route("/media/feed")
def media_feed():
    from media import get_feed
    user_id = request.args.get("user_id")
    following = request.args.get("following_only") == "true"
    limit = int(request.args.get("limit", 50))
    offset = int(request.args.get("offset", 0))
    return jsonify({"posts": get_feed(user_id, limit, offset, following)})

@app.route("/media/user/<user_id>")
def media_user_posts(user_id):
    from media import get_user_posts
    return jsonify({"posts": get_user_posts(user_id)})

@app.route("/media/post/<post_id>")
def media_get_post(post_id):
    from media import get_post
    return jsonify(get_post(post_id) or {"status": "error", "detail": "Not found"})

@app.route("/media/delete/<post_id>", methods=["POST"])
def media_delete(post_id):
    from media import delete_post
    body = request.json or {}
    return jsonify(delete_post(post_id, body.get("user_id","")))

@app.route("/media/like", methods=["POST"])
def media_like():
    from media import like_post
    body = request.json or {}
    return jsonify(like_post(body.get("post_id",""), body.get("user_id","")))

@app.route("/media/unlike", methods=["POST"])
def media_unlike():
    from media import unlike_post
    body = request.json or {}
    return jsonify(unlike_post(body.get("post_id",""), body.get("user_id","")))

@app.route("/media/comment", methods=["POST"])
def media_comment():
    from media import add_comment
    body = request.json or {}
    return jsonify(add_comment(body.get("post_id",""), body.get("user_id",""), body.get("username",""), body.get("text","")))

@app.route("/media/comments/<post_id>")
def media_get_comments(post_id):
    from media import get_comments
    return jsonify({"comments": get_comments(post_id)})

# --- Stream On-Ramps ---

@app.route("/media/onramp/youtube", methods=["POST"])
def media_onramp_youtube():
    from media import set_youtube_rtmp
    body = request.json or {}
    return jsonify(set_youtube_rtmp(body.get("user_id",""), body.get("rtmp_key",""), body.get("channel_id")))

@app.route("/media/onramp/facebook", methods=["POST"])
def media_onramp_facebook():
    from media import set_facebook_token
    body = request.json or {}
    return jsonify(set_facebook_token(body.get("user_id",""), body.get("access_token",""), body.get("page_id")))

@app.route("/media/onramp/wakkii", methods=["POST"])
def media_onramp_wakkii():
    from media import set_wakkii_handle
    body = request.json or {}
    return jsonify(set_wakkii_handle(body.get("user_id",""), body.get("handle","")))

@app.route("/media/keys/<user_id>")
def media_get_keys(user_id):
    from media import get_stream_keys
    return jsonify(get_stream_keys(user_id))

# --- Live Streams ---

@app.route("/media/stream/start", methods=["POST"])
def media_stream_start():
    from media import start_stream
    body = request.json or {}
    return jsonify(start_stream(
        body.get("user_id",""), body.get("username",""), body.get("title",""),
        body.get("platform",""), body.get("rtmp_url",""), body.get("stream_key",""),
        body.get("walkie_room_id")
    ))

@app.route("/media/stream/end", methods=["POST"])
def media_stream_end():
    from media import end_stream
    body = request.json or {}
    return jsonify(end_stream(body.get("stream_id","")))

@app.route("/media/streams/active")
def media_streams_active():
    from media import get_active_streams
    return jsonify({"streams": get_active_streams()})

# --- Verification (State ID, Biometric, Inactivity, Fines) ---

@app.route("/verify/start", methods=["POST"])
def verify_start():
    from verification import start_verification
    body = request.json or {}
    return jsonify(start_verification(body.get("user_id",""), body.get("username",""), body.get("email","")))

@app.route("/verify/state_id", methods=["POST"])
def verify_state_id():
    from verification import submit_state_id
    body = request.json or {}
    return jsonify(submit_state_id(body.get("user_id",""), body.get("state_id",""),
        body.get("state",""), body.get("dob",""), body.get("age_range","")))

@app.route("/verify/biometric/enable", methods=["POST"])
def verify_bio_enable():
    from verification import enable_biometric
    body = request.json or {}
    return jsonify(enable_biometric(body.get("user_id",""), body.get("biometric_data","")))

@app.route("/verify/biometric/check", methods=["POST"])
def verify_bio_check():
    from verification import verify_biometric
    body = request.json or {}
    return jsonify(verify_biometric(body.get("user_id",""), body.get("biometric_data","")))

@app.route("/verify/status/<user_id>")
def verify_status(user_id):
    from verification import get_verification_status, check_inactivity
    status = get_verification_status(user_id)
    inactivity = check_inactivity(user_id)
    return jsonify({**status, **inactivity})

@app.route("/verify/reactivate", methods=["POST"])
def verify_reactivate():
    from verification import reactivate_user
    body = request.json or {}
    return jsonify(reactivate_user(body.get("user_id","")))

@app.route("/verify/flag_money", methods=["POST"])
def verify_flag():
    from verification import flag_for_money_asking
    body = request.json or {}
    return jsonify(flag_for_money_asking(body.get("flagged_user_id",""), body.get("flagged_by",""),
        body.get("reason",""), body.get("evidence","")))

@app.route("/verify/pay_fine", methods=["POST"])
def verify_pay_fine():
    from verification import pay_fine
    body = request.json or {}
    return jsonify(pay_fine(body.get("user_id",""), body.get("amount",0), body.get("tx_hash","")))

@app.route("/verify/fine_status/<user_id>")
def verify_fine_status(user_id):
    from verification import get_fine_status
    return jsonify(get_fine_status(user_id))

@app.route("/")
def serve_ui():
    return send_file(os.path.join("ui", "index.html"))

@app.route("/<path:path>")
def serve_static(path):
    return send_from_directory("ui", path)

if __name__ == "__main__":
    port = int(os.environ.get("WAKKII_PORT", "8085"))
    host = os.environ.get("WAKKII_HOST", "0.0.0.0")
    print(f"Aceline Server starting on {host}:{port}")
    print(f"UI: http://localhost:{port}")
    print(f"Health: http://localhost:{port}/health")
    app.run(host=host, port=port, debug=False)
