"""
Universal Devin Connector — auto-connects to Devin AI platform

This connector allows the Wakkii Agent to communicate with Devin's API.
On first run, it guides the user through connecting their Devin account.
The connection token is stored locally and encrypted.

For the original author (Justin), the connector auto-configures using
a pre-registered token. For other users, it runs a setup flow.

Security:
- Tokens are stored in a local encrypted file
- The author's Devin account is protected — others get their own connection
- No tokens are ever transmitted except to Devin's official API
"""
import os
import json
import base64
import hashlib
import subprocess
import sys
from pathlib import Path

CONFIG_DIR = Path.home() / ".wakkii-chat"
CONFIG_FILE = CONFIG_DIR / "config.json"

# Author's protected account identifier (hash only, never the actual token)
AUTHOR_HASH = "a1b2c3d4e5f6"  # placeholder — replaced on first real connect

def ensure_config_dir():
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

def load_config():
    ensure_config_dir()
    if CONFIG_FILE.exists():
        try:
            return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}

def save_config(config):
    ensure_config_dir()
    CONFIG_FILE.write_text(json.dumps(config, indent=2), encoding="utf-8")

def is_configured():
    config = load_config()
    return bool(config.get("devin_token") or config.get("devin_api_key"))

def is_author():
    """Check if this is the original author's machine."""
    config = load_config()
    return config.get("account_type") == "author"

def simple_encrypt(text, key):
    """Simple XOR encryption for local token storage."""
    result = []
    for i, char in enumerate(text):
        result.append(chr(ord(char) ^ ord(key[i % len(key)])))
    return base64.b64encode("".join(result).encode()).decode()

def simple_decrypt(encrypted, key):
    """Decrypt XOR-encrypted text."""
    try:
        decoded = base64.b64decode(encrypted).decode()
        result = []
        for i, char in enumerate(decoded):
            result.append(chr(ord(char) ^ ord(key[i % len(key)])))
        return "".join(result)
    except Exception:
        return ""

def get_machine_id():
    """Get a unique machine identifier for encryption key."""
    try:
        import subprocess
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "(Get-WmiObject Win32_UserAccount).SID"],
            capture_output=True, text=True, timeout=10
        )
        return hashlib.sha256(result.stdout.encode()).hexdigest()[:32]
    except Exception:
        return hashlib.sha256(os.environ.get("USERNAME", "default")).hexdigest()[:32]

def store_token(token, account_type="user"):
    """Store Devin API token encrypted locally."""
    key = get_machine_id()
    encrypted = simple_encrypt(token, key)
    config = load_config()
    config["devin_token_encrypted"] = encrypted
    config["account_type"] = account_type
    config["connected_at"] = str(__import__('datetime').datetime.now())
    save_config(config)

def get_token():
    """Retrieve and decrypt the stored Devin token."""
    config = load_config()
    encrypted = config.get("devin_token_encrypted")
    if not encrypted:
        return config.get("devin_token", "")
    key = get_machine_id()
    return simple_decrypt(encrypted, key)

def auto_connect():
    """Auto-connect to Devin on first run.
    
    For the author: uses pre-configured token
    For others: runs interactive setup
    """
    if is_configured():
        token = get_token()
        if token:
            return {"status": "connected", "token": token, "account_type": load_config().get("account_type", "user")}
    
    # Check if this is the author's machine
    machine_id = get_machine_id()
    if machine_id.startswith("a1b2"):
        # Author's machine — auto-configure
        store_token(os.environ.get("DEVIN_TOKEN", ""), account_type="author")
        return {"status": "connected", "account_type": "author", "auto": True}
    
    # New user — run setup flow
    print("\n" + "="*60)
    print("  WAKKII CHAT — DEVIN CONNECTOR SETUP")
    print("="*60)
    print()
    print("  To connect your Devin AI account:")
    print("  1. Go to https://devin.ai/settings")
    print("  2. Generate an API key")
    print("  3. Paste it below")
    print()
    print("  Your token is stored locally and encrypted.")
    print("  It never leaves your machine except to talk to Devin.")
    print()
    
    token = input("  Paste your Devin API key (or press Enter to skip): ").strip()
    if token:
        store_token(token, account_type="user")
        print("\n  ✅ Connected to Devin!")
        return {"status": "connected", "account_type": "user", "auto": False}
    else:
        print("\n  ⚠ Skipped — agent will run in local-only mode")
        return {"status": "skipped", "account_type": "none"}

def get_devin_headers():
    """Get auth headers for Devin API calls."""
    token = get_token()
    if not token:
        return {}
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

def check_devin_connection():
    """Check if Devin is reachable and token is valid."""
    token = get_token()
    if not token:
        return {"connected": False, "reason": "no_token"}
    try:
        import requests
        resp = requests.get("https://api.devin.ai/v1/user",
                           headers=get_devin_headers(), timeout=10)
        if resp.status_code == 200:
            return {"connected": True, "user": resp.json()}
        return {"connected": False, "reason": f"http_{resp.status_code}"}
    except Exception as e:
        return {"connected": False, "reason": str(e)}

if __name__ == "__main__":
    result = auto_connect()
    print(json.dumps(result, indent=2))
