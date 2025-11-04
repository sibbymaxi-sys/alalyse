# brava_log_parser.py
# HINWEIS: Zurückgesetzt auf V1. Diese Datei ist NICHT für CSV-Dateien.
print("--- [V15-FIX] brava_log_parser.py wird geladen (Original V1) ... ---")

import pandas as pd
import re
import os

def parse_brava_line(line):
    """
    Parst eine einzelne Zeile aus dem Brava-Log.
    Sucht nach Mustern, um Tray-ID und eine Klartext-Nachricht zu extrahieren.
    """
    tray_id_match = re.search(r'\[TRAY_ID=(\d+)\]', line)
    tray_id = tray_id_match.group(1) if tray_id_match else None
    
    klartext = line.strip()
    
    decision_match = re.search(r'Final Decision is (\w+)', line)
    if decision_match:
        klartext = f"Finale Entscheidung: {decision_match.group(1)}"
        
    return tray_id, klartext

def parse_log(file_path, progress_callback=None):
    """
    Liest eine gesamte Brava-Log-Datei (NICHT CSV) und wandelt sie in einen DataFrame um.
    
    GIBT ZURÜCK:
    (df, None) - Gibt ein Tupel zurück, um mit dem neuen plclog_csv_parser kompatibel zu sein.
                 Der zweite Wert (Errors) ist immer None.
    """
    records = []
    filename = os.path.basename(file_path)
    
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        
        total_lines = len(lines)
        for i, line in enumerate(lines):
            if progress_callback and i % 100 == 0:
                progress_callback(int((i / total_lines) * 100), f"Analysiere {filename}...")

            timestamp_match = re.match(r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z)', line)
            if not timestamp_match:
                continue
                
            timestamp = pd.to_datetime(timestamp_match.group(1)) # Erzeugt TZ-aware (UTC)
            infotext = line[timestamp_match.end(1):].strip()
            
            tray_id, klartext = parse_brava_line(infotext)
            
            records.append({
                "Timestamp": timestamp,
                "Source": "BRAVA", # Quelle ist BRAVA
                "IATA": tray_id,
                "Klartext": klartext,
                "OriginalLog": line.strip()
            })
            
        df = pd.DataFrame(records)
        print(f"--- brava_log_parser: {len(df)} BRAVA-Einträge gefunden.")
        # Gebe (df, None) zurück, um kompatibel zu sein
        return df, pd.DataFrame()
        
    except Exception as e:
        print(f"Fehler beim Parsen von {filename}: {e}")
        return pd.DataFrame(), pd.DataFrame()