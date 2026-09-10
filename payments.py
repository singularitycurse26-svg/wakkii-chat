"""
Aceline Payments Backend — Send, Request, On-Ramp, Off-Ramp

Features:
- Send INC/BNB to other users by @username or wallet address
- Request funds from other users
- On-ramp: buy INC with simulated fiat (local ledger)
- Off-ramp: sell INC for simulated fiat (local ledger)
- Transaction history
- Balance tracking (local ledger — on-chain requires Web3)
"""
import hashlib
import json
import os
import sqlite3
import time
from pathlib import Path

DB_PATH = Path.home() / ".wakkii-chat" / "payments.db"

def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(str(DB_PATH)) as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS transactions (
                id TEXT PRIMARY KEY,
                sender_id TEXT,
                receiver_id TEXT,
                sender_address TEXT,
                receiver_address TEXT,
                amount REAL NOT NULL,
                token TEXT DEFAULT 'INC',
                type TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                memo TEXT,
                created_at REAL NOT NULL,
                completed_at REAL
            );
            CREATE TABLE IF NOT EXISTS fund_requests (
                id TEXT PRIMARY KEY,
                requester_id TEXT NOT NULL,
                requester_address TEXT,
                amount REAL NOT NULL,
                token TEXT DEFAULT 'INC',
                memo TEXT,
                created_at REAL NOT NULL,
                fulfilled INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS onramp_orders (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                user_address TEXT,
                fiat_amount REAL NOT NULL,
                fiat_currency TEXT DEFAULT 'USD',
                crypto_amount REAL NOT NULL,
                crypto_token TEXT DEFAULT 'INC',
                rate REAL NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at REAL NOT NULL,
                completed_at REAL
            );
            CREATE INDEX IF NOT EXISTS idx_tx_sender ON transactions(sender_id);
            CREATE INDEX IF NOT EXISTS idx_tx_receiver ON transactions(receiver_id);
            CREATE INDEX IF NOT EXISTS idx_requests ON fund_requests(requester_id);
        """)

def send_funds(sender_id, sender_address, receiver_id=None, receiver_address=None, amount=0, token="INC", memo=""):
    if amount <= 0: return {"status": "error", "detail": "Amount must be > 0"}
    if not receiver_id and not receiver_address:
        return {"status": "error", "detail": "Need receiver_id or receiver_address"}

    tx_id = hashlib.sha256(f"{sender_id}:{receiver_id or receiver_address}:{time.time()}".encode()).hexdigest()[:16]

    with sqlite3.connect(str(DB_PATH)) as conn:
        conn.execute(
            "INSERT INTO transactions (id, sender_id, receiver_id, sender_address, receiver_address, amount, token, type, status, memo, created_at, completed_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (tx_id, sender_id, receiver_id, sender_address, receiver_address, amount, token, "send", "completed", memo, time.time(), time.time())
        )
    return {"status": "ok", "tx_id": tx_id, "amount": amount, "token": token}

def request_funds(requester_id, requester_address, amount, token="INC", memo=""):
    if amount <= 0: return {"status": "error", "detail": "Amount must be > 0"}
    req_id = hashlib.sha256(f"{requester_id}:{time.time()}".encode()).hexdigest()[:16]
    with sqlite3.connect(str(DB_PATH)) as conn:
        conn.execute(
            "INSERT INTO fund_requests (id, requester_id, requester_address, amount, token, memo, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (req_id, requester_id, requester_address, amount, token, memo, time.time())
        )
    return {"status": "ok", "request_id": req_id, "amount": amount, "token": token}

def get_fund_requests(user_id):
    with sqlite3.connect(str(DB_PATH)) as conn:
        rows = conn.execute(
            "SELECT * FROM fund_requests WHERE requester_id = ? AND fulfilled = 0 ORDER BY created_at DESC",
            (user_id,)
        ).fetchall()
    return [{
        "id": r[0], "amount": r[3], "token": r[4], "memo": r[5], "created_at": r[6]
    } for r in rows]

def onramp(user_id, user_address, fiat_amount, fiat_currency="USD"):
    """Buy INC with fiat (simulated)."""
    if fiat_amount <= 0: return {"status": "error", "detail": "Amount must be > 0"}
    # Simulated rate: 1 INC = $0.001
    rate = 0.001
    crypto_amount = fiat_amount / rate
    order_id = hashlib.sha256(f"{user_id}:{time.time()}".encode()).hexdigest()[:16]
    with sqlite3.connect(str(DB_PATH)) as conn:
        conn.execute(
            "INSERT INTO onramp_orders (id, user_id, user_address, fiat_amount, fiat_currency, crypto_amount, crypto_token, rate, status, created_at, completed_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (order_id, user_id, user_address, fiat_amount, fiat_currency, crypto_amount, "INC", rate, "completed", time.time(), time.time())
        )
    return {"status": "ok", "order_id": order_id, "crypto_amount": crypto_amount, "rate": rate}

def offramp(user_id, user_address, crypto_amount, crypto_token="INC"):
    """Sell INC for fiat (simulated)."""
    if crypto_amount <= 0: return {"status": "error", "detail": "Amount must be > 0"}
    rate = 0.001
    fiat_amount = crypto_amount * rate
    order_id = hashlib.sha256(f"{user_id}:{time.time()}".encode()).hexdigest()[:16]
    with sqlite3.connect(str(DB_PATH)) as conn:
        conn.execute(
            "INSERT INTO onramp_orders (id, user_id, user_address, fiat_amount, fiat_currency, crypto_amount, crypto_token, rate, status, created_at, completed_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (order_id, user_id, user_address, fiat_amount, "USD", crypto_amount, crypto_token, rate, "completed", time.time(), time.time())
        )
    return {"status": "ok", "order_id": order_id, "fiat_amount": fiat_amount, "rate": rate}

def get_transaction_history(user_id, limit=50):
    with sqlite3.connect(str(DB_PATH)) as conn:
        rows = conn.execute(
            "SELECT * FROM transactions WHERE sender_id = ? OR receiver_id = ? ORDER BY created_at DESC LIMIT ?",
            (user_id, user_id, limit)
        ).fetchall()
    return [{
        "id": r[0], "sender_id": r[1], "receiver_id": r[2],
        "sender_address": r[3], "receiver_address": r[4],
        "amount": r[5], "token": r[6], "type": r[7], "status": r[8],
        "memo": r[9], "created_at": r[10], "completed_at": r[11]
    } for r in rows]

init_db()
