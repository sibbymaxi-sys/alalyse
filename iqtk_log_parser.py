import re; import pandas as pd; from datetime import datetime
TS_PATTERN = re.compile(r"^(\d{14}):")
RESULT_PATTERN = re.compile(r"(Nylon Sphere|Aluminum Sphere):.*(pass|fail)\}")
def parse_line(line):
    results = [f"{m.group(1)}-Test: {m.group(2).upper()}" for m in RESULT_PATTERN.finditer(line)]
    if results: return f"[IQTK] Bildqualitäts-Test: " + ", ".join(results)
    return None
def parse_log(file_path):
    records = []
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            if ts_match := TS_PATTERN.search(line):
                try: dt = datetime.strptime(ts_match.group(1), "%Y%m%d%H%M%S")
                except ValueError: continue
                if klartext := parse_line(line): records.append({"Timestamp": dt, "Quelle": "IQTK", "Ereignis": klartext, "OriginalLog": line.strip()})
    return pd.DataFrame(records)