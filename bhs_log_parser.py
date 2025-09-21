import re; import pandas as pd; from datetime import datetime
TS_PATTERN = re.compile(r"^(\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2},\d{3})")
BHS_STATE_PATTERN = re.compile(r"BHS in state '(\w+)'"); ELEMENT_CMD_PATTERN = re.compile(r"Command successful for element '([\w-]+)'"); ERROR_PATTERN = re.compile(r"ERROR: Element '([\w-]+)' failed to respond")
def parse_line(line):
    if m := BHS_STATE_PATTERN.search(line): return f"[BHS] Anlagen-Status: '{m.group(1)}'"
    if m := ELEMENT_CMD_PATTERN.search(line): return f"[BHS] Befehl für Anlagenteil '{m.group(1)}' erfolgreich."
    if m := ERROR_PATTERN.search(line): return f"[BHS] FEHLER: Anlagenteil '{m.group(1)}' antwortet nicht."
    return None
def parse_log(file_path):
    records = []
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            if ts_match := TS_PATTERN.search(line):
                try: dt = datetime.strptime(ts_match.group(1), "%Y-%m-%d %H:%M:%S,%f")
                except ValueError: continue
                if klartext := parse_line(line): records.append({"Timestamp": dt, "Quelle": "BHS", "Ereignis": klartext, "OriginalLog": line.strip()})
    return pd.DataFrame(records)