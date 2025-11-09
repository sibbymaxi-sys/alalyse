# oms_log_parser.py
print("--- [V8-FIX-14] oms_log_parser.py wird geladen (Nur OMS, Robuste Regex V12, MEHR Klartext V14) ... ---")

import re
import pandas as pd
from datetime import datetime
import os
import pytz
import traceback 

# --- KORREKTUR: Importiere die Übersetzungs-Logik aus log_parser.py ---
try:
    from log_parser import _normalize_iata
    print("--- INFO (oms_log_parser): _normalize_iata erfolgreich aus log_parser importiert. ---")
except ImportError:
    print("--- WARNUNG (oms_log_parser): Konnte _normalize_iata nicht aus log_parser importieren. Definiere Fallback. ---")
    
    # --- Fallback-Definition (KORRIGIERT, um '0123' beizubehalten) ---
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

def map_disposition_to_text(code):
    """Übersetzt '1' in CLEAR, alles andere in ALARM."""
    return "**Freigabe (CLEAR)**" if str(code) == '1' else "**Alarm (ALARM)**"

# --- KORREKTUR (V14): Verbesserte Klartext-Muster ---
EVENT_PATTERNS = [
    # Wichtige Entscheidungen
    (re.compile(r"writing to PLC diverter cmd:\s+(\d)"), 
        lambda m, ident: f"[OMS] **Finaler Befehl an Förderanlage gesendet: {map_disposition_to_text(m.group(1))}**"),
    (re.compile(r"setFinalBagDisposition.*final disposition is (\d)"), 
        lambda m, ident: f"[OMS] Interne, finale Entscheidung für Wanne **{ident}** wird gesetzt auf: {map_disposition_to_text(m.group(1))}"),
    (re.compile(r"postOpDec.*diverter cmd:\s*(\d)"),
        lambda m, ident: f"[OMS] Operator-Entscheidung an SPS gesendet: {map_disposition_to_text(m.group(1))}"),

    # Cache-Logik
    (re.compile(r"cacheBagDisposition.*saving disposition for\s+\"([^\"]+)\""),
        lambda m, ident: f"[OMS] Speichere Entscheidung für Wanne **{_normalize_iata(m.group(1))}** im Cache."),
    (re.compile(r"cacheBagDisposition.*updating disposition for\s+\"([^\"]+)\""),
        lambda m, ident: f"[OMS] Aktualisiere Entscheidung für Wanne **{_normalize_iata(m.group(1))}** im Cache."),
    (re.compile(r"removeBagDisposition.*found disposition for\s+\"([^\"]+)\""),
        lambda m, ident: f"[OMS] Lösche Entscheidung für Wanne **{_normalize_iata(m.group(1))}** aus Cache (Vorgang beendet)."),

    # Datenbank-Logik
    (re.compile(r"lookUpBagDisposition.*found disposition for\s+\"([^\"]+)\""), 
        lambda m, ident: f"[OMS] Finale Entscheidung für Wanne **{_normalize_iata(m.group(1))}** in Datenbank gefunden."),
    (re.compile(r"lookUpBagDisposition.*Entering"), 
        lambda m, ident: f"[OMS] Sucht nach finaler Entscheidung für Wanne **{ident}** in der Datenbank."),

    # RFID/Weichen-Logik
    (re.compile(r"slotDiverterAction.*diverter action:\s*(\d)"), 
        lambda m, ident: f"[OMS] Weichen-Aktion für Wanne **{ident}** ausgeführt: {map_disposition_to_text(m.group(1))}"),
    (re.compile(r"slotDivertRfid.*operator descision:\s*(\d)"), 
        lambda m, ident: f"[OMS] RFID (Wanne **{ident}**) an Weiche erkannt. Voreingestellte Operator-Entscheidung: {map_disposition_to_text(m.group(1))}"),
    (re.compile(r"slotDivertRfid", re.IGNORECASE), # Fallback
        lambda m, ident: f"[OMS] RFID (Wanne **{ident}**) an Weiche erkannt."),
    
    # Assoziierungs-Logik
    (re.compile(r"slotAssociateExternalBagIDs.*for bag:\s*([0-9]+)\s*IATA:\s*([0-9]+)\s*GLOBAL:\s*(\d+)"),
        lambda m, ident: f"[OMS] Verknüpfe BagID {m.group(1)} mit IATA {_normalize_iata(m.group(2))} (GLOBAL: {m.group(3)})"),
    (re.compile(r"slotDiverterAction.*for bag:\s*([0-9]+)\s*IATA:\s*([0-9]+)"), # Dein Log V13
        lambda m, ident: f"[OMS] Weichen-Aktion: BagID {m.group(1)} mit IATA {_normalize_iata(m.group(2))} verknüpft."),

    # Allgemeine Kommunikation
    (re.compile(r"slotSendTricBagDispositionMsg", re.IGNORECASE),
        lambda m, ident: f"[OMS] Disposition-Nachricht (Entscheidung) wird an TRIC gesendet."),
    
    # Fehler (NEU HINZUGEFÜGT)
    (re.compile(r"disposition for\s+\"([^\"]+)\"\s+does not match\s+(\d+)"),
        lambda m, ident: f"[OMS] FEHLER: ID '{_normalize_iata(m.group(1))}' stimmt nicht mit '{_normalize_iata(m.group(2))}' überein!"),
    (re.compile(r"bag thinks it missed it's diverter event"),
        lambda m, ident: f"[OMS] FEHLER: Bag glaubt, die Weiche verpasst zu haben (Encoder-Problem)."),

    # Ignoriere diese Zeilen
    (re.compile(r"RFID FOUND -"), lambda m, ident: None), # V14: Ignoriere die RFID FOUND Zeile (zu viele Rohdaten)
    (re.compile(r"TricInterfaceMgr::slotSendFaultStatus"), lambda m, ident: None), 
    (re.compile(r"CCTBagImagePool::ReceiveVsCount"), lambda m, ident: None),
    (re.compile(r"slotUpdateTricRTRCnvState"), lambda m, ident: None),
    (re.compile(r"slotSendEncoderUpdate"), lambda m, ident: None)
]
# --- ENDE KORREKTUR V14 ---


# --- KORREKTUR (V12): Zeitstempel-Muster (erkennt BEIDE Formate) ---
TIMESTAMP_PATTERN = re.compile(
    r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}[\.,]\d{3})' # Group 1: UTC Format (z.B. 2025-10-14...)
    r'|([A-Z][a-z]{2}\s+[A-Z][a-z]{2}\s+\d{2}\s+\d{2}:\d{2}:\d{2})\.\d+' # Group 2: Scanner-Format (z.B. Sat Nov 01...)
)
BAG_ID_PATTERN = re.compile(r'\"(0\d{9})\"')

# --- KORRIGIERTE REGEX (V12): Strikte Regex, die Zeitstempel ignoriert ---
IATA_PATTERN = re.compile(
    # V13/V12: 'disposition for' hinzugefügt
    r'(?:with IATA|found disposition for|disposition for|IATA|for|tric)\s*=\s*\"([^\"]+)\"' # Gruppe 1: IATA="0137"
    r'|\b(RFID|IATA)[\s:]+([0-9]{3,4})\b' # Gruppe 2: "RFID" oder "IATA", Gruppe 3: "0137" (mit Space ODER Doppelpunkt)
    r'|\brfid:\s*([0-9]{3,4})\b', # Gruppe 4: "rfid: 0864" (Kleinschreibung)
    re.IGNORECASE
)
OMS_MESSAGE_PATTERN = re.compile(r'\[OMS:.*\]:\s*(.*)')


def parse_oms_log(file_path, update_progress=None):
    """
    Parst eine OMS.log-Datei.
    KORRIGIERT (V14): Behandelt beide Zeitstempel-Formate als LOKALZEIT (Berlin) und 
    verwendet die neue V14-IATA-Regex.
    """
    print(f"\n--- DEBUG (oms_log_parser V8-FIX-14): Starte Analyse für {os.path.basename(file_path)} ---")
    data = []
    current_year = datetime.now().year
    
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
            iata_match = IATA_PATTERN.search(line) # Nutzt die neue, strikte Regex (V12)
            
            bag_id = bag_id_match.group(1) if bag_id_match else "N/A"
            
            # --- KORRIGIERTE GRUPPEN-ZUWEISUNG (V12) ---
            raw_iata = "N/A"
            if iata_match:
                # Prüfe alle 3 möglichen Treffer-Gruppen der neuen Regex
                raw_iata = iata_match.group(1) or iata_match.group(3) or iata_match.group(4)
            iata = _normalize_iata(raw_iata)
            # --- ENDE KORREKTUR ---
            
            ident = iata if iata != "N/A" else bag_id
            
            if bag_id == "N/A" and iata == "N/A":
                continue 
                
            ts_match = TIMESTAMP_PATTERN.search(line)
            if not ts_match:
                continue 
            
            try:
                timestamp_utc = None
                dt_object_naive = None 
                
                if ts_match.group(1):
                    # Fall 1: Format '2025-10-14 12:57:30.096'
                    ts_str = ts_match.group(1).split('.')[0]
                    dt_object_naive = datetime.strptime(ts_str, '%Y-%m-%d %H:%M:%S')
                
                elif ts_match.group(2):
                    # Fall 2: Format 'Sat Nov 01 06:01:27'
                    dt_no_year = datetime.strptime(ts_match.group(2), "%a %b %d %H:%M:%S")
                    dt_object_naive = dt_no_year.replace(year=current_year)
                
                else:
                    continue 

                if dt_object_naive:
                    aware_local_time = local_tz.localize(dt_object_naive, is_dst=None)
                    timestamp_utc = aware_local_time.astimezone(pytz.utc)

                if pd.isna(timestamp_utc):
                    continue
                    
            except ValueError as ve:
                continue
            except Exception as e:
                continue
                
            # --- KLARTEXT-LOGIK (V14) ---
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
                    # Nimm nur den Text, wenn er nicht bereits von EVENT_PATTERNS als "None" (ignoriert) markiert wurde
                    if not any(p.search(line) for p, func in EVENT_PATTERNS if func is None):
                        klartext = f"[OMS] {message_match.group(1).strip()}"
                else:
                    ts_prefix_match = re.match(r'([A-Z][a-z]{2}\s+[A-Z][a-z]{2}\s+\d{2}\s+\d{2}:\d{2}:\d{2})\.\d+\s+(.*)', line)
                    if ts_prefix_match:
                         if not any(p.search(line) for p, func in EVENT_PATTERNS if func is None):
                             klartext = f"[OMS-RAW] {ts_prefix_match.group(2).strip()}"
                    else:
                         if not any(p.search(line) for p, func in EVENT_PATTERNS if func is None):
                             klartext = f"[OMS-RAW] {line.strip()}" 
            # --- ENDE ---
            
            if klartext: # Nur hinzufügen, wenn Klartext nicht 'None' ist
                data.append({
                    'Timestamp': timestamp_utc, 
                    'Source': 'OMS', 
                    'Klartext': klartext,
                    'OriginalLog': line.strip(), 
                    'IATA': iata, 
                    'BagID': bag_id,
                    'Device': "N/A" # OMS-Parser findet kein CCT-Gerät
                })
                
    except Exception as e:
        print(f"--- FEHLER im OMS Parser (V8-FIX-14): {e} ---")
        traceback.print_exc()

    print(f"--- DEBUG (oms_log_parser V8-FIX-14): {len(data)} OMS-Zeilen erfolgreich extrahiert ---")
    return pd.DataFrame(data)