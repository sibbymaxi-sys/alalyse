# config_manager.py
import json
import os

CONFIG_FILE = "analyzer_config.json" # Umbenannt für allgemeine Einstellungen

def load_profiles():
    """ Lädt die gesamte Konfiguration aus der JSON-Datei. """
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}

def save_profiles(data):
    """ Speichert die gesamte Konfiguration in der JSON-Datei. """
    with open(CONFIG_FILE, 'w') as f:
        json.dump(data, f, indent=4)