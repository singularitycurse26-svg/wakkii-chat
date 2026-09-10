"""
Aceline Verification System — State ID, Biometric, Age, Inactivity, Money-Asking Fines

Rules:
1. Before joining any messaging/wakkii links, users must complete State ID verification
2. Verified users see a "Verified" flash + age before community messages
3. Inactive accounts (30 days) get pulled from community/social until they visit again
4. Asking for money = account flagged + put on hold
5. Caught asking for money = pay fine to platform wallet (goes to founder account)
6. After fine payment, account restored to full access
7. Biometric (fingerprint) re-access after verification is done
"""
import hashlib
import json
import os
import sqlite3
import time
from pathlib import Path

DB_PATH = Path.home() / ".wakkii-chat" / "verification.db"
FOUNDER_EMAIL = "hawpetossjustin25@gmail.com"
INACTIVITY_DAYS = 30
INACTIVITY_SECONDS = INACTIVITY_DAYS * 86400
MONEY_ASKING_FINE = 25.0  # INC tokens to founder
VICTIM_FINE = 25.0  # INC tokens to the person who was asked
TOTAL_FINE = MONEY_ASKING_FINE + VICTIM_FINE  # 50 INC total

# Fine system is ON HOLD until INC stablecoin is created and deployed
# Conditions for reactivation:
#   1. INC stablecoin created and deployed on-chain
#   2. INC added to Soulmate OS platform
#   3. Aceline becomes an OS
#   4. All Incentives Inc. company products integrated
#   5. Incentives Inc. AI company corporation international entity formed
FINE_ON_HOLD = True
FINE_HOLD_REASON = "Waiting for INC stablecoin creation and Incentives Inc. corporate entity formation"

def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(str(DB_PATH)) as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS verifications (
                user_id TEXT PRIMARY KEY,
                username TEXT,
                email TEXT,
                state_id_hash TEXT,
                state_id_state TEXT,
                age_verified INTEGER DEFAULT 0,
                age_range TEXT,
                dob TEXT,
                biometric_enabled INTEGER DEFAULT 0,
                biometric_hash TEXT,
                status TEXT DEFAULT 'unverified',
                verified_at REAL,
                last_active REAL NOT NULL,
                suspended INTEGER DEFAULT 0,
                suspended_reason TEXT,
                suspended_at REAL,
                flagged_count INTEGER DEFAULT 0,
                fine_owed REAL DEFAULT 0,
                fine_paid REAL DEFAULT 0,
                created_at REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS money_flags (
                id TEXT PRIMARY KEY,
                flagged_user_id TEXT NOT NULL,
                flagged_by TEXT,
                victim_id TEXT,
                victim_username TEXT,
                reason TEXT,
                evidence TEXT,
                fine_amount REAL DEFAULT 50.0,
                founder_portion REAL DEFAULT 25.0,
                victim_portion REAL DEFAULT 25.0,
                status TEXT DEFAULT 'pending',
                created_at REAL NOT NULL,
                resolved_at REAL
            );
            CREATE TABLE IF NOT EXISTS fine_payments (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                amount REAL NOT NULL,
                founder_portion REAL DEFAULT 0,
                victim_portion REAL DEFAULT 0,
                victim_id TEXT,
                tx_hash TEXT,
                paid_to_founder INTEGER DEFAULT 0,
                paid_to_victim INTEGER DEFAULT 0,
                created_at REAL NOT NULL
            );
        """)

# --- Verification ---

def start_verification(user_id, username, email):
    with sqlite3.connect(str(DB_PATH)) as conn:
        existing = conn.execute("SELECT user_id FROM verifications WHERE user_id = ?", (user_id,)).fetchone()
        if not existing:
            conn.execute(
                "INSERT INTO verifications (user_id, username, email, status, last_active, created_at) VALUES (?, ?, ?, 'pending', ?, ?)",
                (user_id, username, email, time.time(), time.time())
            )
        else:
            conn.execute("UPDATE verifications SET last_active = ?, username = ?, email = ? WHERE user_id = ?",
                        (time.time(), username, email, user_id))
    return {"status": "ok", "verification_status": "pending"}

def submit_state_id(user_id, state_id_number, state, dob, age_range):
    """Submit state ID for verification. Hashes the ID (never stores raw)."""
    state_id_hash = hashlib.sha256(state_id_number.encode()).hexdigest()

    with sqlite3.connect(str(DB_PATH)) as conn:
        row = conn.execute("SELECT user_id FROM verifications WHERE user_id = ?", (user_id,)).fetchone()
        if not row:
            return {"status": "error", "detail": "Start verification first"}

        conn.execute(
            "UPDATE verifications SET state_id_hash = ?, state_id_state = ?, dob = ?, age_range = ?, age_verified = 1, status = 'verified' WHERE user_id = ?",
            (state_id_hash, state, dob, age_range, user_id)
        )
        conn.execute("UPDATE verifications SET verified_at = ? WHERE user_id = ?", (time.time(), user_id))

    return {"status": "ok", "verified": True, "age_range": age_range}

def enable_biometric(user_id, biometric_data):
    """Enable biometric (fingerprint) re-access."""
    biometric_hash = hashlib.sha256(biometric_data.encode()).hexdigest()
    with sqlite3.connect(str(DB_PATH)) as conn:
        conn.execute(
            "UPDATE verifications SET biometric_enabled = 1, biometric_hash = ? WHERE user_id = ?",
            (biometric_hash, user_id)
        )
    return {"status": "ok", "biometric_enabled": True}

def verify_biometric(user_id, biometric_data):
    """Verify biometric for re-access."""
    biometric_hash = hashlib.sha256(biometric_data.encode()).hexdigest()
    with sqlite3.connect(str(DB_PATH)) as conn:
        row = conn.execute(
            "SELECT biometric_hash, status, suspended FROM verifications WHERE user_id = ?",
            (user_id,)
        ).fetchone()
        if not row:
            return {"status": "error", "detail": "Not registered"}
        if row[0] != biometric_hash:
            return {"status": "error", "detail": "Biometric mismatch"}
        if row[2]:
            return {"status": "error", "detail": "Account suspended", "suspended": True, "reason": "Contact support"}
        # Update last active
        conn.execute("UPDATE verifications SET last_active = ? WHERE user_id = ?", (time.time(), user_id))
        return {"status": "ok", "verified": True, "verification_status": row[1]}

def get_verification_status(user_id):
    with sqlite3.connect(str(DB_PATH)) as conn:
        row = conn.execute("SELECT * FROM verifications WHERE user_id = ?", (user_id,)).fetchone()
    if not row:
        return {"status": "unverified", "verified": False, "suspended": False}
    return {
        "status": row[5], "verified": row[5] == "verified",
        "age_verified": bool(row[7]), "age_range": row[8],
        "biometric_enabled": bool(row[10]),
        "suspended": bool(row[13]), "suspended_reason": row[14],
        "flagged_count": row[16], "fine_owed": row[17],
        "last_active": row[12]
    }

def is_verified(user_id):
    status = get_verification_status(user_id)
    return status.get("verified", False) and not status.get("suspended", False)

# --- Inactivity Auto-Suspend ---

def check_inactivity(user_id):
    """Check if user has been inactive. If so, suspend from community/social."""
    with sqlite3.connect(str(DB_PATH)) as conn:
        row = conn.execute("SELECT last_active, suspended FROM verifications WHERE user_id = ?", (user_id,)).fetchone()
        if not row:
            return {"active": True}
        last_active = row[0]
        is_suspended = bool(row[1])
        now = time.time()
        inactive_for = now - last_active
        if inactive_for > INACTIVITY_SECONDS and not is_suspended:
            conn.execute(
                "UPDATE verifications SET suspended = 1, suspended_reason = 'Inactive for 30+ days', suspended_at = ? WHERE user_id = ?",
                (now, user_id)
            )
            return {"active": False, "suspended": True, "reason": "Inactive for 30+ days"}
        return {"active": inactive_for < INACTIVITY_SECONDS, "suspended": is_suspended}

def reactivate_user(user_id):
    """Reactivate user when they visit the platform again."""
    with sqlite3.connect(str(DB_PATH)) as conn:
        row = conn.execute("SELECT suspended, suspended_reason FROM verifications WHERE user_id = ?", (user_id,)).fetchone()
        if not row:
            return {"status": "error", "detail": "Not registered"}
        if row[0] and row[1] == "Inactive for 30+ days":
            conn.execute(
                "UPDATE verifications SET suspended = 0, suspended_reason = NULL, last_active = ? WHERE user_id = ?",
                (time.time(), user_id)
            )
            return {"status": "ok", "reactivated": True}
        conn.execute("UPDATE verifications SET last_active = ? WHERE user_id = ?", (time.time(), user_id))
        return {"status": "ok", "reactivated": False}

# --- Money-Asking Flag + Fine System ---

def flag_for_money_asking(flagged_user_id, flagged_by, reason, evidence="", victim_id=None, victim_username=None):
    """Flag a user for asking for money. Account put on hold.
    Fine: 25 INC to founder + 25 INC to the person they asked = 50 INC total.
    NOTE: Fine collection is ON HOLD until INC stablecoin is deployed.
    Account is still flagged + suspended, but no payment required until hold lifts.
    """
    flag_id = hashlib.sha256(f"{flagged_user_id}:{time.time()}".encode()).hexdigest()[:16]
    total_fine = TOTAL_FINE
    with sqlite3.connect(str(DB_PATH)) as conn:
        conn.execute(
            """INSERT INTO money_flags (id, flagged_user_id, flagged_by, victim_id, victim_username,
               reason, evidence, fine_amount, founder_portion, victim_portion, status, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?)""",
            (flag_id, flagged_user_id, flagged_by, victim_id, victim_username,
             reason, evidence, total_fine, MONEY_ASKING_FINE, VICTIM_FINE, time.time())
        )
        if FINE_ON_HOLD:
            # Account flagged but fine on hold - no payment required yet
            conn.execute(
                "UPDATE verifications SET suspended = 1, suspended_reason = 'Flagged for asking money (fine on hold)', flagged_count = flagged_count + 1, fine_owed = 0 WHERE user_id = ?",
                (flagged_user_id,)
            )
        else:
            conn.execute(
                "UPDATE verifications SET suspended = 1, suspended_reason = 'Flagged for asking money', flagged_count = flagged_count + 1, fine_owed = fine_owed + ? WHERE user_id = ?",
                (total_fine, flagged_user_id)
            )
    return {
        "status": "ok", "flag_id": flag_id,
        "fine_owed": 0 if FINE_ON_HOLD else total_fine,
        "fine_on_hold": FINE_ON_HOLD,
        "hold_reason": FINE_HOLD_REASON if FINE_ON_HOLD else None,
        "founder_portion": MONEY_ASKING_FINE, "victim_portion": VICTIM_FINE,
        "victim_id": victim_id, "victim_username": victim_username
    }

def pay_fine(user_id, amount, tx_hash=""):
    """Pay fine. 25 INC to founder + 25 INC to the person they asked.
    Account restored after full payment."""
    payment_id = hashlib.sha256(f"{user_id}:{time.time()}".encode()).hexdigest()[:16]
    with sqlite3.connect(str(DB_PATH)) as conn:
        row = conn.execute("SELECT fine_owed FROM verifications WHERE user_id = ?", (user_id,)).fetchone()
        if not row:
            return {"status": "error", "detail": "Not registered"}
        fine_owed = row[0]
        if fine_owed <= 0:
            return {"status": "ok", "message": "No fine owed"}
        if amount < fine_owed:
            return {"status": "error", "detail": f"Insufficient payment. Owed: {fine_owed} INC (25 to founder + 25 to victim)"}

        # Get the latest flag to find victim
        flag_row = conn.execute(
            "SELECT victim_id, victim_username FROM money_flags WHERE flagged_user_id = ? AND status = 'pending' ORDER BY created_at DESC LIMIT 1",
            (user_id,)
        ).fetchone()
        victim_id = flag_row[0] if flag_row else None
        victim_username = flag_row[1] if flag_row else None

        conn.execute(
            """INSERT INTO fine_payments (id, user_id, amount, founder_portion, victim_portion, victim_id,
               tx_hash, paid_to_founder, paid_to_victim, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?)""",
            (payment_id, user_id, amount, MONEY_ASKING_FINE, VICTIM_FINE, victim_id, tx_hash, 1 if victim_id else 0, time.time())
        )
        conn.execute(
            "UPDATE verifications SET fine_owed = 0, fine_paid = fine_paid + ?, suspended = 0, suspended_reason = NULL WHERE user_id = ?",
            (amount, user_id)
        )
        conn.execute(
            "UPDATE money_flags SET status = 'resolved', resolved_at = ? WHERE flagged_user_id = ? AND status = 'pending'",
            (time.time(), user_id)
        )
    return {
        "status": "ok", "paid": amount,
        "founder_portion": MONEY_ASKING_FINE, "founder_email": FOUNDER_EMAIL,
        "victim_portion": VICTIM_FINE, "victim_id": victim_id, "victim_username": victim_username,
        "restored": True
    }

def get_fine_status(user_id):
    with sqlite3.connect(str(DB_PATH)) as conn:
        row = conn.execute("SELECT fine_owed, fine_paid, flagged_count, suspended FROM verifications WHERE user_id = ?", (user_id,)).fetchone()
    if not row:
        return {"fine_owed": 0, "fine_paid": 0, "flagged_count": 0, "suspended": False}
    return {
        "fine_owed": row[0], "fine_paid": row[1],
        "flagged_count": row[2], "suspended": bool(row[3]),
        "fine_on_hold": FINE_ON_HOLD,
        "hold_reason": FINE_HOLD_REASON if FINE_ON_HOLD else None
    }

def activate_fine_system():
    """Activate the fine system once INC stablecoin is deployed.
    This should be called after:
    1. INC stablecoin created and deployed on-chain
    2. INC added to Soulmate OS platform
    3. Aceline becomes an OS
    4. All Incentives Inc. products integrated
    5. Incentives Inc. AI company corporation international entity formed
    """
    global FINE_ON_HOLD
    FINE_ON_HOLD = False
    # Apply pending fines to flagged accounts
    with sqlite3.connect(str(DB_PATH)) as conn:
        flagged = conn.execute(
            "SELECT flagged_user_id FROM money_flags WHERE status = 'pending'"
        ).fetchall()
        for row in flagged:
            user_id = row[0]
            conn.execute(
                "UPDATE verifications SET fine_owed = ?, suspended_reason = 'Flagged for asking money - fine due' WHERE user_id = ? AND suspended = 1",
                (TOTAL_FINE, user_id)
            )
    return {"status": "ok", "fine_system": "active", "reactivated_fines": len(flagged)}

def get_fine_system_status():
    return {
        "fine_on_hold": FINE_ON_HOLD,
        "hold_reason": FINE_HOLD_REASON if FINE_ON_HOLD else None,
        "fine_amount": TOTAL_FINE,
        "founder_portion": MONEY_ASKING_FINE,
        "victim_portion": VICTIM_FINE,
        "founder_email": FOUNDER_EMAIL,
        "conditions_for_activation": [
            "INC stablecoin created and deployed on-chain",
            "INC added to Soulmate OS platform",
            "Aceline becomes an OS",
            "All Incentives Inc. company products integrated",
            "Incentives Inc. AI company corporation international entity formed"
        ]
    }

init_db()
