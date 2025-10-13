# config_manager.py
import json
import os

def get_default_profiles():
    """
    Gibt die Standard-FTP-Profile zurück, inklusive des neuen, intelligenten
    "Clearscan Smart Scan"-Profils.
    """
    return {
        "Clearscan Smart Scan": {
            "targets": {
                "Scanner": {
                    "host": "172.16.10.101",
                    "port": "22",
                    "user": "sds",
                    "passwd": "tpt031t/t/",
                    "download_rules": [
                        # Spezifische Einzeldateien
                        {"type": "specific_file", "path": "/opt/eds/log/dbm.log"},
                        {"type": "specific_file", "path": "/opt/eds/log/img_svr.log"},
                        {"type": "specific_file", "path": "/opt/eds/log/ipi.log"},
                        {"type": "specific_file", "path": "/opt/eds/log/iqs.log"},
                        {"type": "specific_file", "path": "/opt/eds/log/iqs_stream.log"},
                        {"type": "specific_file", "path": "/opt/eds/log/Conveyor.log"},
                        {"type": "specific_file", "path": "/opt/eds/log/iqtk.log"},
                        {"type": "specific_file", "path": "/opt/eds/log/optinet.log"},
                        {"type": "specific_file", "path": "/opt/eds/log/scanner.log"},
                        {"type": "specific_file", "path": "/opt/eds/log/scanner_bag.log"},
                        # KORRIGIERT: Der Dateiname ist jetzt großgeschrieben
                        {"type": "specific_file", "path": "/opt/eds/log/oms/OMS.log"},

                        # Finde die neueste Datei mit Muster
                        {"type": "latest_with_pattern", "dir": "/opt/eds/log/dpp/", "pattern": "DPP_"},
                        {"type": "latest_with_pattern", "dir": "/opt/eds/log/SCS/", "pattern": "SCS_"},
                        {"type": "latest_with_pattern", "dir": "/opt/eds/log/diag/trace/", "pattern": "diagserv_"},
                        
                        # Lade alle Dateien aus Ordnern
                        {"type": "all_in_dir", "dir": "/opt/eds/log/"}
                    ]
                }
            }
        },
        "Standard MV3D": {
            "targets": {
                "SCC": {"host": "192.168.7.10", "port": "22", "user": "sds", "passwd": "IhrPasswort", "paths": ["/opt/eds/log/scs.log", "/opt/eds/log/bhs.log"]},
                "DPP": {"host": "192.168.7.11", "port": "22", "user": "sds", "passwd": "IhrPasswort", "paths": ["/var/log/mv3d/dpp/"]},
                "IAC": {"host": "192.168.7.2",  "port": "22", "user": "sds", "passwd": "IhrPasswort", "paths": ["/opt/eds/log/scanner_bag.log"]}
            }
        },
        "Standard GateView": {
            "targets": {
                 "Scanner": {"host": "", "port": "22", "user": "admin", "passwd": "IhrScannerPasswort", "paths": ["/remote/path/to/scanner.log"]},
                 "OMS": {"host": "", "port": "22", "user": "admin", "passwd": "IhrOMSPasswort", "paths": ["/remote/path/to/oms.log"]},
                 "BRAVA TRS": {"host": "192.168.15.1", "port": "22", "user": "admin", "passwd": "Diamond1234@", "paths": ["/mnt/data/hmi/qthmi/deploy/rts/LOGS/"]}
            }
        },
    }

def load_config():
    CONFIG_FILE = "app_config.json"
    if not os.path.exists(CONFIG_FILE):
        save_config({"theme": "dark", "ftp_profiles": get_default_profiles()})
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        try: 
            return json.load(f)
        except json.JSONDecodeError:
            return {"theme": "dark", "ftp_profiles": get_default_profiles()}
    return {}

def save_config(config_data):
    CONFIG_FILE = "app_config.json"
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config_data, f, indent=4)

def load_ftp_profiles():
    config = load_config()
    profiles = config.get("ftp_profiles", {})
    defaults = get_default_profiles()
    updated = False
    for name, default_data in defaults.items():
        is_outdated = False
        if name in profiles:
            if "download_rules" in default_data.get("targets", {}).get("Scanner", {}):
                if "download_rules" not in profiles[name].get("targets", {}).get("Scanner", {}):
                    is_outdated = True
        if name not in profiles or is_outdated:
            profiles[name] = default_data
            updated = True
    if updated:
        save_ftp_profiles(profiles)
    return profiles

def save_ftp_profiles(profiles):
    config = load_config()
    config["ftp_profiles"] = profiles
    save_config(config)