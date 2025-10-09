import re
import pandas as pd
from datetime import datetime

TRAY_PATTERN = re.compile(r'(Tray with RFID:|Tray ID:|Result (CLEAR|REJECT|ERROR) for tray :|RFID READER \d data ready - ID )\s*([A-Z0-9]+)')
TS_PATTERN = re.compile(r'^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})Z')
SEVERITY_MAP = {1: "INFO", 2: "WARNING", 4: "ERROR", 8: "EXCEPTION", 16: "DEBUG"}

def extract_severity(classid):
    try:
        return SEVERITY_MAP.get(int(classid), "OTHER")
    except Exception:
        return "OTHER"

def parse_line(line):
    m = TRAY_PATTERN.search(line)
    if m:
        tray_id = m.group(3)
        info = line.strip()
        return tray_id, info
    return None, None

def parse_log(file_path):
    records = []
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            # Filter Kommentare und leere Zeilen raus
            if line.startswith(";") or not line.strip():
                continue
            # Extrahiere Zeitstempel, ClassId
            parts = line.strip().split(",", 5)
            if len(parts) < 6:
                continue
            timestamp_raw, cmpid, classid, errorid, infoid, infotext = parts
            tray_id, info = parse_line(infotext)
            if tray_id:
                ts = None
                try:
                    ts = datetime.strptime(timestamp_raw[:19], "%Y-%m-%dT%H:%M:%S")
                except Exception:
                    pass
                severity = extract_severity(classid)
                records.append({
                    "Timestamp": ts,
                    "TrayID": tray_id,
                    "Quelle": "BRAVA",
                    "Ereignis": info,
                    "OriginalLog": line.strip(),
                    "Severity": severity
                })
    return pd.DataFrame(records)