# scs_log_parser.py
import re
import pandas as pd
from datetime import datetime
from fault_translator import translate_fault_code

TS_PATTERN = re.compile(r"^([A-Z][a-z]{2}\s+[A-Z][a-z]{2}\s+\d{2}\s+\d{2}:\d{2}:\d{2}\.\d+)")
OPSTATE_CHANGE = re.compile(r"SetOpState (\w+)")
FAULTSTATE_CHANGE = re.compile(r"SetFaultState (\d+)")
HVPS_STATE = re.compile(r"HVPS state changed to (\w+)")
SEASONING_STATE = re.compile(r"Seasoning State changed to (\w+)")

def parse_line(line):
    # ... (Analyse-Logik unverändert)
    if m := OPSTATE_CHANGE.search(line):
        state = m.group(1)
        explanation = {"OP_INIT": "Initialisierung", "OP_STANDBY": "Standby (Bereit)", "OP_SEASONING": "Kalibrierung/Seasoning läuft", "OP_VERIFY": "Überprüfung läuft", "OP_RUN": "Normalbetrieb (RUN)", "OP_FAULT": "FEHLERZUSTAND", "OP_POWERDOWN": "System fährt herunter"}.get(state, state)
        return f"[SCS] Betriebs-Status wechselt zu: {explanation}"
    if m := FAULTSTATE_CHANGE.search(line):
        code = m.group(1); explanation = translate_fault_code(code)
        return f"[SCS] Fehler-Status gesetzt auf: {explanation} (Code: {code})"
    if m := HVPS_STATE.search(line):
        state = m.group(1); return f"[SCS] Röntgenquelle (HVPS) Status: {state}"
    if m := SEASONING_STATE.search(line):
        state = m.group(1); return f"[SCS] Kalibrierung/Seasoning Prozess-Status: {state}"
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
                    records.append({"Timestamp": dt_object, "Quelle": "SCS", "Ereignis": klartext, "OriginalLog": line.strip()})
    return pd.DataFrame(records)