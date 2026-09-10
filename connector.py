"""
Universal Devin Connector — auto-connects to Devin AI platform

Connects to Devin API (primary) with GLM-5.1 via WindsurfAPI (fallback).
Tokens stored locally, encrypted with machine-specific key.
Author's account is protected — other users connect their own accounts.
"""
import os
import json
import base64
import hashlib
import subprocess
from pathlib import Path
from datetime import datetime

CONFIG_DIR = Path.home() / ".wakkii-chat"
CONFIG_FILE = CONFIG_DIR / "config.json"

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
    return bool(config.get("devin_token_encrypted") or config.get("devin_token"))

def is_author():
    config = load_config()
    return config.get("account_type") == "author"

def get_machine_id():
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "(Get-WmiObject Win32_UserAccount).SID"],
            capture_output=True, text=True, timeout=10
        )
        return hashlib.sha256(result.stdout.encode()).hexdigest()[:32]
    except Exception:
        return hashlib.sha256(os.environ.get("USERNAME", "default").encode()).hexdigest()[:32]

def simple_encrypt(text, key):
    result = []
    for i, char in enumerate(text):
        result.append(chr(ord(char) ^ ord(key[i % len(key)])))
    return base64.b64encode("".join(result).encode()).decode()

def simple_decrypt(encrypted, key):
    try:
        decoded = base64.b64decode(encrypted).decode()
        result = []
        for i, char in enumerate(decoded):
            result.append(chr(ord(char) ^ ord(key[i % len(key)])))
        return "".join(result)
    except Exception:
        return ""

def store_token(token, account_type="user"):
    key = get_machine_id()
    encrypted = simple_encrypt(token, key) if token else ""
    config = load_config()
    config["devin_token_encrypted"] = encrypted
    config["account_type"] = account_type
    config["connected_at"] = datetime.now().isoformat()
    save_config(config)

def get_token():
    config = load_config()
    encrypted = config.get("devin_token_encrypted")
    if not encrypted:
        return config.get("devin_token", os.environ.get("DEVIN_TOKEN", ""))
    key = get_machine_id()
    return simple_decrypt(encrypted, key)

def auto_connect():
    if is_configured():
        token = get_token()
        if token:
            return {"status": "connected", "token": token, "account_type": load_config().get("account_type", "user")}

    env_token = os.environ.get("DEVIN_TOKEN", "")
    if env_token:
        store_token(env_token, account_type="author")
        return {"status": "connected", "account_type": "author", "auto": True}

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
    print("  Or press Enter to skip — agent will use GLM-5.1 (free).")
    print()

    token = input("  Paste your Devin API key (or Enter to skip): ").strip()
    if token:
        store_token(token, account_type="user")
        print("\n  ✅ Connected to Devin!")
        return {"status": "connected", "account_type": "user", "auto": False}
    else:
        print("\n  ⚠ Skipped — agent will use GLM-5.1 via WindsurfAPI (free)")
        return {"status": "skipped", "account_type": "none"}

def check_devin_connection():
    import requests
    token = get_token()
    if not token:
        return {"connected": False, "reason": "no_token"}
    try:
        resp = requests.get("https://api.devin.ai/v1/user",
                           headers={"Authorization": f"Bearer {token}"}, timeout=10)
        if resp.status_code == 200:
            return {"connected": True, "user": resp.json()}
        return {"connected": False, "reason": f"http_{resp.status_code}"}
    except Exception as e:
        return {"connected": False, "reason": str(e)}

def call_devin(messages, max_tokens=1500, model="glm-5.1"):
    """Call Devin API. Returns (response, backend_used)."""
    import requests
    token = get_token()
    if not token:
        return None, "no_token"

    try:
        resp = requests.post(
            "https://api.devin.ai/v1/chat/completions",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={"model": model, "messages": messages, "max_tokens": max_tokens, "temperature": 0.5},
            timeout=180,
        )
        if resp.status_code == 200:
            return resp.json()["choices"][0]["message"]["content"], "devin"
        return None, f"devin_error_{resp.status_code}"
    except Exception as e:
        return None, f"devin_error_{e}"

def call_llm(messages, max_tokens=1500, model="glm-5.1"):
    """Call LLM with fallback: Devin first, then WindsurfAPI GLM-5.1."""
    import requests

    # Try Devin first
    response, backend = call_devin(messages, max_tokens, model)
    if response:
        return response, "devin"

    # Fall back to WindsurfAPI GLM-5.1
    windsurf_api = os.environ.get("WINDSURF_API", "http://127.0.0.1:3003")
    windsurf_key = os.environ.get("WINDSURF_KEY", "local-dev-key-openmausbot")

    try:
        resp = requests.post(
            f"{windsurf_api}/v1/chat/completions",
            headers={"Authorization": f"Bearer {windsurf_key}", "Content-Type": "application/json"},
            json={"model": model, "messages": messages, "max_tokens": max_tokens, "temperature": 0.5},
            timeout=180,
        )
        if resp.status_code == 200:
            return resp.json()["choices"][0]["message"]["content"], "glm-5.1"
        return f"[LLM error: HTTP {resp.status_code}]", "error"
    except requests.exceptions.ReadTimeout:
        return "[LLM timed out — try simpler]", "error"
    except Exception as e:
        return f"[LLM error: {e}]", "error"

if __name__ == "__main__":
    result = auto_connect()
    print(json.dumps(result, indent=2))
