# plclog_csv_parser.py
print("--- [V23-FIX] plclog_csv_parser.py wird geladen (NUR Fehler, Kein-UTC) ... ---")

import pandas as pd
import re
import pytz
import os
import traceback
from datetime import datetime

# Spaltennamen, wie sie in PlcLog_0.csv (File 2) gefunden wurden
ERROR_COL_TIMESTAMP = "Timestamp"
ERROR_COL_CLASSID = "ClassId"
ERROR_COL_INFOTEXT = "InfoText"

def find_header_row_error_log(file_path):
    """
    Findet die Header-Zeile, die ';Timestamp, CmpId, ClassId,' enthält.
    """
    target_header_keywords = [";Timestamp,", "CmpId,", "ClassId,", "ErrorId,", "InfoId,", "InfoText"]
    print(f"--- plclog_csv_parser: Suche nach Error-Header in {os.path.basename(file_path)} ---")
    
    try:
        with open(file_path, 'r', encoding='utf-8-sig', errors='ignore') as f:
            for i, line in enumerate(f):
                if all(keyword in line for keyword in target_header_keywords):
                    print(f"--- plclog_csv_parser: Error-Header in Zeile {i+1} gefunden.")
                    return i # Header-Zeile (0-basiert)
    except Exception:
        pass
    print(f"--- plclog_csv_parser: WARNUNG: Konnte Error-Header nicht finden.")
    return None

def parse_error_log(file_path, header_row_index, progress_callback):
    """Parst den 'Error'-Teil (File 2 Format) einer CSV."""
    filename = os.path.basename(file_path)
    errors_data = []
    
    try:
        with open(file_path, 'r', encoding='utf-8-sig', errors='ignore') as f:
            lines = f.readlines()

        total_lines = len(lines)
        if header_row_index is None or header_row_index >= total_lines:
            print(f"--- plclog_csv_parser: Konnte Error-Header in {filename} nicht finden.")
            return pd.DataFrame()

        header_line = lines[header_row_index].strip().split(',')
        # Entferne ';' und Leerzeichen aus Headern
        header_map = {col.strip().strip(';'): i for i, col in enumerate(header_line)}
        
        idx_ts = header_map.get(ERROR_COL_TIMESTAMP)
        idx_class = header_map.get(ERROR_COL_CLASSID)
        idx_info = header_map.get(ERROR_COL_INFOTEXT)

        if any(idx is None for idx in [idx_ts, idx_class, idx_info]):
            print(f"--- plclog_csv_parser: FEHLER: Erwartete Error-Spalten (Timestamp, ClassId, InfoText) nicht in {filename} gefunden.")
            print(f"--- Gefundene Header: {header_map.keys()}")
            return pd.DataFrame()

        for i, line in enumerate(lines[header_row_index + 1:]):
            if progress_callback and (i % 500 == 0):
                progress = int((i + 1) / (total_lines - header_row_index) * 100)
                progress_callback(progress, f"Analysiere Fehler in {filename}...")

            line = line.strip()
            if not line or line.startswith(';'): # Überspringe leere Zeilen oder Kommentare
                continue

            try:
                parts = line.split(',')
                if len(parts) <= max(idx_ts, idx_class, idx_info):
                    continue 

                ts_str = parts[idx_ts].strip(';')
                class_id_str = parts[idx_class].strip(';')
                # InfoText kann Kommas enthalten, nimm den Rest
                info_text_str = ",".join(parts[idx_info:]).strip('"')
                
                # --- KORREKTUR (Kein UTC) ---
                ts_naive = datetime.strptime(ts_str.split('Z')[0], '%Y-%m-%dT%H:%M:%S')
                
                class_id = int(class_id_str)
                source = "PLC-Error"
                klartext = None
                severity = "Info"

                if class_id == 2: # LOG_WARNING
                    severity = "Warning"
                    klartext = f"[PLC] Warnung: {info_text_str}"
                elif class_id == 4: # LOG_ERROR
                    severity = "Error"
                    klartext = f"[PLC] Fehler: {info_text_str}"
                elif class_id == 8: # LOG_EXCEPTION
                    severity = "Exception"
                    klartext = f"[PLC] Ausnahme: {info_text_str}"
                
                if klartext:
                    errors_data.append({
                        'Timestamp': ts_naive, # KORRIGIERT: ts_naive
                        'Source': source,
                        'Klartext': klartext,
                        'OriginalLog': line.strip(),
                        'IATA': "N/A", # Fehler-Logs haben keine IATA-Spalte
                        'BagID': "N/A",
                        'Device': "N/A",
                        'Severity': severity
                    })

            except Exception:
                continue
                
    except Exception as e:
        print(f"--- plclog_csv_parser: Kritischer Fehler beim manuellen Lesen der CSV: {e} ---")
        traceback.print_exc()
        return pd.DataFrame()

    print(f"--- plclog_csv_parser (Error-Modus): {len(errors_data)} Fehler-Einträge gefunden.")
    return pd.DataFrame(errors_data)


def parse_log(file_path, load_mode, progress_callback=None):
    """
    Hauptfunktion. Liest NUR Fehler-Logs (PlcLog_0.csv).
    Der 'load_mode' wird (vorerst) ignoriert, da dieser Parser nur Fehler kann.
    
    GIBT ZURÜCK:
    (journeys_df (immer leer), errors_df)
    """
    
    journeys_df = pd.DataFrame()
    errors_df = pd.DataFrame()

    # Dieser Parser ist NUR für Fehler (Button 4)
    if load_mode == 'errors':
        header_idx = find_header_row_error_log(file_path)
        if header_idx is not None:
            errors_df = parse_error_log(file_path, header_idx, progress_callback)
        else:
            print(f"--- plclog_csv_parser: Modus ist 'errors', aber kein Error-Header (z.B. ;Timestamp,) gefunden.")
    else:
        # Wenn Button 3 (journeys) fälschlicherweise diesen Parser aufruft
        print(f"--- plclog_csv_parser: Falscher Modus ('{load_mode}') an Fehler-Parser gesendet. Ignoriere.")
    
    return journeys_df, errors_df