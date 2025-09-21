import re; import pandas as pd; from datetime import datetime
TS_PATTERN = re.compile(r"^([A-Z][a-z]{2}\s+[A-Z][a-z]{2}\s+\d{2}\s+\d{2}:\d{2}:\d{2}\.\d+)")
RTR_BIT_PATTERN = re.compile(r"Ready To Receive Bit To BHS (High|Low)")
IBDR_PATTERN = re.compile(r"IBDR PS: \d+ BT: (\d+)")
def parse_line(line):
    if m := RTR_BIT_PATTERN.search(line): return f"[PLC] Meldesignal 'Ready To Receive' an BHS ist jetzt '{m.group(1)}'."
    if m := IBDR_PATTERN.search(line): return f"[PLC] Wanne '{m.group(1)}' hat Lichtschranken passiert."
    return None
def parse_log(file_path):
    records = []
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            if ts_match := TS_PATTERN.search(line):
                try: dt = datetime.strptime(ts_match.group(1), "%a %b %d %H:%M:%S.%f")
                except ValueError: continue
                if klartext := parse_line(line): records.append({"Timestamp": dt, "Quelle": "PLC", "Ereignis": klartext, "OriginalLog": line.strip()})
    return pd.DataFrame(records)