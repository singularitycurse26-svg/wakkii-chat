"""
Aceline Blind Date — Voice-based blind dating for worldwide users

Features:
- Opt in to blind date section
- Get matched with another blind date user
- Voice-only interaction (no video, no profile info shown)
- After conversation: keep talking or move on
- Save contact as "Blind Date" (up to 5 slots)
- Anonymous until both choose to reveal
- Worldwide matching
"""
import hashlib
import json
import os
import sqlite3
import time
from pathlib import Path

DB_PATH = Path.home() / ".wakkii-chat" / "blinddate.db"
MAX_BLIND_DATE_SLOTS = 5

def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(str(DB_PATH)) as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS blind_date_users (
                user_id TEXT PRIMARY KEY,
                username TEXT,
                display_name TEXT,
                gender TEXT,
                age_range TEXT,
                city TEXT,
                country TEXT,
                opted_in INTEGER DEFAULT 0,
                currently_matching INTEGER DEFAULT 0,
                current_match_id TEXT,
                created_at REAL NOT NULL,
                last_active REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS blind_matches (
                id TEXT PRIMARY KEY,
                user_a TEXT NOT NULL,
                user_b TEXT NOT NULL,
                room_id TEXT NOT NULL,
                status TEXT DEFAULT 'active',
                started_at REAL NOT NULL,
                ended_at INTEGER DEFAULT 0,
                user_a_choice TEXT,
                user_b_choice TEXT,
                both_revealed INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS blind_contacts (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                blind_date_id TEXT NOT NULL,
                slot_number INTEGER NOT NULL,
                display_name TEXT DEFAULT 'Blind Date',
                room_id TEXT,
                created_at REAL NOT NULL,
                UNIQUE(user_id, slot_number)
            );
            CREATE INDEX IF NOT EXISTS idx_bd_opted ON blind_date_users(opted_in);
            CREATE INDEX IF NOT EXISTS idx_bd_match ON blind_date_users(currently_matching);
        """)

# --- Opt In/Out ---

def opt_in(user_id, username, display_name, gender=None, age_range=None, city=None, country=None):
    with sqlite3.connect(str(DB_PATH)) as conn:
        conn.execute(
            """INSERT OR REPLACE INTO blind_date_users
            (user_id, username, display_name, gender, age_range, city, country,
             opted_in, currently_matching, current_match_id, created_at, last_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1, 0, NULL, ?, ?)""",
            (user_id, username, display_name, gender, age_range, city, country, time.time(), time.time())
        )
    return {"status": "ok", "opted_in": True}

def opt_out(user_id):
    with sqlite3.connect(str(DB_PATH)) as conn:
        conn.execute(
            "UPDATE blind_date_users SET opted_in = 0, currently_matching = 0, current_match_id = NULL, last_active = ? WHERE user_id = ?",
            (time.time(), user_id)
        )
    return {"status": "ok", "opted_in": False}

def is_opted_in(user_id):
    with sqlite3.connect(str(DB_PATH)) as conn:
        row = conn.execute("SELECT opted_in FROM blind_date_users WHERE user_id = ?", (user_id,)).fetchone()
    return bool(row[0]) if row else False

# --- Matching ---

def find_match(user_id):
    """Find another opted-in user who is not currently matching."""
    with sqlite3.connect(str(DB_PATH)) as conn:
        # Update last active
        conn.execute("UPDATE blind_date_users SET last_active = ? WHERE user_id = ?", (time.time(), user_id))

        # Find available match (not self, opted in, not currently matching)
        row = conn.execute(
            """SELECT user_id, username, display_name FROM blind_date_users
            WHERE opted_in = 1 AND currently_matching = 0 AND user_id != ?
            ORDER BY RANDOM() LIMIT 1""",
            (user_id,)
        ).fetchone()

        if not row:
            return {"status": "no_match", "message": "No blind date users available right now. Try again soon!"}

        partner_id = row[0]

        # Generate room ID
        chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
        hash_hex = hashlib.sha256(f"{user_id}:{partner_id}:{time.time()}".encode()).hexdigest()
        room_id = ''.join(chars[int(hash_hex[i], 16) % len(chars)] for i in range(6))

        match_id = hashlib.sha256(f"{user_id}:{partner_id}:{time.time()}".encode()).hexdigest()[:16]

        # Create match
        conn.execute(
            """INSERT INTO blind_matches (id, user_a, user_b, room_id, status, started_at)
            VALUES (?, ?, ?, ?, 'active', ?)""",
            (match_id, user_id, partner_id, room_id, time.time())
        )

        # Mark both as matching
        conn.execute(
            "UPDATE blind_date_users SET currently_matching = 1, current_match_id = ? WHERE user_id IN (?, ?)",
            (match_id, user_id, partner_id)
        )

    return {
        "status": "matched", "match_id": match_id, "room_id": room_id,
        "partner": {"user_id": partner_id, "username": row[1], "display_name": row[2]}
    }

def end_match(match_id, user_id, choice):
    """End a blind date conversation.
    choice: 'keep_talking', 'move_on', 'reveal'
    """
    with sqlite3.connect(str(DB_PATH)) as conn:
        row = conn.execute(
            "SELECT user_a, user_b, status FROM blind_matches WHERE id = ?",
            (match_id,)
        ).fetchone()
        if not row:
            return {"status": "error", "detail": "Match not found"}
        if row[2] != 'active':
            return {"status": "error", "detail": "Match already ended"}

        user_a, user_b = row[0], row[1]
        partner_id = user_b if user_id == user_a else user_a

        # Record choice
        if user_id == user_a:
            conn.execute("UPDATE blind_matches SET user_a_choice = ? WHERE id = ?", (choice, match_id))
        else:
            conn.execute("UPDATE blind_matches SET user_b_choice = ? WHERE id = ?", (choice, match_id))

        # Check if both made a choice
        match_row = conn.execute(
            "SELECT user_a_choice, user_b_choice FROM blind_matches WHERE id = ?",
            (match_id,)
        ).fetchone()
        a_choice = match_row[0]
        b_choice = match_row[1]

        if a_choice and b_choice:
            # Both chose - end match
            conn.execute(
                "UPDATE blind_matches SET status = 'ended', ended_at = ? WHERE id = ?",
                (time.time(), match_id)
            )
            conn.execute(
                "UPDATE blind_date_users SET currently_matching = 0, current_match_id = NULL WHERE user_id IN (?, ?)",
                (user_a, user_b)
            )

            # If both want to keep talking, save as blind date contact
            if a_choice == 'keep_talking' and b_choice == 'keep_talking':
                save_blind_contact(conn, user_a, match_id)
                save_blind_contact(conn, user_b, match_id)
                return {
                    "status": "ended", "both_keep": True,
                    "message": "You both want to keep talking! Contact saved as Blind Date."
                }
            elif a_choice == 'reveal' or b_choice == 'reveal':
                conn.execute("UPDATE blind_matches SET both_revealed = 1 WHERE id = ?", (match_id,))
                return {
                    "status": "ended", "revealed": True,
                    "message": "Identities revealed! You can now see each other's profiles."
                }
            else:
                return {
                    "status": "ended", "both_keep": False,
                    "message": "Moving on. Good luck out there!"
                }
        else:
            return {
                "status": "waiting", "your_choice": choice,
                "message": "Waiting for the other person to choose..."
            }

def save_blind_contact(conn, user_id, match_id):
    """Save a blind date contact (up to 5 slots)."""
    # Find next available slot
    existing = conn.execute(
        "SELECT slot_number FROM blind_contacts WHERE user_id = ? ORDER BY slot_number",
        (user_id,)
    ).fetchall()
    used_slots = set(r[0] for r in existing)

    slot = None
    for i in range(1, MAX_BLIND_DATE_SLOTS + 1):
        if i not in used_slots:
            slot = i
            break

    if slot is None:
        return  # All slots full

    contact_id = hashlib.sha256(f"{user_id}:{match_id}:{time.time()}".encode()).hexdigest()[:16]
    conn.execute(
        "INSERT OR REPLACE INTO blind_contacts (id, user_id, blind_date_id, slot_number, display_name, created_at) VALUES (?, ?, ?, ?, 'Blind Date', ?)",
        (contact_id, user_id, match_id, slot, time.time())
    )

def get_blind_contacts(user_id):
    with sqlite3.connect(str(DB_PATH)) as conn:
        rows = conn.execute(
            "SELECT id, slot_number, display_name, created_at FROM blind_contacts WHERE user_id = ? ORDER BY slot_number",
            (user_id,)
        ).fetchall()
    return [{
        "id": r[0], "slot": r[1], "display_name": r[2],
        "created_at": r[3], "is_blind": True
    } for r in rows]

def delete_blind_contact(user_id, contact_id):
    with sqlite3.connect(str(DB_PATH)) as conn:
        conn.execute("DELETE FROM blind_contacts WHERE id = ? AND user_id = ?", (contact_id, user_id))
    return {"status": "ok"}

def get_active_match(user_id):
    with sqlite3.connect(str(DB_PATH)) as conn:
        row = conn.execute(
            "SELECT current_match_id FROM blind_date_users WHERE user_id = ? AND currently_matching = 1",
            (user_id,)
        ).fetchone()
        if not row:
            return {"status": "no_active_match"}
        match_id = row[0]
        match = conn.execute(
            "SELECT id, room_id, user_a, user_b, status FROM blind_matches WHERE id = ?",
            (match_id,)
        ).fetchone()
        if not match:
            return {"status": "no_active_match"}
        partner_id = match[2] if user_id == match[3] else match[3]
        partner = conn.execute(
            "SELECT username, display_name FROM blind_date_users WHERE user_id = ?",
            (partner_id,)
        ).fetchone()
        return {
            "status": "active", "match_id": match[0], "room_id": match[1],
            "partner_id": partner_id,
            "partner_name": partner[1] if partner else "Blind Date"
        }

def get_blind_date_stats():
    with sqlite3.connect(str(DB_PATH)) as conn:
        total = conn.execute("SELECT COUNT(*) FROM blind_date_users WHERE opted_in = 1").fetchone()[0]
        active = conn.execute("SELECT COUNT(*) FROM blind_date_users WHERE currently_matching = 1").fetchone()[0]
        matches = conn.execute("SELECT COUNT(*) FROM blind_matches").fetchone()[0]
    return {"opted_in_users": total, "active_matches": active, "total_matches": matches}

init_db()
