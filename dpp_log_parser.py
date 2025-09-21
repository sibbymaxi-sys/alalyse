import re; import pandas as pd; from datetime import datetime
TS_PATTERN = re.compile(r"^([A-Z][a-z]{2}\s+[A-Z][a-z]{2}\s+\d{2}\s+\d{2}:\d{2}:\d{2}\.\d+)")
EXITING_PATTERN = re.compile(r"Client::read\(\) -- exiting\((\d+)\)")
def parse_line(line):
    if m := EXITING_PATTERN.search(line): return f"[DPP] Client-Verbindung beendet (Code: {m.group(1)})."
    return None
def parse_log(file_path):
    records = []
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            if ts_match := TS_PATTERN.search(line):
                try: dt = datetime.strptime(ts_match.group(1), "%a %b %d %H:%M:%S.%f")
                except ValueError: continue
                if klartext := parse_line(line): records.append({"Timestamp": dt, "Quelle": "DPP", "Ereignis": klartext, "OriginalLog": line.strip()})
    return pd.DataFrame(records)