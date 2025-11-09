# plclog_journey_parser.py
print("--- [NEUSTART] plclog_journey_parser.py wird geladen (Neue 2-Phasen-Logik) ... ---")

import re
import pandas as pd
from datetime import datetime
import os
import traceback # Importiert
from collections import defaultdict

# --- REGEX-MUSTER (Passend zu den Log-Daten, mit Leerzeichen) ---

# 1. Zeitstempel (Muss am Zeilenanfang stehen)
TIMESTAMP_PATTERN = re.compile(r'^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{3})?Z)')

# 2. IATA-Muster (Priorisiert)
RE_IATA_QUEUE = re.compile(r'Tray\s+with\s+RFID:\s*([\wL]+)\s+added') # Wichtigstes Muster
RE_IATA_RESULT = re.compile(r'tray\s*:\s*([\wL]+)') 
RE_RFID_READ = re.compile(r'ID\s+([\wL]+)') 
RE_IATA_INFEED = re.compile(r'New\s+tray\s+INFEED\s+-0\s+ID:\s*([\wL]+)')
RE_IATA_EXAMINED = re.compile(r'EXAMINED:\s*(\w+)') 
RE_IATA_SIMPLE = re.compile(r'ID:\s*(\w+)') 

# 3. Key-Muster
RE_KEY_ADDED = re.compile(r'key:\s*(\d+)') 
RE_KEY_DELETED = re.compile(r'key(\d+)') # Für 'key17265'

def normalize_rfid(rfid_str):
    """ Normalisiert '000L0131' zu '131' """
    if not rfid_str or rfid_str == "0": 
        return "N/A"
    match = re.search(r'0*L?0*(\d+)$', rfid_str) 
    if match:
        return match.group(1)
    return rfid_str.strip()

def _find_iata_in_line(infotext):
    """ Findet die IATA in einer normalisierten Zeile """
    if match := RE_IATA_QUEUE.search(infotext):
        return normalize_rfid(match.group(1))
    elif match := RE_IATA_RESULT.search(infotext):
        return normalize_rfid(match.group(1))
    elif match := RE_RFID_READ.search(infotext):
        return normalize_rfid(match.group(1))
    elif match := RE_IATA_INFEED.search(infotext):
        return normalize_rfid(match.group(1))
    elif match := RE_IATA_EXAMINED.search(infotext):
        return normalize_rfid(match.group(1))
    elif match := RE_IATA_SIMPLE.search(infotext):
        return normalize_rfid(match.group(1))
    return None

def _find_key_in_line(infotext):
    """ Findet den Key in einer normalisierten Zeile """
    if match := RE_KEY_ADDED.search(infotext):
        return match.group(1)
    elif match := RE_KEY_DELETED.search(infotext):
        return match.group(1)
    return None

def _get_klartext_for_event(infotext):
    """ Erstellt Klartext NUR für relevante Zeilen """
    
    if re.search(r'added\s+to\s+queue', infotext): return "Wanne zur System-Warteschlange hinzugefügt"
    if re.search(r'RFID\s+READER\s+([1-2])\s+data\s+ready', infotext): return "[PLC] Wanne am Zulauf erkannt (Reader 1/2)"
    if re.search(r'New\s+tray\s+INFEED', infotext): return "[PLC] Wanne am Zulauf (Infeed) registriert"
    
    if re.search(r'RFID\s+READER\s+([3-4])\s+data\s+ready', infotext): return "[PLC] Wanne an der Weiche erkannt (Reader 3/4)"
    if 'NEW_TRAY_DIVERTER' in infotext: return "[PLC] Wanne an Weiche registriert"
    
    if re.search(r'Result\s+CLEAR\s+for\s+tray', infotext): return "System-Ergebnis verbucht: CLEAR"
    if re.search(r'Result\s+REJECT\s+for\s+tray', infotext): return "System-Ergebnis verbucht: REJECT"
    
    match_decision = re.search(r'NEW_INFO_RFID.*decision:\s*(\d)', infotext)
    if match_decision:
        decision_text = "CLEAR" if match_decision.group(1) == '1' else "REJECT"
        return f"Entscheidung vom Scanner empfangen: {decision_text}"
        
    step_match = re.search(r'Diverter\s+(clear|reject)\s+-0\s+Step\s+(250|700|2000)', infotext)
    if step_match:
        dtype, step = step_match.groups()
        if step == '250': return f"Wanne ist in Position (Step 250)"
        if step == '700': return f"Weiche '{dtype}': Fährt vorwärts (Step 700)"
        if step == '2000': return f"Weiche '{dtype}': Zyklus beendet (Step 2000)"
        
    if re.search(r'Deleting\s+tray\s+with\s+key\d+', infotext): return "[PLC] Wanne wird aus Warteschlange gelöscht"
    
    if 'CLEARSCAN_BELT_STOP' in infotext: return "[PLC] Gurt gestoppt"

    return None # Alle anderen Zeilen (Steps 0, 50, etc.) ignorieren

def parse_log(file_path, progress_callback=None):
    """
    Parst eine PlcLog.csv-Datei mit 2-Phasen-Logik
    (1. Normalisieren, 2. Zuordnen)
    """
    
    preliminary_events = []
    key_to_iata_map = {}
    
    try:
        total_size = os.path.getsize(file_path)
        processed_size = 0
        
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                processed_size += len(line.encode('utf-8'))
                if progress_callback and processed_size % 100000 == 0:
                    progress = int((processed_size / total_size) * 100)
                    progress_callback(progress, f"Lese {os.path.basename(file_path)}...")

                original_log = line.strip()
                if not original_log: continue

                # --- Phase 1: Normalisieren (Umwandeln) ---
                # Ersetze alle Kommas und Semikolons durch Leerzeichen
                normalized_line = original_log.replace(',', ' ').replace(';', ' ').replace('\t', ' ')
                # Entferne mehrfache Leerzeichen
                infotext = re.sub(r'\s+', ' ', normalized_line).strip()

                timestamp_match = TIMESTAMP_PATTERN.search(infotext)
                if not timestamp_match:
                    continue 

                timestamp = pd.to_datetime(timestamp_match.group(1)).tz_localize(None)

                # --- Phase 2: Verknüpfen (Landkarte bauen) ---
                iata = _find_iata_in_line(infotext)
                key = _find_key_in_line(infotext)
                
                # Speichere die Rohdaten für Phase 3
                preliminary_events.append({
                    "Timestamp": timestamp,
                    "IATA_found": iata, # IATA, die wir in dieser Zeile gefunden haben
                    "Key_found": key,   # Key, den wir in dieser Zeile gefunden haben
                    "Info": infotext,   # Normalisierter Text
                    "OriginalLog": original_log 
                })
                
                # Wenn die Zeile "added to queue" ist, ist die Verknüpfung sicher
                if key and iata and iata != "N/A" and re.search(r'added\s+to\s+queue', infotext):
                    key_to_iata_map[key] = iata

    except Exception as e:
        print(f"Fehler bei Phase 1 (Sammeln) in {file_path}: {e}")
        traceback.print_exc()
        return pd.DataFrame() 

    if not preliminary_events:
        # Dieser print-Befehl hilft beim Debuggen
        print("DEBUG: Phase 1 (Sammeln) hat keine Events gefunden.")
        return pd.DataFrame(columns=["Timestamp", "IATA", "Klartext", "OriginalLog", "JourneyID"])

    # --- Phase 3 & 4: Zuordnen & Filtern ---
    final_records = []
    
    for event in preliminary_events:
        final_iata = event["IATA_found"]
        key = event["Key_found"]
        
        # Wenn IATA fehlt, aber Key da ist -> Nachschlagen
        if (final_iata is None or final_iata == "N/A") and key:
            final_iata = key_to_iata_map.get(key, "N/A") 

        # Wenn IATA (auch nach dem Nachschlagen) fehlt, ist die Zeile nutzlos
        if final_iata is None or final_iata == "N/A":
            continue
            
        # Erst JETZT den Klartext generieren
        klartext = _get_klartext_for_event(event["Info"])
        
        # Nur relevante Zeilen behalten
        if not klartext:
            continue
            
        final_records.append({
            "Timestamp": event["Timestamp"],
            "Source": "PLC",
            "IATA": final_iata, # Die final zugewiesene IATA
            "Klartext": klartext,
            "OriginalLog": event["OriginalLog"]
        })

    if not final_records:
        print("DEBUG: Phase 2 (Zuordnen) hat keine Events zugeordnet.")
        return pd.DataFrame()

    df = pd.DataFrame(final_records)
    
    # De-Duplizierung (pro IATA)
    df = df.drop_duplicates(subset=["IATA", "Klartext"])
    
    return df.sort_values(by="Timestamp").reset_index(drop=True)