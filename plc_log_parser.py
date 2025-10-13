# plc_log_parser.py
import re
import pandas as pd
import os

# Versuche, die Definitionen zu importieren. Wenn es nicht klappt, setze leere Dictionaries.
try:
    from error_definitions import TD_CODES, SD_CODES
except ImportError:
    TD_CODES, SD_CODES = {}, {}

# === Regex-Muster für die Ereignisse in der 'Message'-Spalte ===
IATA_PATTERN = re.compile(r'\b(\w{4,})\b') # Allgemeineres Muster, um IDs zu fangen

TRACKING_DECISION_PATTERN = re.compile(r"Tracking Decision, Bag \w+, TD (\d+)", re.IGNORECASE)
SORTING_DECISION_PATTERN = re.compile(r"Sorting Decision, Bag \w+, SD (\d+)", re.IGNORECASE)
PHOTOCELL_PATTERN = re.compile(r"(IBDR|XBDP) PS:")
RTR_BIT_PATTERN = re.compile(r"Ready To Receive Bit To BHS (High|Low)")
DIVERTER_PATTERN = re.compile(r"Diverter (\w+) activated", re.IGNORECASE)
WAITING_PATTERN = re.compile(r"stopped at switch (\w+)", re.IGNORECASE)
# Muster für allgemeine Prozess-Events
PROCESSING_START_PATTERN = re.compile(r"Start processing Product file", re.IGNORECASE)
PROCESSING_STOP_PATTERN = re.compile(r"Finished processing Product file", re.IGNORECASE)
CLEARSCAN_START_PATTERN = re.compile(r"Start ClearScan", re.IGNORECASE)
CLEARSCAN_STOP_PATTERN = re.compile(r"Stop ClearScan", re.IGNORECASE)


def parse_line(line):
    """Analysiert eine einzelne Log-Zeile, sucht nach IATA und dem spezifischen Ereignis."""
    iata_match = IATA_PATTERN.search(line)
    bag_id_full = iata_match.group(1) if iata_match else None

    # Tracking Decision (TD)
    if td_match := TRACKING_DECISION_PATTERN.search(line):
        code = td_match.group(1)
        explanation = TD_CODES.get(code, f"Unbekannter Code")
        return bag_id_full, f"[PLC] Tracking: {explanation} (TD-{code})"

    # Sorting Decision (SD)
    if sd_match := SORTING_DECISION_PATTERN.search(line):
        code = sd_match.group(1)
        explanation = SD_CODES.get(code, f"Unbekannter Code")
        return bag_id_full, f"[PLC] Sortierung: {explanation} (SD-{code})"

    # Lichtschranke
    if PHOTOCELL_PATTERN.search(line):
        sensor_name = "Einlauf-Lichtschranke (IBDR)" if "IBDR" in line else "Auslauf-Lichtschranke (XBDP)"
        return bag_id_full, f"[PLC] Position: Wanne hat '{sensor_name}' passiert."
    
    # Weiche (Diverter)
    if d_match := DIVERTER_PATTERN.search(line):
        diverter_id = d_match.group(1)
        return bag_id_full, f"[PLC] Aktion: Weiche '{diverter_id}' wurde aktiviert."

    # Warten an einer Weiche
    if w_match := WAITING_PATTERN.search(line):
        switch_id = w_match.group(1)
        return bag_id_full, f"[PLC] Zustand: Wanne wartet an Weiche '{switch_id}'."

    # Ready-To-Receive Signal (ohne BagID)
    if RTR_BIT_PATTERN.search(line):
        state = "High" if "High" in line else "Low"
        return None, f"[PLC] Systemsignal 'Ready To Receive' ist '{state}'."
        
    # Allgemeine Prozess-Events (ohne BagID)
    if PROCESSING_START_PATTERN.search(line): return None, "[Prozess] Start der Verarbeitung"
    if PROCESSING_STOP_PATTERN.search(line): return None, "[Prozess] Ende der Verarbeitung"
    if CLEARSCAN_START_PATTERN.search(line): return None, "[Prozess] ClearScan gestartet"
    if CLEARSCAN_STOP_PATTERN.search(line): return None, "[Prozess] ClearScan beendet"

    return None, None

def parse_log(file_path, progress_callback):
    """Liest eine PlcLog.csv, normalisiert die BagID und übersetzt Fehlercodes."""
    filename = os.path.basename(file_path)
    records = []
    
    try:
        progress_callback(10, f"Lese {filename}...")
        # KORREKTUR: Liest die CSV-Datei und konvertiert die 'Time'-Spalte direkt
        df = pd.read_csv(file_path, on_bad_lines='skip')
        df['Time'] = pd.to_datetime(df['Time'], errors='coerce')
        df.dropna(subset=['Time', 'Message'], inplace=True)

        total_lines = len(df)
        for i, row in df.iterrows():
            if i % 100 == 0:
                progress_callback(int((i/total_lines)*100), f"Analysiere {filename}...")

            dt_object = row['Time']
            line = row['Message']

            bag_id_full, klartext = parse_line(line)
            if klartext:
                bag_id_normalized = bag_id_full[-4:] if bag_id_full else None
                records.append({
                    "Timestamp": dt_object, 
                    "BagID": bag_id_normalized,
                    "IATA_volĺständig": bag_id_full,
                    "Source": "PLC", 
                    "Klartext": klartext, 
                    "OriginalLog": line.strip()
                })
    except Exception:
        return pd.DataFrame()

    return pd.DataFrame(records)