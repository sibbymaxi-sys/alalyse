# license_validator.py
import base64
from datetime import datetime
import os

# NEU: Definiere den sicheren Speicherort
APP_NAME = "MV3D_GateView_Analyzer"
CONFIG_DIR = os.path.join(os.getenv('APPDATA'), APP_NAME)
LICENSE_FILE = os.path.join(CONFIG_DIR, "license.key")

SECRET_KEY = "MySecretKeyForEncoding2025"

def decode_key(license_key):
    # ... (Diese Funktion bleibt gleich) ...
    try:
        decoded_bytes = base64.b64decode(license_key); decoded_str = decoded_bytes.decode('utf-8')
        if f"|{SECRET_KEY}" in decoded_str: return decoded_str.split('|')[0]
    except Exception: return None
    return None

def check_license():
    if not os.path.exists(LICENSE_FILE):
        return {"valid": False, "reason": "NO_FILE", "expires": None}
    with open(LICENSE_FILE, 'r') as f:
        license_key = f.read().strip()
    expiration_date_str = decode_key(license_key)
    if not expiration_date_str:
        return {"valid": False, "reason": "INVALID_KEY", "expires": None}
    if expiration_date_str == "9999-12-31":
        return {"valid": True, "reason": "VALID", "expires": "Unbegrenzt"}
    try:
        expiration_date = datetime.strptime(expiration_date_str, '%Y-%m-%d')
        if datetime.now() > expiration_date:
            return {"valid": False, "reason": "EXPIRED", "expires": expiration_date_str}
        else:
            return {"valid": True, "reason": "VALID", "expires": expiration_date_str}
    except ValueError:
        return {"valid": False, "reason": "INVALID_DATE", "expires": None}

def write_license_key(key):
    try:
        # Stelle sicher, dass das Verzeichnis existiert
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(LICENSE_FILE, 'w') as f:
            f.write(key)
        return True
    except Exception:
        return False