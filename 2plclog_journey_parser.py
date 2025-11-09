# plclog_journey_parser.py
print("--- [V23-FIX] plclog_journey_parser.py wird geladen (NEUE Start/End-Logik + De-Duplizierung) ... ---")

import re
import pandas as pd
from datetime import datetime
import os
from collections import defaultdict

# --- KORRIGIERTES MUSTER (DEINE LOGIK BLEIBT ERHALTEN) ---
# Das Muster (.\d{3})? macht die Millisekunden optional.
# Es erkennt jetzt BEIDES: ...SSZ und ...SS.sssZ
TIMESTAMP_PATTERN = re.compile(r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{3})?Z)')
# --- ENDE DER KORREKTUR ---

# --- Regex-Muster für die IATA-Erkennung ---
RE_RFID_READ = re.compile(r'ID;([\wL]+)(?:;|$)')
RE_IATA_SIMPLE = re.compile(r'ID:;(\w+)(?:;|$)')
RE_IATA_EXAMINED = re.compile(r'EXAMINED:;(\w+)(?:;|$)')
RE_IATA_RESULT = re.compile(r'tray;:;([\wL]+)(?:;|$)')

def normalize_rfid(rfid_str):
    """ 
    Normalisiert die RFID-Strings (z.B. '000L0131' -> '131', '0460' -> '460', '0' -> 'N/A')
    """
    if not rfid_str or rfid_str == "0": 
        return "N/A"
    
    match = re.search(r'0*L?0*(\d+)$', rfid_str) 
    if match:
        return match.group(1)
    
    return rfid_str.strip().replace(';', '')

def _get_klartext_for_event(infotext):
    """ 
    Wandelt eine technische Log-Zeile in einen Klartext-Schritt um.
    (Basierend auf deinem Wanne 195-Beispiel)
    """
    
    # 1. Scanner-Entscheidung
    match_decision = re.search(r'NEW_INFO_RFID.*EXAMINED:;(\w+);.*decision:;(\d)', infotext)
    if match_decision:
        decision = match_decision.group(2)
        decision_text = "CLEAR" if decision == '1' else "REJECT"
        return f"Entscheidung vom Scanner empfangen: Decision {decision} ({decision_text})"
        
    # 2. Weichen-Schritte
    step_match = re.search(r'Diverter;(clear|reject);-0;Step;(\w+);(.*)', infotext)
    if step_match:
        dtype, step, info = step_match.groups()
        info_clean = info.split(';')[0].strip()
        
        # Ignoriere technische Steps (0, 50, 100, 551, 600)
        if step in ('0', '50', '100', '551', '600'):
            return None 
            
        if step == '250': return f"Wanne ist in Position (Step 250)"
        if step == '300': return f"Weiche 'reject': Aktion REJECT (Step 300)"
        if step == '450': return f"Weiche 'reject': Aktion RightFWD (Step 450)"
        if step == '550': return f"Weiche 'reject': Aktion Links (Step 550)"
        if step == '700': return f"Weiche '{dtype}': Fährt vorwärts (Step 700 {info_clean})"
        if step == '1000': return f"FEHLER: System im ERROR STOP (Step 1000)"
        if step == '2000': return f"Weiche '{dtype}': Zyklus beendet (Step 2000)"
        return None # Ignoriere alle anderen unbekannten Steps

    # 3. Ankunft / Registrierung
    if 'NEW_TRAY_DIVERTER' in infotext:
        return "[PLC] Wanne an Weiche registriert"
    if 'INFO_RECEIVED_DVERTER' in infotext:
        return "[PLC] Info von Weiche empfangen"
    if 'FT;Module;before;diverter' in infotext:
        return f"[PLC] Sensor 'FT Module before diverter' Status: {infotext.split('=')[-1].strip()}"
    if 'FT;Module;before;scanner' in infotext:
        return f"[PLC] Sensor 'FT Module before scanner' Status: {infotext.split('=')[-1].strip()}"
        
    # 4. Zulauf (Reader 1 & 2)
    rfid_match = re.search(r'RFID;READER;([1-2]);data;ready', infotext)
    if rfid_match:
        return f"[PLC] Wanne am Zulauf erkannt (Reader {rfid_match.group(1)})"

    # 5. Ankunft Weiche (Reader 3 & 4)
    rfid_match_div = re.search(r'RFID;READER;([3-4]);data;ready', infotext)
    if rfid_match_div:
        return f"[PLC] Wanne an der Weiche erkannt (Reader {rfid_match_div.group(1)})"

    # 6. Hinzufügen zur Queue
    if 'added;to;queue' in infotext:
        return "Wanne zur System-Warteschlange hinzugefügt"
    if 'New;tray;INFEED' in infotext:
        return "[PLC] Wanne am Zulauf (Infeed) registriert"
    if 'INFO_RECEIVED_INFEED' in infotext:
        return "[PLC] Info von Zulauf (Infeed) empfangen"

    # 7. Ergebnisse (WICHTIG für Regel 2)
    if 'Result;CLEAR;for;tray' in infotext:
        return "System-Ergebnis verbucht: CLEAR"
    if 'Result;REJECT;for;tray' in infotext:
        return "System-Ergebnis verbucht: REJECT"

    # 8. Fehler (WICHTIG für Regel 1)
    if 'NO;READ;BEFORE;DIVERTER' in infotext:
        return "FEHLER: 'NO READ' an der Weiche"
    if 'Object/tray;removed;from;diverter' in infotext:
        return "FEHLER: Objekt/Wanne manuell entfernt"
    if 'Tray;ID:;NO;READ' in infotext:
        return "FEHLER: 'NO READ' Wanne nicht in Warteschlange"
        
    # 9. Queue Management
    if 'Deleting;tray;with;key' in infotext:
        return "[PLC] Wanne wird aus Warteschlange gelöscht"
    if 'Reallocating;tray' in infotext:
        return "[PLC] Wanne wird in Warteschlange neu zugewiesen"
        
    # 10. Gurt-Befehle
    if 'CLEARSCAN_BELT_FORWARD' in infotext:
        return "[PLC] Gurt fährt vorwärts"
    if 'CLEARSCAN_BELT_STOP' in infotext:
        return "[PLC] Gurt gestoppt"

    return None

def _find_iata_in_line(infotext):
    """ Versucht, eine IATA aus einer beliebigen Zeile zu extrahieren """
    if match := RE_RFID_READ.search(infotext):
        return normalize_rfid(match.group(1))
    elif match := RE_IATA_SIMPLE.search(infotext):
        return normalize_rfid(match.group(1))
    elif match := RE_IATA_EXAMINED.search(infotext):
        return normalize_rfid(match.group(1))
    elif match := RE_IATA_RESULT.search(infotext):
        return normalize_rfid(match.group(1))
    elif 'added;to;queue' in infotext:
         match_queue = re.search(r'RFID:;([\wL]+);added', infotext)
         if match_queue:
             return normalize_rfid(match_queue.group(1))
    return None

def parse_log(file_path, progress_callback=None):
    """
    Parst eine PlcLog.csv-Datei und erstellt eine DataFrame mit Klartext-Ereignissen
    basierend auf der "Start/End"-Logik (Reader 1 -> Belt Stop).
    """
    all_entries = []
    current_journey_events = []
    current_journey_id = 0
    current_iata = "N/A"
    is_tracking = False

    try:
        total_size = os.path.getsize(file_path)
        processed_size = 0
        
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                processed_size += len(line.encode('utf-8'))
                if progress_callback and processed_size % 100000 == 0: # Update alle ~100KB
                    progress = int((processed_size / total_size) * 100)
                    progress_callback(progress, f"Lese {os.path.basename(file_path)}...")

                if line.startswith(';'):
                    continue

                line_parts = line.split(',', 1) # Split only at the first comma
                if len(line_parts) != 2:
                    continue # Invalid format

                try:
                    # --- KORRIGIERT: (Problem 2 - Zeitzonen-Fehler) ---
                    timestamp_aware = pd.to_datetime(line_parts[0]) 
                    timestamp = timestamp_aware.tz_localize(None) # Konvertiere zu 'naive'
                    # --- ENDE KORREKTUR ---
                    
                    original_log = line.strip()
                    fields = line_parts[1].split(';')
                    
                    if len(fields) < 6:
                        continue
                        
                    infotext = ";".join(fields[5:]).strip()
                    
                except (pd.errors.ParserError, ValueError, IndexError) as e:
                    continue # Ungültige Zeile überspringen

                # --- NEUE STATE-MACHINE LOGIK (START/END) ---

                # 1. SUCHE NACH START (Reader 1)
                if not is_tracking:
                    # Bsp: ...RFID;READER;1;data;ready;-0;ID;000L0855;;;;;
                    if 'RFID;READER;1;data;ready' in infotext:
                        is_tracking = True
                        current_journey_id += 1
                        current_journey_events = []
                        
                        # Versuche, die IATA direkt aus der Startzeile zu holen
                        iata = _find_iata_in_line(infotext)
                        current_iata = iata if iata else "N/A" # Wird später gesucht
                
                # 2. VERFOLGE VORGANG (Tracking)
                if is_tracking:
                    # Versuche, die IATA zu finden, falls sie noch fehlt (z.B. bei NO_READ)
                    if current_iata == "N/A":
                        iata = _find_iata_in_line(infotext)
                        if iata:
                            current_iata = iata
                    
                    # Generiere Klartext
                    klartext = _get_klartext_for_event(infotext)
                    
                    # Speichere das Event
                    if klartext:
                        # Weise IATA zu (auch für Fehler)
                        iata_for_entry = "ERROR" if "FEHLER:" in klartext else current_iata
                        
                        current_journey_events.append({
                            "Timestamp": timestamp,
                            "IATA": iata_for_entry,
                            "Klartext": klartext,
                            "OriginalLog": original_log,
                            "JourneyID": current_journey_id
                        })

                    # 3. SUCHE NACH ENDE (Belt Stop)
                    if 'CLEARSCAN_BELT_STOP' in infotext:
                        is_tracking = False
                        
                        # Wenn wir Events haben, füge sie zur Gesamtliste hinzu
                        if current_journey_events:
                            # Stelle sicher, dass alle Events die korrekte IATA haben
                            final_iata = current_iata
                            if any("FEHLER:" in e['Klartext'] for e in current_journey_events):
                                final_iata = "ERROR"
                            
                            # --- KORRIGIERT (Problem 3 - Duplikate) ---
                            # De-dupliziere die Events *innerhalb* dieses Vorgangs
                            temp_df = pd.DataFrame(current_journey_events)
                            temp_df = temp_df.drop_duplicates(subset=["Klartext"])
                            # --- ENDE KORREKTUR ---

                            for _, event_row in temp_df.iterrows():
                                event = event_row.to_dict()
                                # Überschreibe IATA nur, wenn sie 'N/A' war oder ein Fehler auftrat
                                if event['IATA'] == "N/A" or final_iata == "ERROR":
                                    event['IATA'] = final_iata
                                all_entries.append(event)
                                
                        # Setze zurück
                        current_journey_events = []
                        current_iata = "N/A"
                
                # --- ENDE STATE-MACHINE LOGIK ---

    except Exception as e:
        print(f"Fehler beim Parsen von {file_path}: {e}")
        traceback.print_exc()

    if not all_entries:
        return pd.DataFrame(columns=["Timestamp", "IATA", "Klartext", "OriginalLog", "JourneyID"])

    df = pd.DataFrame(all_entries)
    
    # Entferne Duplikate (falls Start/End-Logik fehlschlägt)
    df = df.drop_duplicates(subset=["Timestamp", "IATA", "Klartext"])
    
    return df.sort_values(by="Timestamp").reset_index(drop=True)