# dpp_log_parser.py
import re
import pandas as pd
from datetime import datetime

TS_PATTERN = re.compile(r"^([A-Z][a-z]{2}\s+[A-Z][a-z]{2}\s+\d{2}\s+\d{2}:\d{2}:\d{2}\.\d+)")
EXITING_PATTERN = re.compile(r"Client::read\(\) -- exiting\((\d+)\)")

def parse_line(line):
    # ... (Analyse-Logik unverändert)
    if m := EXITING_PATTERN.search(line):
        exit_code = m.group(1)
        if exit_code == '3': return "[DPP] FEHLER: Client-Verbindung wurde unerwartet beendet (Exit-Code: 3). Ursache: Netzwerkfehler oder Timeout."
        else: return f"[DPP] Client-Verbindung beendet (Code: {exit_code})."
    return None

def parse_log(file_path):
    records = []
    last_month = None
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            if ts_match := TS_PATTERN.search(line):
                try:
                    # **KORRIGIERTE DATUMS-LOGIK**
                    ts_str_no_year = ts_match.group(1).split('.')[0]
                    dt_no_year = datetime.strptime(ts_str_no_year, "%a %b %d %H:%M:%S")
                    
                    year_to_use = 2025
                    if last_month and dt_no_year.month < last_month:
                        year_to_use += 1

                    dt_object = dt_no_year.replace(year=year_to_use)
                    last_month = dt_object.month
                except ValueError: continue

                if klartext := parse_line(line):
                    records.append({"Timestamp": dt_object, "Quelle": "DPP", "Ereignis": klartext, "OriginalLog": line.strip()})
    return pd.DataFrame(records)