# license_generator.py
import hashlib
import base64
from datetime import datetime, timedelta

# Dieser geheime Schlüssel muss exakt derselbe sein wie im license_manager.py
SECRET_KEY = "Ihre_Geheime_Passphrase_Hier_Aendern"
VALIDITY_DAYS = 180 # Feste Gültigkeit von 6 Monaten

def generate_key(user_name):
    """Erzeugt einen Lizenzschlüssel für einen Benutzer."""
    if user_name.upper() == "MASTERKEY":
        expiration_date_str = "never"
    else:
        expiration_date = datetime.now() + timedelta(days=VALIDITY_DAYS)
        expiration_date_str = expiration_date.strftime("%Y-%m-%d")

    # Erstelle den Daten-String
    data_string = f"{user_name}:{expiration_date_str}:{SECRET_KEY}"
    
    # Erstelle einen sicheren Hash (Signatur)
    signature = hashlib.sha256(data_string.encode()).hexdigest()
    
    # Kombiniere die Originaldaten mit der Signatur
    license_data = f"{user_name}:{expiration_date_str}:{signature}"
    
    # Kodiere das Ganze, um es unleserlicher zu machen
    license_key = base64.b64encode(license_data.encode()).decode()
    
    return license_key, expiration_date_str

if __name__ == "__main__":
    print("--- Lizenz-Generator (6-Monats-Lizenzen) ---")
    user = input("Benutzername eingeben (oder 'MASTERKEY' für Masterkey): ")
    
    key, exp_date = generate_key(user)
    
    print("\n-------------------------")
    print(f"Benutzer: {user}")
    if user.upper() == "MASTERKEY":
        print("Gültigkeit: Unbegrenzt (Masterkey)")
    else:
        print(f"Gültigkeit: {VALIDITY_DAYS} Tage (bis {exp_date})")
    print(f"\nLizenzschlüssel:\n{key}")
    print("-------------------------")