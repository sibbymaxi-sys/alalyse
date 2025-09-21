import re; import pandas as pd; from datetime import datetime
TS_PATTERN = re.compile(r"^([A-Z][a-z]{2}\s+[A-Z][a-z]{2}\s+\d{2}\s+\d{2}:\d{2}:\d{2}\.\d+)")
FSM_STATE_CHANGE = re.compile(r"FSM:next\((\w+)\)")
FSM_INPUT = re.compile(r"FSM:input=\w+\(([^)]+)\)")
def parse_line(line):
    if m := FSM_STATE_CHANGE.search(line): return f"[FSM] System-Zustand wechselt zu: '{m.group(1)}'."
    if m := FSM_INPUT.search(line): return f"[FSM] System-Input empfangen: {m.group(1)}"
    return None
def parse_log(file_path):
    records = []
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            if ts_match := TS_PATTERN.search(line):
                try: dt = datetime.strptime(ts_match.group(1), "%a %b %d %H:%M:%S.%f")
                except ValueError: continue
                if klartext := parse_line(line): records.append({"Timestamp": dt, "Quelle": "FSM", "Ereignis": klartext, "OriginalLog": line.strip()})
    return pd.DataFrame(records)