# plclog_journey_parser.py
print("--- [V22-FIX] plclog_journey_parser.py wird geladen (NEUER Parser für PlcLog.csv) ... ---")

import re
import pandas as pd
from datetime import datetime
import os

# --- MUSTER (basierend auf deinen Beispielen) ---

# 1. Zeitstempel (immer am Anfang)
TS_PATTERN = re.compile(r"^([\d\-]+T[\d:]+)") # Akzeptiert Z, aber ignoriert es

# 2. IATA / Wannen-Nummer
#    Sucht nach verschiedenen Formaten wie 'ID 000L0131', 'ID: 131', 'tray : 000L0131'
IATA_PATTERN = re.compile(r"ID\s*:?\s*(\S+)|tray\s*:\s*(\S+)|RFID:\s*(\S+)")

# 3. Klartext-Ereignisse
EVENT_PATTERNS = [
    (re.compile(r"RFID\s+READER\s+(\d+)\s+data\s+ready\s+-0\s+ID\s+(\S+)"),
     lambda m: (f"[PLC-RFID] Wanne {m.group(2)} an Leser {m.group(1)} erkannt.", m.group(2))),
    
    (re.compile(r"NEW_TRAY_DIVERTER\s+ID:\s*(\d+)"),
     lambda m: (f"[PLC] Wanne {m.group(1)} an Weiche angemeldet.", m.group(1))),
     
    (re.compile(r"INFO_RECEIVED_DVERTER\s+from\s+scanner"),
     lambda m: ("[PLC] Scanner-Info für Weiche empfangen.", None)),
     
    (re.compile(r"CLEARSCAN_BELT_FORWARD"),
     lambda m: ("[PLC] ClearScan-Band START.", None)),
     
    (re.compile(r"CLEARSCAN_BELT_STOP"),
     lambda m: ("[PLC] ClearScan-Band STOPP.", None)),
     
    (re.compile(r"Diverter\s+reject\s+-0\s+Step\s+(\d+)\s+(.*)"),
     lambda m: (f"[PLC-Weiche-Reject] Schritt {m.group(1)}: {m.group(2).strip()}", None)),
     
    (re.compile(r"Diverter\s+clear\s+-0\s+Step\s+(\d+)\s+(.*)"),
     lambda m: (f"[PLC-Weiche-Clear] Schritt {m.group(1)}: {m.group(2).strip()}", None)),
     
    (re.compile(r"NEW_INFO_RFID\s+from\s+scanner\s+-0\s+RFID\s+EXAMINED:\s*(\d+)\s+-0\s+Operator\s+decision:\s*(\d)"),
     lambda m: (f"[PLC] Scanner-Info: Operator-Entscheidung für Wanne {m.group(1)} ist {'CLEAR' if m.group(2) == '1' else 'REJECT'}.", m.group(1))),
     
    (re.compile(r"Result\s+(CLEAR|REJECT)\s+for\s+tray\s*:\s*(\S+)"),
     lambda m: (f"[PLC] Finale Entscheidung für Wanne {m.group(2)}: {m.group(1)}.", m.group(2))),
     
    (re.compile(r"Deleting\s+tray\s+with\s+key(\d+)"),
     lambda m: (f"[PLC] Wanne (Key {m.group(1)}) wird aus System gelöscht.", None)),

    (re.compile(r"Tray\s+with\s+RFID:\s*(\S+)\s+added\s+to\s+queue\s+with\s+key:\s*(\d+)"),
     lambda m: (f"[PLC] Wanne {m.group(1)} (Key {m.group(2)}) zur Warteschlange hinzugefügt.", m.group(1))),
     
    (re.compile(r"New\s+tray\s+INFEED\s+-0\s+ID:\s*(\S+)"),
     lambda m: (f"[PLC] Neue Wanne am Infeed: {m.group(1)}", m.group(1))),

    (re.compile(r"INFO_RECEIVED_INFEED\s+ok"),
     lambda m: ("[PLC] Infeed-Info von Scanner empfangen.", None)),

    (re.compile(r"FT\s+Module\s+before\s+(diverter|scanner)\s+=\s+(TRUE|FALSE)"),
     lambda m: (f"[PLC-Sensor] Sensor vor '{m.group(1)}' ist {'Aktiv' if m.group(2) == 'TRUE' else 'Inaktiv'}.", None)),
     
    (re.compile(r"HMI\s+Alarms\s+reset\s+=\s+(TRUE|FALSE)"),
     lambda m: (f"[PLC-HMI] Alarm-Reset-Signal: {m.group(1)}", None))
]

def parse_log(file_path, progress_callback=None):
    """
    Liest eine SPS-Journey-Log-Datei (PlcLog.csv) Zeile für Zeile.
    GIBT ZURÜCK: Einen DataFrame
    """
    records = []
    filename = os.path.basename(file_path)
    
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        
        total_lines = len(lines)
        if total_lines == 0:
            return pd.DataFrame()

        for i, line in enumerate(lines):
            if progress_callback and (i % 100 == 0 or i == total_lines - 1):
                progress_callback(int((i + 1) / total_lines * 100), f"Analysiere {filename}...")

            line = line.strip()
            if not line or line.startswith(';'): # Ignoriert Header und Kommentare
                continue

            ts_match = TS_PATTERN.search(line)
            if not ts_match:
                continue
            
            try:
                # Zeitstempel extrahieren (Originalzeit, kein UTC)
                ts_str = ts_match.group(1)
                dt_object = datetime.strptime(ts_str, '%Y-%m-%dT%H:%M:%S')
            except ValueError:
                continue
            
            klartext = None
            iata = None

            # Teste alle definierten Muster
            for pattern, handler in EVENT_PATTERNS:
                if m := pattern.search(line):
                    klartext, iata_match = handler(m)
                    if iata_match:
                        # Bereinige IATA (z.B. "131" oder "000L0131")
                        iata = iata_match.strip().strip(':')
                    break # Nimm das erste Muster, das passt
            
            # Wenn kein Muster gepasst hat, versuche zumindest IATA zu finden
            if klartext is None:
                iata_match = IATA_PATTERN.search(line)
                if iata_match:
                    iata = iata_match.group(1) or iata_match.group(2) or iata_match.group(3)
                    if iata:
                        iata = iata.strip().strip(':')
                        klartext = f"[PLC] Unbekannter Eintrag (IATA: {iata})"
                
            if klartext: # Nur Zeilen hinzufügen, die wir übersetzen konnten
                records.append({
                    "Timestamp": dt_object, 
                    "Klartext": klartext, 
                    "OriginalLog": line,
                    "IATA": iata if iata else "N/A",
                    "Source": "PLC"
                })
    
    except Exception as e:
        print(f"--- FEHLER beim Parsen von {filename}: {e}")
        return pd.DataFrame()
        
    df = pd.DataFrame(records)
    # Entferne Duplikate, die durch mehrfaches Lesen (z.B. Reader 3 & 4) entstehen
    df = df.drop_duplicates(subset=['Timestamp', 'Klartext']) 
    print(f"--- plclog_journey_parser: {len(df)} SPS-Journey-Einträge gefunden.")
    return df