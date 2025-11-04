# config_manager.py
import json
import os

CONFIG_FILE = "app_config.json"

def get_default_profiles():
    """Gibt die Standard-FTP-Profile mit allen bekannten Servern und Log-Pfaden zurück."""
    return {
        "Standard MV3D": {
            "targets": {
                "SCC": {"host": "192.168.7.10", "port": "22", "user": "sds", "passwd": "IhrPasswort", "paths": ["/opt/eds/log/scs.log", "/opt/eds/log/bhs.log"]},
                "DPP": {"host": "192.168.7.11", "port": "22", "user": "sds", "passwd": "IhrPasswort", "paths": ["/var/log/mv3d/dpp/current"]},
                "IAC": {"host": "192.168.7.2",  "port": "22", "user": "sds", "passwd": "IhrPasswort", "paths": ["/opt/eds/log/scanner_bag.log"]}
            }
        },
        "Standard GateView": {
            "targets": {
                 "Scanner": {
                     "host": "", # Hier Ihre Scanner-IP eintragen
                     "port": "22",
                     "user": "admin",
                     "passwd": "IhrScannerPasswort",
                     "paths": ["/remote/path/to/scanner.log"]
                 },
                 "OMS": {
                     "host": "", # Hier Ihre OMS-IP eintragen
                     "port": "22",
                     "user": "admin",
                     "passwd": "IhrOMSPasswort",
                     "paths": ["/remote/path/to/oms.log"]
                 },
                 "BRAVA TRS": {
                     "host": "192.168.15.1",
                     "port": "22",
                     "user": "admin",
                     "passwd": "Diamond1234@",
                     "paths": ["/mnt/data/hmi/qthmi/deploy/rts/LOGS/"]
                 }
            }
        },
        "System Analyzer Default": {
            "targets": {
                "Server 1": {
                    "host": "192.168.1.100", # Beispiel-IP
                    "port": "22",
                    "user": "admin",
                    "passwd": "password",
                    "paths": ["/pfad/zu/den/logs/"]
                }
            }
        }
    }

def load_config():
    """Lädt die Konfigurationsdatei. Erstellt sie, wenn sie nicht existiert."""
    if not os.path.exists(CONFIG_FILE):
        save_config({"theme": "dark", "ftp_profiles": get_default_profiles()})
        
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}
    return {}

def save_config(config_data):
    """Speichert die Konfigurationsdatei."""
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config_data, f, indent=4)

def load_ftp_profiles():
    """Lädt die FTP-Profile und stellt sicher, dass die Standardprofile vorhanden sind."""
    config = load_config()
    profiles = config.get("ftp_profiles", {})
    
    defaults = get_default_profiles()
    updated = False
    for name, data in defaults.items():
        if name not in profiles:
            profiles[name] = data
            updated = True
    
    if updated:
        save_ftp_profiles(profiles)
        
    return profiles

def save_ftp_profiles(profiles):
    """Speichert die FTP-Profile in der Konfiguration."""
    config = load_config()
    config["ftp_profiles"] = profiles
    save_config(config)