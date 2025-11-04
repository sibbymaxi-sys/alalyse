# oms_log_parser.py
print("--- [V8-FIX-2] oms_log_parser.py wird geladen (Berlin-Time) ... ---")

import re
import pandas as pd
from datetime import datetime
import os
import pytz
import traceback # Import für Fehler-Debugging hinzugefügt

# --- KORREKTUR: Importiere die Übersetzungs-Logik aus log_parser.py ---
try:
    from log_parser import _normalize_iata
except ImportError:
    print("--- WARNUNG (oms_log_parser): Konnte _normalize_iata nicht aus log_parser importieren. Definiere Fallback. ---")
    
    # --- Fallback-Definition ---
    def _normalize_iata(iata_str):
        if pd.isna(iata_str) or iata_str is None: return "N/A"
        if re.fullmatch(r'\d{3,4}', iata_str):
            try: return str(int(iata_str))
            except ValueError: return str(iata_str)
        try:
            norm_id = str(int(str(iata_str).replace('L', '')))
            return norm_id
        except ValueError: return str(iata_str)

# --- KLARTEXT-MUSTER ---
EVENT_PATTERNS = [
    (re.compile(r"writing to PLC diverter cmd:\s+(\d)"), 
        lambda m, ident: f"[OMS] **Finaler Befehl an Förderanlage gesendet: {map_disposition_to_text(m.group(1))}**"),
    (re.compile(r"setFinalBagDisposition.*final disposition is (\d)"), 
        lambda m, ident: f"[OMS] Interne, finale Entscheidung für Wanne **{ident}** wird gesetzt auf: {map_disposition_to_text(m.group(1))}"),
    (re.compile(r"lookUpBagDisposition.*found disposition for\s+\"([^\"]+)\""), 
        lambda m, ident: f"[OMS] Finale Entscheidung für Wanne **{m.group(1)}** in Datenbank gefunden."),
    (re.compile(r"lookUpBagDisposition.*Entering"), 
        lambda m, ident: f"[OMS] Sucht nach finaler Entscheidung für Wanne **{ident}** in der Datenbank."),
    (re.compile(r"slotSendTricBagDispositionMsg", re.IGNORECASE),
        lambda m, ident: f"[OMS] Disposition-Nachricht (Entscheidung) wird an TRIC gesendet."),
    (re.compile(r"slotDivertRfid", re.IGNORECASE),
        lambda m, ident: f"[OMS] RFID (Wanne **{ident}**) an Weiche erkannt."),
    (re.compile(r"slotDiverterAction", re.IGNORECASE),
        lambda m, ident: f"[OMS] Aktion für Wanne **{ident}** an Weiche wird ausgeführt."),
    (re.compile(r"disposition for\s+\"([^\"]+)\"\s+does not match\s+(\d+)"),
        lambda m, ident: f"[OMS] FEHLER: ID '{m.group(1)}' stimmt nicht mit '{m.group(2)}' überein!"),
    (re.compile(r"RFID FOUND -.*HIGHALERT"), 
        lambda m, ident: None), 
    (re.compile(r"TricInterfaceMgr::slotSendFaultStatus"), 
        lambda m, ident: None), 
    (re.compile(r"CCTBagImagePool::ReceiveVsCount"), 
        lambda m, ident: None)
]

def map_disposition_to_text(code):
    return "**Freigabe (CLEAR)**" if str(code) == '1' else "**Alarm (ALARM)**"
# --- ENDE KLARTEXT ---


# Zeitstempel-Muster (erkennt BEIDE Formate)
TIMESTAMP_PATTERN = re.compile(
    r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}[\.,]\d{3})' # Group 1: UTC Format (z.B. 2025-10-14...)
    r'|([A-Z][a-z]{2}\s+[A-Z][a-z]{2}\s+\d{2}\s+\d{2}:\d{2}:\d{2})\.\d+' # Group 2: Scanner-Format (z.B. Sat Nov 01...)
)
BAG_ID_PATTERN = re.compile(r'\"(0\d{9})\"')
IATA_PATTERN = re.compile(r'(?:IATA|for|tric)\s*=\s*\"([^\"]+)\"|\b([0-9]{4})\b', re.IGNORECASE)
OMS_MESSAGE_PATTERN = re.compile(r'\[OMS:.*\]:\s*(.*)')

# HINWEIS: Das Argument 'local_tz' wird entfernt, da wir es jetzt fest auf Berlin setzen
def parse_oms_log(file_path, update_progress=None):
    """
    Parst eine OMS.log-Datei.
    KORRIGIERT: Behandelt beide Zeitstempel-Formate als LOKALZEIT (Berlin) und 
    konvertiert sie korrekt nach UTC.
    """
    print(f"\n--- DEBUG (oms_log_parser V8-FIX-2): Starte Analyse für {os.path.basename(file_path)} ---")
    data = []
    current_year = datetime.now().year
    
    # --- KORREKTUR: Zeitstempel als LOKALZEIT (Berlin) behandeln ---
    try:
        local_tz = pytz.timezone('Europe/Berlin')
    except pytz.exceptions.UnknownTimeZoneError:
        local_tz = pytz.utc # Fallback
    
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
            
        total_lines = len(lines)
        if total_lines == 0:
            return pd.DataFrame()

        for i, line in enumerate(lines):
            if update_progress and (i % 200 == 0 or i == total_lines - 1):
                progress = int(((i + 1) / total_lines) * 100)
                update_progress(progress, f"Analysiere {os.path.basename(file_path)}...")

            bag_id_match = BAG_ID_PATTERN.search(line)
            iata_match = IATA_PATTERN.search(line)
            
            bag_id = bag_id_match.group(1) if bag_id_match else "N/A"
            raw_iata = "N/A"
            if iata_match:
                raw_iata = iata_match.group(1) or iata_match.group(2)
            
            iata = _normalize_iata(raw_iata)
            ident = iata if iata != "N/A" else bag_id
            
            if bag_id == "N/A" and iata == "N/A":
                continue 
                
            ts_match = TIMESTAMP_PATTERN.search(line)
            if not ts_match:
                continue 
            
            try:
                timestamp_utc = None
                dt_object_naive = None # Naives (zeitzonenloses) Datums-Objekt
                
                if ts_match.group(1):
                    # Fall 1: Format '2025-10-14 12:57:30.096'
                    # Entferne Millisekunden-Teil, der manchmal Probleme macht
                    ts_str = ts_match.group(1).split('.')[0]
                    dt_object_naive = datetime.strptime(ts_str, '%Y-%m-%d %H:%M:%S')
                
                elif ts_match.group(2):
                    # Fall 2: Format 'Sat Nov 01 06:01:27'
                    dt_no_year = datetime.strptime(ts_match.group(2), "%a %b %d %H:%M:%S")
                    dt_object_naive = dt_no_year.replace(year=current_year)
                
                else:
                    continue # Kein Zeitstempel gefunden

                # --- KORREKTUR: Wende Berlin-Zeitzonen-Logik an ---
                if dt_object_naive:
                    # 1. Mache die 'naive' Zeit 'aware' (Lokalzeit Berlin)
                    aware_local_time = local_tz.localize(dt_object_naive, is_dst=None)
                    # 2. Konvertiere die Lokalzeit nach UTC zur Speicherung
                    timestamp_utc = aware_local_time.astimezone(pytz.utc)
                # --- ENDE KORREKTUR ---

                if pd.isna(timestamp_utc):
                    continue
                    
            except ValueError as ve:
                # print(f"Datumsfehler: {ve} bei Zeile: {line.strip()}")
                continue
            except Exception as e:
                # print(f"Allg. Fehler: {e} bei Zeile: {line.strip()}")
                continue
                
            # --- KLARTEXT-LOGIK ---
            klartext = None
            for pattern, translation_func in EVENT_PATTERNS:
                match = pattern.search(line)
                if match:
                    if translation_func is None:
                        klartext = None 
                        break
                    klartext = translation_func(match, ident)
                    break 
            
            if klartext is None:
                message_match = OMS_MESSAGE_PATTERN.search(line)
                if message_match:
                    klartext = f"[OMS] {message_match.group(1).strip()}"
                else:
                    ts_prefix_match = re.match(r'([A-Z][a-z]{2}\s+[A-Z][a-z]{2}\s+\d{2}\s+\d{2}:\d{2}:\d{2})\.\d+\s+(.*)', line)
                    if ts_prefix_match:
                         klartext = f"[OMS] {ts_prefix_match.group(2).strip()}"
                    else:
                         klartext = f"[OMS] {line.strip()}" 
            # --- ENDE ---
            
            if klartext:
                data.append({
                    'Timestamp': timestamp_utc, # WICHTIG: Hier wird der UTC-Zeitstempel gespeichert
                    'Source': 'OMS', 
                    'Klartext': klartext,
                    'OriginalLog': line.strip(), 
                    'IATA': iata, 
                    'BagID': bag_id,
                    'Device': "N/A" 
                })
                
    except Exception as e:
        print(f"--- FEHLER im OMS Parser (V8-FIX-2): {e} ---")
        traceback.print_exc()

    print(f"--- DEBUG (oms_log_parser V8-FIX-2): {len(data)} OMS-Zeilen erfolgreich extrahiert ---")
    return pd.DataFrame(data)