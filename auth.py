"""
Wakkii Chat Authentication System

Built exactly like Soulmate OS:
- Founder account: hawpetossjustin25@gmail.com — free forever, all features unlocked
- Other users: sign up with email + password
- Session tokens with expiry (permanent for founder)
- Local founder check for offline mode
- SQLite for user storage
"""
import hashlib
import json
import os
import sqlite3
import time
from pathlib import Path

FOUNDER_EMAIL = "hawpetossjustin25@gmail.com"
FOUNDER_PASSWORD_HASH = "add3e2d64e2a04bfe4cc9606612d20a74706737fbbff433e0e262cc59735cc96"

DB_PATH = Path.home() / ".wakkii-chat" / "auth.db"

def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(str(DB_PATH)) as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                email TEXT UNIQUE,
                created_at REAL NOT NULL,
                is_founder INTEGER DEFAULT 0,
                metadata TEXT
            );
            CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                created_at REAL NOT NULL,
                expires_at REAL NOT NULL,
                is_permanent INTEGER DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            );
            CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);
        """)

def sha256(text):
    return hashlib.sha256(text.encode()).hexdigest()

def create_session(user_id, permanent=False):
    token = hashlib.sha256(f"{user_id}:{time.time()}:{os.urandom(16).hex()}".encode()).hexdigest()
    created = time.time()
    expires = created + (86400 * 365 if permanent else 86400 * 7)  # 1 year permanent, 7 days normal
    with sqlite3.connect(str(DB_PATH)) as conn:
        conn.execute(
            "INSERT INTO sessions (token, user_id, created_at, expires_at, is_permanent) VALUES (?, ?, ?, ?, ?)",
            (token, user_id, created, expires, 1 if permanent else 0)
        )
    return token

def ensure_user(user_id, email, is_founder=False):
    with sqlite3.connect(str(DB_PATH)) as conn:
        existing = conn.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,)).fetchone()
        if existing:
            if is_founder:
                conn.execute("UPDATE users SET is_founder = 1 WHERE user_id = ?", (user_id,))
            return
        conn.execute(
            "INSERT INTO users (user_id, email, created_at, is_founder, metadata) VALUES (?, ?, ?, ?, ?)",
            (user_id, email, time.time(), 1 if is_founder else 0, "{}")
        )

def signup(email, password):
    email = email.lower().strip()
    if not "@" in email:
        return {"status": "error", "detail": "Invalid email"}
    if len(password) < 8:
        return {"status": "error", "detail": "Password must be 8+ characters"}

    password_hash = sha256(password)
    with sqlite3.connect(str(DB_PATH)) as conn:
        existing = conn.execute("SELECT user_id FROM users WHERE email = ?", (email,)).fetchone()
        if existing:
            return {"status": "error", "detail": "Email already registered"}

        user_id = hashlib.sha256(f"{email}:{time.time()}".encode()).hexdigest()[:16]
        conn.execute(
            "INSERT INTO users (user_id, email, created_at, is_founder, metadata) VALUES (?, ?, ?, 0, ?)",
            (user_id, email, time.time(), json.dumps({"password_hash": password_hash}))
        )
    token = create_session(user_id, permanent=False)
    return {"status": "created", "session_token": token, "user_id": user_id, "is_founder": False}

def login(email, password):
    email = email.lower().strip()
    password_hash = sha256(password)

    # Founder check
    if email == FOUNDER_EMAIL and password_hash == FOUNDER_PASSWORD_HASH:
        user_id = "founder"
        ensure_user(user_id, email, is_founder=True)
        token = create_session(user_id, permanent=True)
        return {
            "status": "ok",
            "session_token": token,
            "user_id": user_id,
            "is_founder": True,
            "message": "Welcome back, Founder. Full access granted — free forever."
        }

    # Normal user check
    with sqlite3.connect(str(DB_PATH)) as conn:
        row = conn.execute(
            "SELECT user_id, is_founder, metadata FROM users WHERE email = ?",
            (email,)
        ).fetchone()

    if row is None:
        return {"status": "error", "detail": "Invalid email or password"}

    user_id, is_founder, metadata_str = row
    try:
        metadata = json.loads(metadata_str or "{}")
    except Exception:
        metadata = {}
    stored_hash = metadata.get("password_hash", "")

    if stored_hash != password_hash:
        return {"status": "error", "detail": "Invalid email or password"}

    token = create_session(user_id, permanent=bool(is_founder))
    return {
        "status": "ok",
        "session_token": token,
        "user_id": user_id,
        "is_founder": bool(is_founder)
    }

def verify_token(token):
    if not token:
        return None
    with sqlite3.connect(str(DB_PATH)) as conn:
        row = conn.execute(
            "SELECT s.user_id, s.expires_at, s.is_permanent, u.email, u.is_founder "
            "FROM sessions s JOIN users u ON s.user_id = u.user_id "
            "WHERE s.token = ?",
            (token,)
        ).fetchone()
    if row is None:
        return None
    user_id, expires_at, is_permanent, email, is_founder = row
    if not is_permanent and time.time() > expires_at:
        return None
    return {
        "user_id": user_id,
        "email": email,
        "is_founder": bool(is_founder),
        "is_permanent": bool(is_permanent)
    }

def check_session(token):
    info = verify_token(token)
    if info is None:
        return {"status": "invalid"}
    return {"status": "valid", "email": info["email"], "user_id": info["user_id"], "is_founder": info["is_founder"]}

def local_founder_check(email, password):
    """Offline founder check — used when server is not available."""
    if email.lower().strip() != FOUNDER_EMAIL:
        return False
    return sha256(password) == FOUNDER_PASSWORD_HASH

def get_user_info(token):
    info = verify_token(token)
    if info is None:
        return {"status": "error", "detail": "Invalid token"}
    return {
        "status": "ok",
        "email": info["email"],
        "user_id": info["user_id"],
        "is_founder": info["is_founder"],
        "free_forever": info["is_founder"]
    }

init_db()
