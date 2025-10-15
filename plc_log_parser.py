# log_parser.py
import re
import pandas as pd
from datetime import datetime
import os
import traceback
from tkinter import messagebox

# Externe Parser importieren
from brava_log_parser import parse_log as parse_external_brava_log

try:
    from error_definitions import TD_CODES, SD_CODES
except ImportError:
    TD_CODES, SD_CODES = {}, {}

# === Regex-Muster ===
TS_PATTERN_GENERIC = re.compile(r"^(\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2})")
TS_PATTERN_LEGACY = re.compile(r"^([A-Z][a-z]{2}\s+[A-Z][a-z]{2}\s+\d{2}\s+\d{2}:\d{2}:\d{2})")
BAG_ID_PATTERN = re.compile(r'\"(0\d{9})\"')
IATA_RFID_PATTERN = re.compile(r"(?:IATA:|with IATA|L=)\s*(?:\"|')?([\w\d\-]+)(?:\"|')?|\bRFID:\s*(\d{3,4})\b", re.IGNORECASE)
DEVICE_ID_PATTERN = re.compile(r'@(CCT\d{4})')

# Breva PLC Muster
BREVA_TRAY_RFID = re.compile(r"Tray with RFID: ([\w\d\-]+)")
BREVA_DIVERTER_REJECT = re.compile(r"Diverter reject: .* IS NOT DIVERTED")
BREVA_RESULT_CLEAR = re.compile(r"Result CLEAR for tray ([\w\d\-]+)")
BREVA_SEND_TO_OSR = re.compile(r"SEND TO OSR ([\w\d\-]+)")
BREVA_STATION_WARNING = re.compile(r"!!!! Warning: Station '([\w\d\-]+)'")

def _parse_line_to_klartext(line, source, bag_id=None, iata=None):
    # Diese Funktion bleibt wie in der letzten vollständigen Version
    pass

def _determine_source(filename, line):
    # Diese Funktion bleibt unverändert
    pass

def _parse_generic_log(file_path, update_progress):
    # Diese Funktion bleibt unverändert
    pass

def _parse_brava_log(file_path, update_progress):
    # Diese Funktion bleibt unverändert
    pass

def _parse_breva_plclog_csv(file_path, update_progress):
    """
    Ein spezialisierter, intelligenter Parser für die 6-spaltige PlcLog.csv von Breva.
    """
    try:
        records = []; filename = os.path.basename(file_path)
        if update_progress: update_progress(10, f"Lese {filename}...")

        df = pd.read_csv(file_path, comment=';', header=None, on_bad_lines='skip', sep=r',\s*', engine='python')
        df.columns = ["Timestamp", "CmpId", "ClassId", "ErrorId", "InfoId", "InfoText"]
        
        df['Timestamp'] = pd.to_datetime(df['Timestamp'].str.replace('Z', ''), errors='coerce')
        df.dropna(subset=['Timestamp', 'InfoText'], inplace=True)

        severity_map = {1: "INFO", 2: "WARNUNG", 4: "FEHLER", 8: "EXCEPTION"}

        total_lines = len(df)
        for i, row in df.iterrows():
            if update_progress and i % 100 == 0:
                update_progress(10 + int((i / total_lines) * 90), f"Analysiere {filename}...")
            
            info_text = str(row['InfoText'])
            severity = severity_map.get(row['ClassId'], "UNBEKANNT")
            klartext, bag_id_full = "", None

            iata_match = BREVA_TRAY_RFID.search(info_text) or re.search(r"tray ([\w\d\-]+)", info_text, re.IGNORECASE)
            if iata_match: bag_id_full = iata_match.group(1)

            if BREVA_DIVERTER_REJECT.search(info_text): klartext = f"KRITISCHER FEHLER: Weiche hat nicht wie befohlen sortiert!"
            elif m := BREVA_RESULT_CLEAR.search(info_text): klartext = f"Info: Finale Freigabe-Entscheidung für Wanne {m.group(1)}."
            elif m := BREVA_SEND_TO_OSR.search(info_text): klartext = f"Info: Wanne {m.group(1)} wird zur manuellen Kontrolle (OSR) geschickt."
            elif m := BREVA_TRAY_RFID.search(info_text): klartext = f"Position: Wanne {m.group(1)} am RFID-Leser erkannt."
            elif m := BREVA_STATION_WARNING.search(info_text): klartext = f"System-Warnung von Station '{m.group(1)}'."
            else: klartext = info_text
            
            if klartext:
                normalized_id = None
                if bag_id_full:
                    num_part = re.search(r'(\d{3})$', bag_id_full) # KORRIGIERT: Sucht nach den letzten 3 Ziffern
                    if num_part:
                        try: normalized_id = str(int(num_part.group(1))) # Stellt sicher, dass es ein String ist
                        except ValueError: pass
                
                records.append({
                    "Timestamp": row['Timestamp'], "BagID": normalized_id, "IATA": bag_id_full,
                    "Source": f"PLC-{severity}", "Klartext": f"[PLC-{severity}] {klartext}", 
                    "OriginalLog": info_text.strip(), "Operator": None
                })

        if update_progress: update_progress(100, "Abgeschlossen.")
        return pd.DataFrame(records)
    except Exception:
        messagebox.showerror("Parser-Fehler (Breva PlcLog.csv)", f"Fehler in '{os.path.basename(file_path)}'.\n\n{traceback.format_exc()}"); return pd.DataFrame()

# --- ZENTRALE DISPATCHER-FUNKTION ---
def parse_log_file(file_path, progress_callback=None):
    filename_lower = os.path.basename(file_path).lower()
    if filename_lower == "plclog.csv":
        return _parse_breva_plclog_csv(file_path, progress_callback)
    elif "brava" in filename_lower:
        return _parse_brava_log(file_path, progress_callback)
    else:
        return _parse_generic_log(file_path, progress_callback)