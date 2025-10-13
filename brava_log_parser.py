# brava_log_parser.py
import re
import pandas as pd
from datetime import datetime

# === Erweiterte Muster für HMI-Ereignisse ===
# Bestehendes Muster, um die primäre Tray-ID zu finden
TRAY_PATTERN = re.compile(r'(Tray with RFID:|Tray ID:|Result (?:CLEAR|REJECT|ERROR) for tray :|RFID READER \d data ready - ID )\s*([A-Z0-9]+)')

# Neue Muster für spezifische HMI-Aktionen oder -Zustände
HMI_WAITING_PATTERN = re.compile(r"waiting for operator decision", re.IGNORECASE)
HMI_MANUAL_CMD_PATTERN = re.compile(r"Manual reroute command", re.IGNORECASE)
# (Hier können zukünftig weitere Muster hinzugefügt werden)

# Muster für den Zeitstempel
TS_PATTERN = re.compile(r'^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})Z')
SEVERITY_MAP = {1: "INFO", 2: "WARNING", 4: "ERROR", 8: "EXCEPTION", 16: "DEBUG"}

def extract_severity(classid):
    try:
        return SEVERITY_MAP.get(int(classid), "OTHER")
    except Exception:
        return "OTHER"

def parse_brava_line(infotext):
    """
    Analysiert den Informationstext einer BRAVA-Logzeile,
    sucht nach der TrayID und spezifischen HMI-Ereignissen.
    """
    tray_id_match = TRAY_PATTERN.search(infotext)
    tray_id = tray_id_match.group(3) if tray_id_match else None
    
    klartext = infotext.strip() # Standard-Klartext ist die ursprüngliche Nachricht

    # Überschreibe den Klartext mit einer verständlicheren Meldung, wenn ein Muster passt
    if HMI_WAITING_PATTERN.search(infotext):
        id_text = f"für Wanne {tray_id} " if tray_id else ""
        klartext = f"[HMI] System wartet {id_text}auf eine Operator-Entscheidung."
    
    elif HMI_MANUAL_CMD_PATTERN.search(infotext):
        id_text = f"für Wanne {tray_id}" if tray_id else "durch Operator"
        klartext = f"[HMI] Manueller Umleitungsbefehl {id_text} ausgeführt."
        
    return tray_id, klartext

def parse_log(file_path):
    """Liest und verarbeitet eine komplette BRAVA-Logdatei."""
    records = []
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            if line.startswith(";") or not line.strip():
                continue
            
            parts = line.strip().split(",", 5)
            if len(parts) < 6:
                continue
            
            timestamp_raw, _, classid, _, _, infotext = parts
            
            tray_id, klartext = parse_brava_line(infotext)
            
            if tray_id: # Wir zeichnen nur Ereignisse auf, die einer Wanne zugeordnet werden können
                ts = None
                try:
                    ts = datetime.strptime(timestamp_raw[:19], "%Y-%m-%dT%H:%M:%S")
                except Exception:
                    pass # Zeitstempel konnte nicht gelesen werden
                
                severity = extract_severity(classid)
                records.append({
                    "Timestamp": ts,
                    "TrayID": tray_id, # Wird später in BagID umbenannt
                    "Quelle": "BRAVA",
                    "Ereignis": klartext,
                    "OriginalLog": line.strip(),
                    "Severity": severity
                })
                
    return pd.DataFrame(records)