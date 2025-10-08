# license_validator.py

import configparser
from datetime import datetime
import base64

# Ein einfacher "geheimer" Schlüssel zur Verschleierung.
# Dieser muss mit dem in license_generator.py übereinstimmen.
SECRET_KEY = "MySecretKeyForEncoding2025"

def check_license():
    """
    Prüft den Lizenzschlüssel in der config.ini und gibt Status und Ablaufdatum zurück.
    
    Rückgabe:
        (bool, datetime.date oder None):
            - True, falls die Lizenz gültig ist.
            - False, falls die Lizenz ungültig oder nicht vorhanden ist.
            - Das Ablaufdatum der Lizenz als datetime.date-Objekt.
            - None, wenn der Schlüssel ungültig ist oder nicht existiert.
    """
    config = configparser.ConfigParser()
    config.read('config.ini')
    
    license_key = config.get('License', 'Key', fallback=None)
    
    if not license_key:
        return False, None

    try:
        # Dekodieren des Base64-Strings
        decoded_bytes = base64.b64decode(license_key.encode('utf-8'))
        decoded_str = decoded_bytes.decode('utf-8')

        # Trennen des Datums und des Secret Key
        expiration_date_str, key_check = decoded_str.split('|')

        # Überprüfen, ob der Secret Key übereinstimmt, um Manipulation zu erkennen
        if key_check != SECRET_KEY:
            return False, None

        # Überprüfen des Datums
        expiration_date = datetime.strptime(expiration_date_str, '%Y-%m-%d')
        
        # Lizenz ist gültig, wenn das heutige Datum vor oder am Ablaufdatum liegt
        if expiration_date.date() >= datetime.now().date():
            # Rückgabe des Status und des Ablaufdatums
            return True, expiration_date.date()
        else:
            # Lizenz ist abgelaufen
            return False, expiration_date.date()

    except Exception:
        # Fängt alle Fehler ab, falls der Schlüssel ungültig ist
        return False, None