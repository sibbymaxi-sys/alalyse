# log_parser.py
print("--- [V23-FIX] log_parser.py wird geladen (Kein UTC, OMS-Filter, CCT) ... ---")

import re
import pandas as pd
from datetime import datetime
import os

TS_PATTERN = re.compile(r"^([A-Z][a-z]{2}\s+[A-Z][a-z]{2}\s+\d{2}\s+\d{2}:\d{2}:\d{2})\.\d+")
BAG_ID_PATTERN = re.compile(r'\"(0\d{9})\"') 
IATA_PATTERN = re.compile(r'(?:with IATA|found disposition for|RFID|tric)\s*=\s*\"([^\"]+)\"|\bRFID\s+([0-9]{4})\b', re.IGNORECASE)
CCT_PATTERN = re.compile(r'@(CCT\d+)') 

SOURCE_SCANNER = "Scanner"
SOURCE_OMS = "OMS"

def map_disposition_to_text(code):
    return "**Freigabe (CLEAR)**" if str(code) == '1' else "**Alarm (ALARM)**"

# --- SCANNER-MUSTER (NEUE STRUKTUR) ---
SCANNER_PATTERNS = [
    (re.compile(r'CreateNewBag'), 
     lambda m, ident, bag_id, iata, dev: f"[{SOURCE_SCANNER}] Gepäckstück **{bag_id}** wird im System angelegt."),
    (re.compile(r'AssignAlgorithms.*assigning (eds-\d\.\d\.\d+|ltr algo object)'), 
     lambda m, ident, bag_id, iata, dev: f"[{SOURCE_SCANNER}] Analyse-Algorithmus '{m.group(1)}' wird zugewiesen."),
    (re.compile(r'Associated.*with IATA=\"([^\"]+)\"'), 
     lambda m, ident, bag_id, iata, dev: f"[{SOURCE_SCANNER}] Gepäckstück {bag_id} wurde Wanne **{m.group(1)}** zugeordnet."),
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

# --- OMS-MUSTER (Kombination aus deinen Wünschen und den alten Mustern) ---
OMS_PATTERNS = [
    (re.compile(r"writing to PLC diverter cmd:\s+(\d)"),  
     lambda m, ident, bag_id, iata, dev: f"[{SOURCE_OMS}] **Finaler Befehl an Förderanlage gesendet: {map_disposition_to_text(m.group(1))}**"),
    (re.compile(r"setFinalBagDisposition.*final disposition is (\d)"), 
     lambda m, ident, bag_id, iata, dev: f"[{SOURCE_OMS}] Interne, finale Entscheidung für Wanne **{ident}** wird gesetzt auf: {map_disposition_to_text(m.group(1))}"),
    (re.compile(r"lookUpBagDisposition.*found disposition for\s+\"([^\"]+)\""), 
     lambda m, ident, bag_id, iata, dev: f"[{SOURCE_OMS}] Finale Entscheidung für Wanne **{m.group(1)}** in Datenbank gefunden."),
    (re.compile(r"lookUpBagDisposition.*Entering"), 
     lambda m, ident, bag_id, iata, dev: f"[{SOURCE_OMS}] Sucht nach finaler Entscheidung für Wanne **{ident}** in der Datenbank."),
    
    # --- WUNSCH: Diese Zeile ausblenden ---
    (re.compile(r"RFID FOUND -.*HIGHALERT:"), 
     lambda m, ident, bag_id, iata, dev: None), # Gibt None zurück -> wird ignoriert
    
    (re.compile(r"slotSendTricBagDispositionMsg", re.IGNORECASE),
     lambda m, ident, bag_id, iata, dev: f"[{SOURCE_OMS}] Disposition-Nachricht (Entscheidung) wird an TRIC gesendet."),
    (re.compile(r"slotDivertRfid", re.IGNORECASE),
     lambda m, ident, bag_id, iata, dev: f"[{SOURCE_OMS}] RFID (Wanne **{ident}**) an Weiche erkannt."),
    (re.compile(r"slotDiverterAction", re.IGNORECASE),
     lambda m, ident, bag_id, iata, dev: f"[{SOURCE_OMS}] Aktion für Wanne **{ident}** an Weiche wird ausgeführt."),
    (re.compile(r"\[OMS:\d+:\w+\]:\s(?:virtual void|void|virtual bool|int)\s+([\w:]+)\("),
     lambda m, ident, bag_id, iata, dev: f"[{SOURCE_OMS}] Technischer Systemaufruf: {m.group(1)}")
]

def parse_line_to_klartext(line, source, bag_id, iata, device):
    """
    Sucht nach einem passenden Muster in der Zeile und gibt den Klartext zurück.
    Verwendet jetzt die neuen Pattern-Listen.
    """
    ident = iata if iata not in ["N/A", "NO_READ"] else bag_id
    
    patterns_to_check = []
    if source == SOURCE_SCANNER:
        patterns_to_check = SCANNER_PATTERNS
    elif source == SOURCE_OMS:
        patterns_to_check = OMS_PATTERNS

    for pattern, handler in patterns_to_check:
        if m := pattern.search(line):
            # Rufe die zugehörige Lambda-Funktion auf
            return handler(m, ident, bag_id, iata, device) 
    
    return None # Kein Muster hat gepasst

def _get_timestamp_from_line(line_str, current_year, last_month):
    """Hilfsfunktion, um einen Zeitstempel aus einer Zeile zu extrahieren."""
    ts_match = TS_PATTERN.search(line_str)
    if not ts_match: 
        return None, last_month
        
    try:
        dt_no_year = datetime.strptime(ts_match.group(1), "%a %b %d %H:%M:%S")
        year_to_use = current_year
        if last_month and dt_no_year.month == 1 and last_month == 12: 
            year_to_use -= 1
        
        # --- KORREKTUR (Kein UTC) ---
        dt_object = dt_no_year.replace(year=year_to_use)
        return dt_object, dt_object.month
        
    except (ValueError, Exception):
        return None, last_month

def _find_last_day_date(file_path, current_year):
    """Liest eine Datei von hinten, um das Datum des letzten Eintrags zu finden."""
    last_month = datetime.now().month
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            # Versuche, das Ende der Datei zu lesen (effizient)
            try:
                f.seek(0, os.SEEK_END)
                end_pos = f.tell()
                f.seek(max(0, end_pos - 8192), os.SEEK_SET) # Lese letzte 8KB
            except (IOError, OSError):
                f.seek(0) # Fallback: Lese von vorne

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
        
        # --- OPTIMIERUNG 1: "PRE-FILTER" ---
        if '\"0' not in line and 'IATA' not in line and 'RFID' not in line:
            continue
            
        dt_object, new_last_month = _get_timestamp_from_line(line, current_year, last_month)
        if not dt_object:
            continue
        last_month = new_last_month
        
        # --- NEU: "Letzter Tag"-Filter ---
        if load_last_day and target_date and dt_object.date() != target_date:
            continue # Überspringe alle Zeilen, die nicht vom Zieldatum sind
            
        bag_id_match = BAG_ID_PATTERN.search(line); iata_match = IATA_PATTERN.search(line)
        bag_id = bag_id_match.group(1) if bag_id_match else "N/A"
        iata = (iata_match.group(1) or iata_match.group(2)) if iata_match else "N/A"
        
        cct_match = CCT_PATTERN.search(line)
        device = cct_match.group(1) if cct_match else "N/A"
        
        if bag_id == "N/A" and iata == "N/A": continue
            
        source = SOURCE_OMS if "[OMS:" in line else SOURCE_SCANNER
        
        klartext = parse_line_to_klartext(line, source, bag_id, iata, device)
        
        if klartext: # Ignoriert Zeilen, wenn Klartext 'None' ist (z.B. "RFID FOUND")
            log_records.append({
                "Timestamp": dt_object, 
                "BagID": bag_id, 
                "IATA": iata, 
                "Source": source, 
                "Klartext": klartext, 
                "OriginalLog": line.strip(),
                "Device": device 
            })
            
    return pd.DataFrame(log_records)