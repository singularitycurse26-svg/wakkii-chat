"""
Aceline Social Media — Posts, Feeds, Likes, Comments, Live Streaming

Features:
- Post text/image/video posts
- Feed (following + global)
- Like/unlike posts
- Comment on posts
- Live stream to YouTube + Facebook (RTMP)
- Wakkii Social on-ramp (connect accounts, cross-post)
- YouTube on-ramp (OAuth + RTMP key)
- Facebook on-ramp (OAuth + live video API)
"""
import hashlib
import json
import os
import sqlite3
import time
from pathlib import Path

DB_PATH = Path.home() / ".wakkii-chat" / "media.db"

def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(str(DB_PATH)) as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS posts (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                username TEXT,
                display_name TEXT,
                text TEXT NOT NULL,
                media_type TEXT,
                media_data TEXT,
                media_url TEXT,
                walkie_room_id TEXT,
                is_live INTEGER DEFAULT 0,
                live_platform TEXT,
                live_url TEXT,
                likes_count INTEGER DEFAULT 0,
                comments_count INTEGER DEFAULT 0,
                shares_count INTEGER DEFAULT 0,
                created_at REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS likes (
                post_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                created_at REAL NOT NULL,
                PRIMARY KEY (post_id, user_id)
            );
            CREATE TABLE IF NOT EXISTS comments (
                id TEXT PRIMARY KEY,
                post_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                username TEXT,
                text TEXT NOT NULL,
                created_at REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS stream_keys (
                user_id TEXT PRIMARY KEY,
                youtube_rtmp_key TEXT,
                youtube_channel_id TEXT,
                facebook_access_token TEXT,
                facebook_page_id TEXT,
                wakkii_handle TEXT,
                created_at REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS live_streams (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                username TEXT,
                title TEXT,
                platform TEXT NOT NULL,
                rtmp_url TEXT,
                stream_key TEXT,
                walkie_room_id TEXT,
                status TEXT DEFAULT 'starting',
                viewers INTEGER DEFAULT 0,
                started_at REAL NOT NULL,
                ended_at INTEGER DEFAULT 0
            );
            CREATE INDEX IF NOT EXISTS idx_posts_user ON posts(user_id);
            CREATE INDEX IF NOT EXISTS idx_posts_created ON posts(created_at);
            CREATE INDEX IF NOT EXISTS idx_comments_post ON comments(post_id);
        """)

# --- Posts ---

def create_post(user_id, username, display_name, text, media_type=None, media_data=None,
                media_url=None, walkie_room_id=None, is_live=False, live_platform=None, live_url=None):
    post_id = hashlib.sha256(f"{user_id}:{time.time()}".encode()).hexdigest()[:16]
    with sqlite3.connect(str(DB_PATH)) as conn:
        conn.execute(
            """INSERT INTO posts (id, user_id, username, display_name, text, media_type,
               media_data, media_url, walkie_room_id, is_live, live_platform, live_url, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (post_id, user_id, username, display_name, text, media_type, media_data, media_url,
             walkie_room_id, 1 if is_live else 0, live_platform, live_url, time.time())
        )
    return {"status": "ok", "post_id": post_id}

def get_feed(user_id=None, limit=50, offset=0, following_only=False):
    query = "SELECT * FROM posts"
    params = []

    if following_only and user_id:
        from social import get_following
        following_ids = [f["user_id"] for f in get_following(user_id)]
        if following_ids:
            placeholders = ",".join("?" * len(following_ids))
            query += f" WHERE user_id IN ({placeholders})"
            params.extend(following_ids)
        else:
            return []

    query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    with sqlite3.connect(str(DB_PATH)) as conn:
        rows = conn.execute(query, params).fetchall()
    return [_post_row_to_dict(r) for r in rows]

def get_user_posts(user_id, limit=50):
    with sqlite3.connect(str(DB_PATH)) as conn:
        rows = conn.execute(
            "SELECT * FROM posts WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
            (user_id, limit)
        ).fetchall()
    return [_post_row_to_dict(r) for r in rows]

def get_post(post_id):
    with sqlite3.connect(str(DB_PATH)) as conn:
        row = conn.execute("SELECT * FROM posts WHERE id = ?", (post_id,)).fetchone()
    return _post_row_to_dict(row) if row else None

def delete_post(post_id, user_id):
    with sqlite3.connect(str(DB_PATH)) as conn:
        row = conn.execute("SELECT user_id FROM posts WHERE id = ?", (post_id,)).fetchone()
        if not row: return {"status": "error", "detail": "Not found"}
        if row[0] != user_id: return {"status": "error", "detail": "Not owner"}
        conn.execute("DELETE FROM posts WHERE id = ?", (post_id,))
        conn.execute("DELETE FROM likes WHERE post_id = ?", (post_id,))
        conn.execute("DELETE FROM comments WHERE post_id = ?", (post_id,))
    return {"status": "ok"}

# --- Likes ---

def like_post(post_id, user_id):
    with sqlite3.connect(str(DB_PATH)) as conn:
        try:
            conn.execute("INSERT OR IGNORE INTO likes (post_id, user_id, created_at) VALUES (?, ?, ?)",
                        (post_id, user_id, time.time()))
            conn.execute("UPDATE posts SET likes_count = (SELECT COUNT(*) FROM likes WHERE post_id = ?) WHERE id = ?",
                        (post_id, post_id))
        except Exception:
            pass
    return {"status": "ok"}

def unlike_post(post_id, user_id):
    with sqlite3.connect(str(DB_PATH)) as conn:
        conn.execute("DELETE FROM likes WHERE post_id = ? AND user_id = ?", (post_id, user_id))
        conn.execute("UPDATE posts SET likes_count = (SELECT COUNT(*) FROM likes WHERE post_id = ?) WHERE id = ?",
                    (post_id, post_id))
    return {"status": "ok"}

def is_liked(post_id, user_id):
    with sqlite3.connect(str(DB_PATH)) as conn:
        row = conn.execute("SELECT 1 FROM likes WHERE post_id = ? AND user_id = ?", (post_id, user_id)).fetchone()
    return row is not None

# --- Comments ---

def add_comment(post_id, user_id, username, text):
    comment_id = hashlib.sha256(f"{post_id}:{user_id}:{time.time()}".encode()).hexdigest()[:16]
    with sqlite3.connect(str(DB_PATH)) as conn:
        conn.execute(
            "INSERT INTO comments (id, post_id, user_id, username, text, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (comment_id, post_id, user_id, username, text, time.time())
        )
        conn.execute("UPDATE posts SET comments_count = (SELECT COUNT(*) FROM comments WHERE post_id = ?) WHERE id = ?",
                    (post_id, post_id))
    return {"status": "ok", "comment_id": comment_id}

def get_comments(post_id, limit=50):
    with sqlite3.connect(str(DB_PATH)) as conn:
        rows = conn.execute(
            "SELECT * FROM comments WHERE post_id = ? ORDER BY created_at ASC LIMIT ?",
            (post_id, limit)
        ).fetchall()
    return [{
        "id": r[0], "post_id": r[1], "user_id": r[2],
        "username": r[3], "text": r[4], "created_at": r[5]
    } for r in rows]

# --- Stream Keys (On-Ramps) ---

def set_youtube_rtmp(user_id, rtmp_key, channel_id=None):
    with sqlite3.connect(str(DB_PATH)) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO stream_keys (user_id, youtube_rtmp_key, youtube_channel_id, created_at) VALUES (?, ?, ?, ?)",
            (user_id, rtmp_key, channel_id, time.time())
        )
    return {"status": "ok"}

def set_facebook_token(user_id, access_token, page_id=None):
    with sqlite3.connect(str(DB_PATH)) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO stream_keys (user_id, facebook_access_token, facebook_page_id, created_at) VALUES (?, ?, ?, ?)",
            (user_id, access_token, page_id, time.time())
        )
    return {"status": "ok"}

def set_wakkii_handle(user_id, handle):
    with sqlite3.connect(str(DB_PATH)) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO stream_keys (user_id, wakkii_handle, created_at) VALUES (?, ?, ?)",
            (user_id, handle, time.time())
        )
    return {"status": "ok"}

def get_stream_keys(user_id):
    with sqlite3.connect(str(DB_PATH)) as conn:
        row = conn.execute("SELECT * FROM stream_keys WHERE user_id = ?", (user_id,)).fetchone()
    if not row: return {"youtube": None, "facebook": None, "wakkii": None}
    return {
        "youtube": {"rtmp_key": row[1], "channel_id": row[2]} if row[1] else None,
        "facebook": {"access_token": row[3], "page_id": row[4]} if row[3] else None,
        "wakkii": {"handle": row[5]} if row[5] else None
    }

# --- Live Streams ---

def start_stream(user_id, username, title, platform, rtmp_url, stream_key, walkie_room_id=None):
    stream_id = hashlib.sha256(f"{user_id}:{platform}:{time.time()}".encode()).hexdigest()[:16]
    with sqlite3.connect(str(DB_PATH)) as conn:
        conn.execute(
            """INSERT INTO live_streams (id, user_id, username, title, platform, rtmp_url, stream_key,
               walkie_room_id, status, started_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'live', ?)""",
            (stream_id, user_id, username, title, platform, rtmp_url, stream_key, walkie_room_id, time.time())
        )
    return {"status": "ok", "stream_id": stream_id, "rtmp_url": rtmp_url, "stream_key": stream_key}

def end_stream(stream_id):
    with sqlite3.connect(str(DB_PATH)) as conn:
        conn.execute("UPDATE live_streams SET status = 'ended', ended_at = ? WHERE id = ?", (time.time(), stream_id))
    return {"status": "ok"}

def get_active_streams(limit=50):
    with sqlite3.connect(str(DB_PATH)) as conn:
        rows = conn.execute(
            "SELECT * FROM live_streams WHERE status = 'live' ORDER BY started_at DESC LIMIT ?",
            (limit,)
        ).fetchall()
    return [{
        "id": r[0], "user_id": r[1], "username": r[2], "title": r[3],
        "platform": r[4], "walkie_room_id": r[7], "viewers": r[9], "started_at": r[10]
    } for r in rows]

def _post_row_to_dict(r):
    if not r: return None
    return {
        "id": r[0], "user_id": r[1], "username": r[2], "display_name": r[3],
        "text": r[4], "media_type": r[5], "media_data": r[6], "media_url": r[7],
        "walkie_room_id": r[8], "is_live": bool(r[9]), "live_platform": r[10],
        "live_url": r[11], "likes_count": r[12], "comments_count": r[13],
        "shares_count": r[14], "created_at": r[15]
    }

init_db()
