# license_validator.py
import base64
from datetime import datetime
import os

# Muss exakt derselbe sein wie im license_generator.py
SECRET_KEY = "MySecretKeyForEncoding2025"
LICENSE_FILE = "license.key"

def decode_key(license_key):
    """Entschlüsselt einen Lizenzschlüssel und gibt das Ablaufdatum zurück."""
    try:
        decoded_bytes = base64.b64decode(license_key)
        decoded_str = decoded_bytes.decode('utf-8')
        
        # Prüfe, ob der Secret Key übereinstimmt
        if f"|{SECRET_KEY}" in decoded_str:
            expiration_date_str = decoded_str.split('|')[0]
            return expiration_date_str
    except Exception:
        return None
    return None

def check_license():
    """
    Prüft die Lizenzdatei und gibt den Status zurück.
    Rückgabe: Ein Dictionary mit 'valid' (True/False) und weiteren Infos.
    """
    if not os.path.exists(LICENSE_FILE):
        return {"valid": False, "reason": "NO_FILE", "expires": None}

    with open(LICENSE_FILE, 'r') as f:
        license_key = f.read().strip()

    expiration_date_str = decode_key(license_key)
    
    if not expiration_date_str:
        return {"valid": False, "reason": "INVALID_KEY", "expires": None}

    # Spezieller Fall für die unbegrenzte Vollversion
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
    """Schreibt einen neuen Schlüssel in die Lizenzdatei."""
    try:
        with open(LICENSE_FILE, 'w') as f:
            f.write(key)
        return True
    except Exception:
        return False