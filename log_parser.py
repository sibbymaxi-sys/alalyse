# log_parser.py
print("--- [V23-FIX-OMS-V12] log_parser.py wird geladen (UTC, 4-Digit-IATA, Robuste Regex V12) ... ---")

import re
import pandas as pd
from datetime import datetime
import os
import pytz # Import für Zeitzonen

# --- Normalisierungsfunktion (unverändert) ---
def _normalize_iata(iata_str):
    if pd.isna(iata_str) or iata_str is None: return "N/A"
    
    cleaned_str = "N/A"
    if isinstance(iata_str, str):
        cleaned_str = iata_str.replace('L', '').strip()
    else:
        cleaned_str = str(iata_str).replace('.0', '').strip() 

    if re.fullmatch(r'[0-9]{4}', cleaned_str):
        return cleaned_str  
    if re.fullmatch(r'[0-9]{3}', cleaned_str):
        return cleaned_str.zfill(4) 
    return "N/A"
# --- ENDE ---

TS_PATTERN = re.compile(r"^([A-Z][a-z]{2}\s+[A-Z][a-z]{2}\s+\d{2}\s+\d{2}:\d{2}:\d{2})\.\d+")
BAG_ID_PATTERN = re.compile(r'\"(0\d{9})\"') 

# --- KORRIGIERTE REGEX (V12): Strikte, aber vollständige Suche ---
IATA_PATTERN = re.compile(
    # Fall 1: IATA="0123" ODER for="0123" ODER tric="0123" ODER disposition for="0123"
    r'(?:with IATA|found disposition for|disposition for|IATA|for|tric)\s*=\s*\"([0-9]{3,4})\"' 
    
    # Fall 2: RFID 0123 ODER IATA: 0123 (mit Space ODER Doppelpunkt)
    r'|\b(RFID|IATA)[\s:]+([0-9]{3,4})\b'
    
    # Fall 3: rfid: 0123 (Kleinschreibung, Doppelpunkt)
    r'|\brfid:\s*([0-9]{3,4})\b',
    re.IGNORECASE
)
CCT_PATTERN = re.compile(r'@(CCT\d+)') 

SOURCE_SCANNER = "Scanner"

def map_disposition_to_text(code):
    return "**Freigabe (CLEAR)**" if str(code) == '1' else "**Alarm (ALARM)**"

# --- SCANNER-MUSTER (NEUE STRUKTUR) ---
SCANNER_PATTERNS = [
    (re.compile(r'CreateNewBag'), 
     lambda m, ident, bag_id, iata, dev: f"[{SOURCE_SCANNER}] Gepäckstück **{bag_id}** wird im System angelegt."),
    (re.compile(r'AssignAlgorithms.*assigning (eds-\d\.\d\.\d+|ltr algo object)'), 
     lambda m, ident, bag_id, iata, dev: f"[{SOURCE_SCANNER}] Analyse-Algorithmus '{m.group(1)}' wird zugewiesen."),
    (re.compile(r'Associated.*with IATA=\"([^\"]+)\"'), 
     lambda m, ident, bag_id, iata, dev: f"[{SOURCE_SCANNER}] Gepäckstück {bag_id} wurde Wanne **{_normalize_iata(m.group(1))}** zugeordnet."), # Normalisierung
    (re.compile(r'BagIoHandler::MarkAlgoDone\[([a-z0-9\.-]+)\]'), 
     lambda m, ident, bag_id, iata, dev: f"[{SOURCE_SCANNER}] Analyse durch Algorithmus '{m.group(1)}' ist abgeschlossen."),
    (re.compile(r'SetDisposition\[(MACHINE_OBJECT|MACHINE_THREAT)\].*disp=\"(ALARM|CLEAR)\"'), 
     lambda m, ident, bag_id, iata, dev: f"[{SOURCE_SCANNER}] Maschinelle Entscheidung ({'LTR' if m.group(1) == 'MACHINE_OBJECT' else 'EDS'}): **{m.group(2)}**"),
    (re.compile(r'SetDisposition\[OSR\].*disp=\"(CLEAR|ALARM)\".*op=\"([a-zA-Z0-9_]+)\"'), 
     lambda m, ident, bag_id, iata, dev: f"[{SOURCE_SCANNER}] Finale Operator-Entscheidung von '{m.group(2)}': **{m.group(1)}**"),
    (re.compile(r'SetOperatorDisposition.*operator=([a-zA-Z0-9_]+),\s*disposition=(\d)'), 
     lambda m, ident, bag_id, iata, dev: f"[{SOURCE_SCANNER}] Operator-Entscheidung von '{m.group(1)}': **{'CLEAR' if m.group(2) == '1' else 'ALARM'}**"),
    (re.compile(r'Security rule for this bag is now (\w+)'), 
     lambda m, ident, bag_id, iata, dev: f"[{SOURCE_SCANNER}] Sicherheitsregel für dieses Gepäckstück ist jetzt: **{m.group(1)}**."),
    (re.compile(r'Finished\('), 
     lambda m, ident, bag_id, iata, dev: f"[{SOURCE_SCANNER}] Verarbeitung für Gepäckstück **{bag_id}** im Scanner beendet."),
    (re.compile(r'Ok:Saved'), 
     lambda m, ident, bag_id, iata, dev: f"[{SOURCE_SCANNER}] Bilddaten für Wanne **{ident}** wurden gespeichert.")
]

# --- V13: OMS_PATTERNS entfernt ---

def parse_line_to_klartext(line, source, bag_id, iata, device):
    ident = iata if iata not in ["N/A", "NO_READ"] else bag_id
    
    patterns_to_check = SCANNER_PATTERNS

    for pattern, handler in patterns_to_check:
        if m := pattern.search(line):
            return handler(m, ident, bag_id, iata, device) 
    
    return None 

def _get_timestamp_from_line(line_str, current_year, last_month):
    ts_match = TS_PATTERN.search(line_str)
    if not ts_match: 
        return None, last_month
        
    try:
        dt_no_year = datetime.strptime(ts_match.group(1), "%a %b %d %H:%M:%S")
        year_to_use = current_year
        if last_month and dt_no_year.month == 1 and last_month == 12: 
            year_to_use -= 1
        
        dt_object = dt_no_year.replace(year=year_to_use)
        return dt_object, dt_object.month
        
    except (ValueError, Exception):
        return None, last_month

def _find_last_day_date(file_path, current_year):
    last_month = datetime.now().month
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            try:
                f.seek(0, os.SEEK_END)
                end_pos = f.tell()
                f.seek(max(0, end_pos - 8192), os.SEEK_SET) 
            except (IOError, OSError):
                f.seek(0) 

            for line in reversed(f.readlines()):
                dt_object, _ = _get_timestamp_from_line(line, current_year, last_month)
                if dt_object:
                    print(f"--- log_parser: Letzter Log-Tag gefunden: {dt_object.date()} ---")
                    return dt_object.date()
                    
    except Exception as e:
        print(f"--- log_parser: Fehler beim Finden des letzten Tags: {e} ---")
        return None

def parse_log_file(file_path, update_progress=None, load_last_day=False):
    log_records = []; current_year = datetime.now().year; last_month = None
    
    try:
        local_tz = pytz.timezone('Europe/Berlin')
    except pytz.exceptions.UnknownTimeZoneError:
        local_tz = pytz.utc 
    
    target_date = None
    if load_last_day:
        target_date = _find_last_day_date(file_path, current_year)
        if target_date is None:
            print("--- log_parser: Konnte letzten Tag nicht ermitteln, lade komplettes Log. ---")
            
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f: lines = f.readlines()
    total_lines = len(lines)
    
    for i, line in enumerate(lines):
        if update_progress and (i % 500 == 0 or i == total_lines - 1):
            progress = int((i + 1) / total_lines * 100); update_progress(progress, os.path.basename(file_path))
        
        if '\"0' not in line and 'IATA' not in line and 'RFID' not in line:
            continue
        
        if "[OMS:" in line:
            continue
            
        dt_object, new_last_month = _get_timestamp_from_line(line, current_year, last_month)
        if not dt_object:
            continue
        last_month = new_last_month
        
        if load_last_day and target_date and dt_object.date() != target_date:
            continue 
            
        try:
            aware_local_time = local_tz.localize(dt_object, is_dst=None)
            timestamp_utc = aware_local_time.astimezone(pytz.utc)
        except Exception as tz_err:
            continue
            
        bag_id_match = BAG_ID_PATTERN.search(line)
        iata_match = IATA_PATTERN.search(line) # Nutzt die neue, strikte Regex (V12)
        
        bag_id = bag_id_match.group(1) if bag_id_match else "N/A"
        
        # --- KORRIGIERTE GRUPPEN-ZUWEISUNG (V12) ---
        raw_iata = "N/A"
        if iata_match:
            raw_iata = iata_match.group(1) or iata_match.group(3) or iata_match.group(4)
        iata = _normalize_iata(raw_iata)
        # --- ENDE KORREKTUR ---
        
        cct_match = CCT_PATTERN.search(line)
        device = cct_match.group(1) if cct_match else "N/A" 
        
        if bag_id == "N/A" and iata == "N/A": continue
            
        source = SOURCE_SCANNER 
        
        klartext = parse_line_to_klartext(line, source, bag_id, iata, device)
        
        if klartext: 
            log_records.append({
                "Timestamp": timestamp_utc, 
                "BagID": bag_id, 
                "IATA": iata, 
                "Source": source, 
                "Klartext": klartext, 
                "OriginalLog": line.strip(),
                "Device": device 
            })
            
    return pd.DataFrame(log_records)