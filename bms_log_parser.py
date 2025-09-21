import re; import pandas as pd; from datetime import datetime
from fault_translator import translate_fault_code # NEU
TS_PATTERN = re.compile(r"^([A-Z][a-z]{2}\s+[A-Z][a-z]{2}\s+\d{2}\s+\d{2}:\d{2}:\d{2}\.\d+)")
BAG_DESTROY_PATTERN = re.compile(r'Destroying bag (\d+)')
FAULT_CAUSE_PATTERN = re.compile(r'UpdateScannerStatus - scs_fault_cause = (\d+)')
SCS_STATUS_PATTERN = re.compile(r'UpdateScannerStatus - got SCS Opstate = (\d+)')
def parse_line(line):
    if m := FAULT_CAUSE_PATTERN.search(line): return f"[BMS] FEHLERURSACHE gemeldet: {m.group(1)} - '{translate_fault_code(m.group(1))}'"
    if m := BAG_DESTROY_PATTERN.search(line): return f"[BMS] Bag '{m.group(1)}' wird aus Speicher entfernt."
    if m := SCS_STATUS_PATTERN.search(line): return f"[BMS] Status-Update vom Scanner (SCS) erhalten: Code {m.group(1)}."
    return None
def parse_log(file_path):
    records = []
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            if ts_match := TS_PATTERN.search(line):
                try: dt = datetime.strptime(ts_match.group(1), "%a %b %d %H:%M:%S.%f")
                except ValueError: continue
                if klartext := parse_line(line): records.append({"Timestamp": dt, "Quelle": "BMS", "Ereignis": klartext, "OriginalLog": line.strip()})
    return pd.DataFrame(records)