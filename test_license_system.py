# test_license_system.py
from license_generator import generate_key
from license_manager import validate_key

# --- TESTFALL 1: GÜLTIGER SCHLÜSSEL ---
print("--- Testfall 1: Erzeuge gültigen Schlüssel für 'TestUser' (7 Tage) ---")
user1 = "TestUser"
key1 = generate_key(user1, 7)
print(f"Generierter Schlüssel: {key1}")
is_valid, message = validate_key(user1, key1)
print(f"Validierungsergebnis: {is_valid}, Nachricht: {message}")
assert is_valid is True
print("--> ERFOLG\n")

# --- TESTFALL 2: ABGELAUFENER SCHLÜSSEL ---
print("--- Testfall 2: Erzeuge abgelaufenen Schlüssel für 'ExpiredUser' (-1 Tag) ---")
user2 = "ExpiredUser"
key2 = generate_key(user2, -1)
print(f"Generierter Schlüssel: {key2}")
is_valid, message = validate_key(user2, key2)
print(f"Validierungsergebnis: {is_valid}, Nachricht: {message}")
assert is_valid is False
print("--> ERFOLG\n")

# --- TESTFALL 3: FALSCHER BENUTZERNAME ---
print("--- Testfall 3: Prüfe Schlüssel mit falschem Benutzernamen ---")
user3 = "CorrectUser"
key3 = generate_key(user3, 30)
print(f"Generierter Schlüssel für '{user3}': {key3}")
is_valid, message = validate_key("WrongUser", key3)
print(f"Validierungsergebnis: {is_valid}, Nachricht: {message}")
assert is_valid is False
print("--> ERFOLG\n")

# --- TESTFALL 4: MASTERKEY ---
print("--- Testfall 4: Erzeuge Masterkey für 'Admin' ---")
user4 = "Admin"
key4 = generate_key(user4, 0) # 0 Tage = Masterkey
print(f"Generierter Masterkey: {key4}")
is_valid, message = validate_key(user4, key4)
print(f"Validierungsergebnis: {is_valid}, Nachricht: {message}")
assert is_valid is True
print("--> ERFOLG\n")