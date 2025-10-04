# analysis_engine.py
import re
from collections import Counter

# ==============================================================================
# 1. WISSENSDATENBANK: Fehlerdefinitionen und bekannte Muster
# Diese Sektion ist das "Handbuch-Wissen" deines Programms.
# ==============================================================================

ERROR_DEFINITIONS = {
    "CHILLER_FAULT": {
        "description": "Fehler im Kühlsystem.",
        "severity": "KRITISCH",
        "action": "Kühlaggregat (Wasserstand/Temperatur) und Schläuche prüfen."
    },
    "YASKAWA_FAULT": {
        "description": "Problem mit der Motorsteuerung des Förderbands.",
        "severity": "HOCH",
        "action": "Yaskawa-Motor und Mechanik auf Blockaden prüfen."
    },
    "BMS_ENTRANCE_BAG_JAM": {
        "description": "Gepäckstück blockiert den Einlass.",
        "severity": "MITTEL",
        "action": "Blockade am Einlass entfernen, Sensoren prüfen."
    },
    "SUBSYSTEMMISSING": {
        "description": "Ein Software-Modul antwortet nicht.",
        "severity": "HOCH",
        "action": "Betroffenes Subsystem neustarten. Ggf. gesamtes System rebooten."
    },
    "REBOOT": {
        "description": "System-Neustart wurde ausgelöst.",
        "severity": "INFO",
        "action": "Prüfen, welcher Fehler den Neustart verursacht hat."
    },
    "ESTOP": {
        "description": "NOT-AUS wurde betätigt.",
        "severity": "KRITISCH",
        "action": "Grund für Not-Aus klären und Quittierung am Bedienpult."
    }
}

KNOWN_PATTERNS = [
    {
        "name": "Kritische Überhitzung",
        "sequence": ["CHILLER_FAULT", "ESTOP"],
        "explanation": "Das Kühlsystem ist ausgefallen, was zu einem Not-Stopp führte."
    },
    {
        "name": "Blockade durch Motorfehler",
        "sequence": ["YASKAWA_FAULT", "BMS_ENTRANCE_BAG_JAM"],
        "explanation": "Ein Motorfehler führte wahrscheinlich zu einer Gepäck-Blockade."
    },
    {
        "name": "Verlorenes Subsystem",
        "sequence": ["SUBSYSTEMMISSING", "REBOOT"],
        "explanation": "Ein Subsystem war nicht erreichbar und hat einen System-Neustart erzwungen."
    }
]

# ==============================================================================
# 2. ALGORITHMEN: Die Werkzeuge für die Analyse
# ==============================================================================

def _extract_error_code(raw_error_string):
    """Extrahiert den Fehler-Code aus einer rohen Log-Zeile."""
    # Beispiel-Annahme: "Zeile 12345: [Timestamp] ERROR: YASKAWA_FAULT - Details..."
    # Wir suchen nach einem der bekannten Fehlercodes im Text.
    for code in ERROR_DEFINITIONS:
        if code in raw_error_string:
            return code
    return None

def find_known_sequences(error_codes):
    """Findet bekannte, vordefinierte Sequenzen in der Fehlerliste."""
    found_patterns = []
    text_of_errors = " ".join(error_codes) # Effizienter als eine Schleife
    for pattern in KNOWN_PATTERNS:
        # Wir suchen die Sequenz als einfachen String im Gesamttext
        sequence_as_string = " ".join(pattern["sequence"])
        if sequence_as_string in text_of_errors:
            found_patterns.append(pattern)
    return found_patterns

# ==============================================================================
# 3. HAUPTFUNKTION: Das öffentliche Interface des Moduls
# ==============================================================================

def analyze_log_data(raw_error_list):
    """
    Die zentrale Analyse-Funktion. Schnell, effizient und wiederverwendbar.
    Nimmt eine Liste roher Fehler-Strings entgegen und gibt einen strukturierten Report zurück.
    """
    # Schritt 1: Strukturierung (Daten für schnelle Analyse aufbereiten)
    # Wir extrahieren nur die reinen Fehlercodes.
    structured_errors = [_extract_error_code(raw_error) for raw_error in raw_error_list]
    # Wir filtern 'None'-Werte raus, falls eine Zeile keinen bekannten Code enthielt.
    structured_errors = [code for code in structured_errors if code]
    
    if not structured_errors:
        return {"summary": "Keine bekannten Fehlercodes in den Logs gefunden.", "details": {}}

    # Schritt 2: Single-Pass-Analyse (Alles in einem Durchgang)
    error_counts = Counter(structured_errors)
    
    # Schritt 3: Sequenz-Analyse
    found_sequences = find_known_sequences(structured_errors)

    # Schritt 4: Report erstellen
    # Wir bereiten die Daten für die Ausgabe vor.
    top_5_errors = error_counts.most_common(5)
    
    report = {
        "summary": {
            "total_errors": len(structured_errors),
            "unique_errors": len(error_counts),
        },
        "top_errors": [
            {
                "code": code,
                "count": count,
                "definition": ERROR_DEFINITIONS.get(code, {})
            } for code, count in top_5_errors
        ],
        "found_patterns": found_sequences,
        "raw_results": structured_errors # für eventuelle tiefere Analysen
    }
    
    return report