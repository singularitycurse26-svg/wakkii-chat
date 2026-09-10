"""
Aceline Community Voice Messages — City-based connection board

Features:
- Leave voice messages for your city (recorded as base64 audio)
- Search messages by city, gender, age range
- Auto city detection via geolocation (browser API) + IP fallback
- Play community messages
- Call through walkie-talki for free from any message
- Men and women can find live connections by city
"""
import hashlib
import json
import os
import sqlite3
import time
from pathlib import Path

DB_PATH = Path.home() / ".wakkii-chat" / "community.db"

def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(str(DB_PATH)) as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS community_messages (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                username TEXT,
                display_name TEXT,
                gender TEXT,
                age_range TEXT,
                city TEXT NOT NULL,
                state TEXT,
                country TEXT,
                lat REAL,
                lon REAL,
                title TEXT,
                description TEXT,
                audio_data TEXT,
                duration REAL DEFAULT 0,
                room_id TEXT,
                views INTEGER DEFAULT 0,
                calls INTEGER DEFAULT 0,
                created_at REAL NOT NULL,
                expires_at REAL
            );
            CREATE TABLE IF NOT EXISTS cities (
                name TEXT NOT NULL,
                state TEXT,
                country TEXT DEFAULT 'US',
                lat REAL,
                lon REAL,
                message_count INTEGER DEFAULT 0,
                PRIMARY KEY (name, state)
            );
            CREATE INDEX IF NOT EXISTS idx_cm_city ON community_messages(city);
            CREATE INDEX IF NOT EXISTS idx_cm_gender ON community_messages(gender);
            CREATE INDEX IF NOT EXISTS idx_cm_created ON community_messages(created_at);
        """)

# --- Community Messages ---

def post_message(user_id, username, display_name, city, gender=None, age_range=None,
                 state=None, country='US', lat=None, lon=None,
                 title='', description='', audio_data=None, duration=0, room_id=None):
    msg_id = hashlib.sha256(f"{user_id}:{city}:{time.time()}".encode()).hexdigest()[:16]
    expires = time.time() + 86400  # 24 hour expiry

    with sqlite3.connect(str(DB_PATH)) as conn:
        conn.execute(
            """INSERT INTO community_messages
            (id, user_id, username, display_name, gender, age_range, city, state, country,
             lat, lon, title, description, audio_data, duration, room_id, created_at, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (msg_id, user_id, username, display_name, gender, age_range, city, state, country,
             lat, lon, title, description, audio_data, duration, room_id, time.time(), expires)
        )
        # Update city message count
        conn.execute(
            "INSERT OR IGNORE INTO cities (name, state, country, lat, lon, message_count) VALUES (?, ?, ?, ?, ?, 0)",
            (city, state, country, lat, lon)
        )
        conn.execute(
            "UPDATE cities SET message_count = message_count + 1, lat = COALESCE(?, lat), lon = COALESCE(?, lon) WHERE name = ? AND state = ?",
            (lat, lon, city, state)
        )
    return {"status": "ok", "message_id": msg_id, "expires_at": expires}

def get_messages(city=None, gender=None, age_range=None, limit=50, offset=0):
    query = "SELECT * FROM community_messages WHERE expires_at > ?"
    params = [time.time()]

    if city:
        query += " AND city = ?"
        params.append(city)
    if gender:
        query += " AND gender = ?"
        params.append(gender)
    if age_range:
        query += " AND age_range = ?"
        params.append(age_range)

    query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    with sqlite3.connect(str(DB_PATH)) as conn:
        rows = conn.execute(query, params).fetchall()
    return [_msg_row_to_dict(r) for r in rows]

def get_message(msg_id):
    with sqlite3.connect(str(DB_PATH)) as conn:
        row = conn.execute("SELECT * FROM community_messages WHERE id = ?", (msg_id,)).fetchone()
        if row:
            conn.execute("UPDATE community_messages SET views = views + 1 WHERE id = ?", (msg_id,))
        return _msg_row_to_dict(row) if row else None

def increment_calls(msg_id):
    with sqlite3.connect(str(DB_PATH)) as conn:
        conn.execute("UPDATE community_messages SET calls = calls + 1 WHERE id = ?", (msg_id,))
    return {"status": "ok"}

def delete_message(msg_id, user_id):
    with sqlite3.connect(str(DB_PATH)) as conn:
        row = conn.execute("SELECT user_id FROM community_messages WHERE id = ?", (msg_id,)).fetchone()
        if not row: return {"status": "error", "detail": "Not found"}
        if row[0] != user_id: return {"status": "error", "detail": "Not owner"}
        conn.execute("DELETE FROM community_messages WHERE id = ?", (msg_id,))
    return {"status": "ok"}

def get_cities(limit=100):
    with sqlite3.connect(str(DB_PATH)) as conn:
        rows = conn.execute(
            "SELECT name, state, country, message_count FROM cities WHERE message_count > 0 ORDER BY message_count DESC LIMIT ?",
            (limit,)
        ).fetchall()
    return [{
        "name": r[0], "state": r[1], "country": r[2], "message_count": r[3]
    } for r in rows]

def get_user_messages(user_id):
    with sqlite3.connect(str(DB_PATH)) as conn:
        rows = conn.execute(
            "SELECT * FROM community_messages WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,)
        ).fetchall()
    return [_msg_row_to_dict(r) for r in rows]

def _msg_row_to_dict(r):
    if not r: return None
    return {
        "id": r[0], "user_id": r[1], "username": r[2], "display_name": r[3],
        "gender": r[4], "age_range": r[5], "city": r[6], "state": r[7], "country": r[8],
        "lat": r[9], "lon": r[10], "title": r[11], "description": r[12],
        "audio_data": r[13], "duration": r[14], "room_id": r[15],
        "views": r[16], "calls": r[17], "created_at": r[18], "expires_at": r[19]
    }

init_db()
