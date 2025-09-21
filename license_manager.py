# license_manager.py
import hashlib
import base64
from datetime import datetime

# Dieser geheime Schlüssel muss exakt derselbe sein wie im license_generator.py
SECRET_KEY = "Ihre_Geheime_Passphrase_Hier_Aendern"

def validate_key(user_name, license_key):
    """
    Prüft, ob ein Lizenzschlüssel gültig ist.
    Gibt (True, "Gültig bis X") oder (False, "Fehlermeldung") zurück.
    """
    try:
        # Dekodiere den Schlüssel
        decoded_data = base64.b64decode(license_key).decode()
        parts = decoded_data.split(':')
        
        if len(parts) != 3:
            return False, "Ungültiges Schlüsselformat."

        key_user, expiration_date_str, signature = parts
        
        # Prüfe, ob der Schlüssel zum eingegebenen Benutzernamen passt
        if key_user != user_name:
            return False, "Schlüssel passt nicht zum Benutzernamen."
            
        # Überprüfe die Signatur, um Manipulationen zu verhindern
        expected_data_string = f"{key_user}:{expiration_date_str}:{SECRET_KEY}"
        expected_signature = hashlib.sha256(expected_data_string.encode()).hexdigest()
        
        if signature != expected_signature:
            return False, "Ungültiger oder manipulierter Schlüssel."

        # Prüfe das Ablaufdatum
        if expiration_date_str == "never":
            return True, "Unbegrenzt gültig (Masterkey)"
            
        expiration_date = datetime.strptime(expiration_date_str, "%Y-%m-%d")
        if datetime.now() > expiration_date:
            return False, f"Lizenz ist am {expiration_date_str} abgelaufen."
            
        return True, f"Gültig bis {expiration_date_str}"

    except Exception:
        return False, "Fehler beim Lesen des Schlüssels. Ungültiges Format."