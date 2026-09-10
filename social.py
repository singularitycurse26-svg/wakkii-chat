"""
Aceline Social Backend — Users, Following, Contacts, Messaging, Live Broadcasts

Features:
- User profiles with @username
- Follow/unfollow system
- Auto-contact filing when talking/FaceTime
- Direct messaging (DMs)
- Live broadcasting (Go Live, watch, join)
- Live chat during broadcasts
- Contact list management
"""
import hashlib
import json
import os
import sqlite3
import time
from pathlib import Path

DB_PATH = Path.home() / ".wakkii-chat" / "social.db"

def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(str(DB_PATH)) as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS profiles (
                user_id TEXT PRIMARY KEY,
                username TEXT UNIQUE,
                display_name TEXT,
                bio TEXT,
                avatar TEXT,
                created_at REAL NOT NULL,
                is_live INTEGER DEFAULT 0,
                live_title TEXT,
                live_room_id TEXT
            );
            CREATE TABLE IF NOT EXISTS follows (
                follower_id TEXT NOT NULL,
                following_id TEXT NOT NULL,
                created_at REAL NOT NULL,
                PRIMARY KEY (follower_id, following_id)
            );
            CREATE TABLE IF NOT EXISTS contacts (
                owner_id TEXT NOT NULL,
                contact_id TEXT NOT NULL,
                contact_name TEXT,
                contact_username TEXT,
                notes TEXT,
                added_at REAL NOT NULL,
                source TEXT DEFAULT 'manual',
                PRIMARY KEY (owner_id, contact_id)
            );
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                sender_id TEXT NOT NULL,
                receiver_id TEXT NOT NULL,
                text TEXT NOT NULL,
                created_at REAL NOT NULL,
                read INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS live_broadcasts (
                room_id TEXT PRIMARY KEY,
                host_id TEXT NOT NULL,
                host_name TEXT,
                title TEXT,
                description TEXT,
                listener_count INTEGER DEFAULT 0,
                started_at REAL NOT NULL,
                ended_at INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS live_chat (
                id TEXT PRIMARY KEY,
                room_id TEXT NOT NULL,
                sender_id TEXT NOT NULL,
                sender_name TEXT,
                text TEXT NOT NULL,
                created_at REAL NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_messages_receiver ON messages(receiver_id);
            CREATE INDEX IF NOT EXISTS idx_messages_sender ON messages(sender_id);
            CREATE INDEX IF NOT EXISTS idx_live_chat_room ON live_chat(room_id);
            CREATE INDEX IF NOT EXISTS idx_contacts_owner ON contacts(owner_id);
        """)

# --- Profiles ---

def create_or_update_profile(user_id, username, display_name=None, bio=None, avatar=None):
    username = username.lower().replace("@", "").strip()
    with sqlite3.connect(str(DB_PATH)) as conn:
        existing = conn.execute("SELECT user_id FROM profiles WHERE user_id = ?", (user_id,)).fetchone()
        if existing:
            updates = []
            params = []
            if display_name: updates.append("display_name = ?"); params.append(display_name)
            if bio is not None: updates.append("bio = ?"); params.append(bio)
            if avatar: updates.append("avatar = ?"); params.append(avatar)
            if updates:
                params.append(user_id)
                conn.execute(f"UPDATE profiles SET {', '.join(updates)} WHERE user_id = ?", params)
        else:
            conn.execute(
                "INSERT INTO profiles (user_id, username, display_name, bio, avatar, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (user_id, username, display_name or username, bio or "", avatar or "", time.time())
            )
    return get_profile(user_id)

def get_profile(user_id):
    with sqlite3.connect(str(DB_PATH)) as conn:
        row = conn.execute("SELECT * FROM profiles WHERE user_id = ?", (user_id,)).fetchone()
    if not row: return None
    return _profile_row_to_dict(row)

def get_profile_by_username(username):
    username = username.lower().replace("@", "").strip()
    with sqlite3.connect(str(DB_PATH)) as conn:
        row = conn.execute("SELECT * FROM profiles WHERE username = ?", (username,)).fetchone()
    if not row: return None
    return _profile_row_to_dict(row)

def search_users(query):
    query = query.lower().strip()
    with sqlite3.connect(str(DB_PATH)) as conn:
        rows = conn.execute(
            "SELECT * FROM profiles WHERE username LIKE ? OR display_name LIKE ? LIMIT 20",
            (f"%{query}%", f"%{query}%")
        ).fetchall()
    return [_profile_row_to_dict(r) for r in rows]

def _profile_row_to_dict(row):
    return {
        "user_id": row[0], "username": row[1], "display_name": row[2],
        "bio": row[3], "avatar": row[4], "created_at": row[5],
        "is_live": bool(row[6]), "live_title": row[7], "live_room_id": row[8]
    }

# --- Following ---

def follow_user(follower_id, following_id):
    if follower_id == following_id: return {"status": "error", "detail": "Cannot follow yourself"}
    with sqlite3.connect(str(DB_PATH)) as conn:
        try:
            conn.execute(
                "INSERT OR IGNORE INTO follows (follower_id, following_id, created_at) VALUES (?, ?, ?)",
                (follower_id, following_id, time.time())
            )
        except Exception:
            pass
    return {"status": "ok"}

def unfollow_user(follower_id, following_id):
    with sqlite3.connect(str(DB_PATH)) as conn:
        conn.execute("DELETE FROM follows WHERE follower_id = ? AND following_id = ?", (follower_id, following_id))
    return {"status": "ok"}

def get_following(user_id):
    with sqlite3.connect(str(DB_PATH)) as conn:
        rows = conn.execute(
            "SELECT p.* FROM follows f JOIN profiles p ON f.following_id = p.user_id WHERE f.follower_id = ?",
            (user_id,)
        ).fetchall()
    return [_profile_row_to_dict(r) for r in rows]

def get_followers(user_id):
    with sqlite3.connect(str(DB_PATH)) as conn:
        rows = conn.execute(
            "SELECT p.* FROM follows f JOIN profiles p ON f.follower_id = p.user_id WHERE f.following_id = ?",
            (user_id,)
        ).fetchall()
    return [_profile_row_to_dict(r) for r in rows]

def is_following(follower_id, following_id):
    with sqlite3.connect(str(DB_PATH)) as conn:
        row = conn.execute(
            "SELECT 1 FROM follows WHERE follower_id = ? AND following_id = ?",
            (follower_id, following_id)
        ).fetchone()
    return row is not None

# --- Contacts (auto-filing) ---

def add_contact(owner_id, contact_id, contact_name, contact_username=None, source="manual", notes=""):
    if owner_id == contact_id: return {"status": "ok"}
    with sqlite3.connect(str(DB_PATH)) as conn:
        existing = conn.execute(
            "SELECT owner_id FROM contacts WHERE owner_id = ? AND contact_id = ?",
            (owner_id, contact_id)
        ).fetchone()
        if existing:
            conn.execute(
                "UPDATE contacts SET contact_name = ?, contact_username = ?, notes = ?, source = ? WHERE owner_id = ? AND contact_id = ?",
                (contact_name, contact_username, notes, source, owner_id, contact_id)
            )
        else:
            conn.execute(
                "INSERT INTO contacts (owner_id, contact_id, contact_name, contact_username, notes, added_at, source) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (owner_id, contact_id, contact_name, contact_username, notes, time.time(), source)
            )
    return {"status": "ok"}

def get_contacts(owner_id):
    with sqlite3.connect(str(DB_PATH)) as conn:
        rows = conn.execute("SELECT * FROM contacts WHERE owner_id = ? ORDER BY added_at DESC", (owner_id,)).fetchall()
    return [{
        "contact_id": r[1], "contact_name": r[2], "contact_username": r[3],
        "notes": r[4], "added_at": r[5], "source": r[6]
    } for r in rows]

def auto_add_contact_from_call(owner_id, owner_name, contact_id, contact_name, contact_username, call_type):
    """Auto-add contact when talking/FaceTime."""
    add_contact(owner_id, contact_id, contact_name, contact_username,
                source=call_type, notes=f"Auto-added from {call_type}")
    add_contact(contact_id, owner_name, owner_id, owner_name,
                source=call_type, notes=f"Auto-added from {call_type}")

# --- Messaging ---

def send_message(sender_id, receiver_id, text):
    msg_id = hashlib.sha256(f"{sender_id}:{receiver_id}:{time.time()}".encode()).hexdigest()[:16]
    with sqlite3.connect(str(DB_PATH)) as conn:
        conn.execute(
            "INSERT INTO messages (id, sender_id, receiver_id, text, created_at) VALUES (?, ?, ?, ?, ?)",
            (msg_id, sender_id, receiver_id, text, time.time())
        )
    return {"status": "ok", "message_id": msg_id}

def get_messages(user_id, other_id, limit=50):
    with sqlite3.connect(str(DB_PATH)) as conn:
        rows = conn.execute(
            "SELECT * FROM messages WHERE (sender_id = ? AND receiver_id = ?) OR (sender_id = ? AND receiver_id = ?) ORDER BY created_at DESC LIMIT ?",
            (user_id, other_id, other_id, user_id, limit)
        ).fetchall()
        # Mark as read
        conn.execute(
            "UPDATE messages SET read = 1 WHERE sender_id = ? AND receiver_id = ?",
            (other_id, user_id)
        )
    return [{
        "id": r[0], "sender_id": r[1], "receiver_id": r[2],
        "text": r[3], "created_at": r[4], "read": bool(r[5])
    } for r in reversed(rows)]

def get_conversations(user_id):
    with sqlite3.connect(str(DB_PATH)) as conn:
        rows = conn.execute(
            """SELECT m.sender_id, m.receiver_id, m.text, m.created_at, p.username, p.display_name
               FROM messages m
               JOIN profiles p ON p.user_id = CASE WHEN m.sender_id = ? THEN m.receiver_id ELSE m.sender_id END
               WHERE m.id IN (
                   SELECT MAX(id) FROM messages
                   WHERE sender_id = ? OR receiver_id = ?
                   GROUP BY CASE WHEN sender_id = ? THEN receiver_id ELSE sender_id END
               )
               ORDER BY m.created_at DESC""",
            (user_id, user_id, user_id, user_id)
        ).fetchall()
    return [{
        "other_id": r[0] if r[0] != user_id else r[1],
        "other_username": r[4], "other_name": r[5],
        "last_message": r[2], "last_at": r[3]
    } for r in rows]

def get_unread_count(user_id):
    with sqlite3.connect(str(DB_PATH)) as conn:
        row = conn.execute("SELECT COUNT(*) FROM messages WHERE receiver_id = ? AND read = 0", (user_id,)).fetchone()
    return row[0] if row else 0

# --- Live Broadcasts ---

def go_live(user_id, title, description="", room_id=None):
    if not room_id:
        room_id = hashlib.sha256(f"{user_id}:{time.time()}".encode()).hexdigest()[:6].upper()

    with sqlite3.connect(str(DB_PATH)) as conn:
        # End any existing live
        conn.execute("UPDATE live_broadcasts SET ended_at = ? WHERE host_id = ? AND ended_at = 0", (time.time(), user_id))
        conn.execute(
            "INSERT OR REPLACE INTO live_broadcasts (room_id, host_id, host_name, title, description, started_at) VALUES (?, ?, ?, ?, ?, ?)",
            (room_id, user_id, "", title, description, time.time())
        )
        conn.execute("UPDATE profiles SET is_live = 1, live_title = ?, live_room_id = ? WHERE user_id = ?",
                     (title, room_id, user_id))
    return {"status": "ok", "room_id": room_id}

def end_live(user_id):
    with sqlite3.connect(str(DB_PATH)) as conn:
        conn.execute("UPDATE live_broadcasts SET ended_at = ? WHERE host_id = ? AND ended_at = 0", (time.time(), user_id))
        conn.execute("UPDATE profiles SET is_live = 0, live_title = NULL, live_room_id = NULL WHERE user_id = ?", (user_id,))
    return {"status": "ok"}

def get_live_broadcasts():
    with sqlite3.connect(str(DB_PATH)) as conn:
        rows = conn.execute(
            "SELECT b.*, p.username, p.display_name, p.avatar FROM live_broadcasts b JOIN profiles p ON b.host_id = p.user_id WHERE b.ended_at = 0 ORDER BY b.started_at DESC"
        ).fetchall()
    return [{
        "room_id": r[0], "host_id": r[1], "title": r[3], "description": r[4],
        "listener_count": r[5], "started_at": r[6],
        "host_username": r[8], "host_name": r[9], "host_avatar": r[10]
    } for r in rows]

def update_listener_count(room_id, count):
    with sqlite3.connect(str(DB_PATH)) as conn:
        conn.execute("UPDATE live_broadcasts SET listener_count = ? WHERE room_id = ?", (count, room_id))
    return {"status": "ok"}

# --- Live Chat ---

def send_live_chat(room_id, sender_id, sender_name, text):
    msg_id = hashlib.sha256(f"{room_id}:{sender_id}:{time.time()}".encode()).hexdigest()[:16]
    with sqlite3.connect(str(DB_PATH)) as conn:
        conn.execute(
            "INSERT INTO live_chat (id, room_id, sender_id, sender_name, text, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (msg_id, room_id, sender_id, sender_name, text, time.time())
        )
    return {"status": "ok", "message_id": msg_id}

def get_live_chat(room_id, limit=50):
    with sqlite3.connect(str(DB_PATH)) as conn:
        rows = conn.execute(
            "SELECT * FROM live_chat WHERE room_id = ? ORDER BY created_at DESC LIMIT ?",
            (room_id, limit)
        ).fetchall()
    return [{
        "id": r[0], "sender_id": r[2], "sender_name": r[3],
        "text": r[4], "created_at": r[5]
    } for r in reversed(rows)]

init_db()
