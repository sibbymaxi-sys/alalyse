# log_parser.py
import re
import pandas as pd
from datetime import datetime
import os

BAG_ID_PATTERN = re.compile(r'\"(0\d{9})\"') 
TS_PATTERN = re.compile(r"^([A-Z][a-z]{2}\s+[A-Z][a-z]{2}\s+\d{2}\s+\d{2}:\d{2}:\d{2})\.\d+")
IATA_PATTERN = re.compile(r'(?:with IATA|found disposition for|RFID)\s*=\s*\"([^\"]+)\"|\bRFID\s+([0-9]{4})\b')

# --- ERWEITERTE MUSTER FÜR ALLE RELEVANTEN LOG-EINTRÄGE ---
CREATE_BAG_PATTERN = re.compile(r'CreateNewBag')
ASSIGN_ALGO_PATTERN = re.compile(r'AssignAlgorithms.*assigning (eds-\d\.\d\.\d+|ltr algo object)')
ASSOCIATED_IATA_PATTERN = re.compile(r'Associated.*with IATA=\"([^\"]+)\"')
MARK_ALGO_DONE_PATTERN = re.compile(r'BagIoHandler::MarkAlgoDone\[([a-z0-9\.-]+)\]')
MACHINE_DISP_PATTERN = re.compile(r'SetDisposition\[(MACHINE_OBJECT|MACHINE_THREAT)\].*disp=\"(ALARM|CLEAR)\"')
OPERATOR_DISP_PATTERN = re.compile(r'SetDisposition\[OSR\].*disp=\"(CLEAR|ALARM)\".*op=\"([a-zA-Z0-9_]+)\"')
FINISHED_PATTERN = re.compile(r'Finished\(')
SAVED_PATTERN = re.compile(r'Ok:Saved')
OMS_LOOKUP_ENTERING_PATTERN = re.compile(r"lookUpBagDisposition.*Entering")
OMS_LOOKUP_FOUND_PATTERN = re.compile(r"lookUpBagDisposition.*found disposition for\s+\"([^\"]+)\"")
OMS_RFID_FOUND_PATTERN = re.compile(r"RFID FOUND -.*HIGHALERT:\s+EDS:\s+(\d+)\s+LTR:\s+(\d+)")
OMS_FINAL_CMD_PATTERN = re.compile(r"writing to PLC diverter cmd:\s+(\d)")
OMS_GENERIC_CALL_PATTERN = re.compile(r"\[OMS:\d+:\w+\]:\s(?:virtual void|void|virtual bool|int)\s+([\w:]+)\(")

def map_disposition_to_text(code):
    return "**Freigabe (CLEAR)**" if str(code) == '1' else "**Alarm (ALARM)**"

def parse_line_to_klartext(line, source, bag_id, iata):
    ident = iata if iata not in ["N/A", "NO_READ"] else bag_id
    prefix = f"[{source}]"

    if m := CREATE_BAG_PATTERN.search(line): return f"{prefix} Bag {bag_id} im System angelegt."
    if m := ASSIGN_ALGO_PATTERN.search(line): return f"{prefix} Analyse-Algorithmus '{m.group(1)}' wird zugewiesen."
    if m := ASSOCIATED_IATA_PATTERN.search(line): return f"{prefix} Bag {bag_id} wurde Wanne **{m.group(1)}** zugeordnet."
    if m := MARK_ALGO_DONE_PATTERN.search(line): return f"{prefix} Analyse durch Algorithmus '{m.group(1)}' abgeschlossen."
    if m := MACHINE_DISP_PATTERN.search(line):
        sys, disp = m.groups(); sys_name = "LTR" if sys == "MACHINE_OBJECT" else "EDS"
        return f"{prefix} Maschinelle Entscheidung ({sys_name}): **{disp}**"
    if m := OPERATOR_DISP_PATTERN.search(line):
        disp, op = m.groups(); return f"{prefix} Finale Operator-Entscheidung von '{op}': **{disp}**"
    if FINISHED_PATTERN.search(line): return f"{prefix} Bag {bag_id} Verarbeitung im Scanner abgeschlossen."
    if SAVED_PATTERN.search(line): return f"{prefix} Bild für Wanne {ident} wurde gespeichert."
    if OMS_LOOKUP_ENTERING_PATTERN.search(line): return f"{prefix} Sucht nach finaler Entscheidung in der Datenbank..."
    if m := OMS_LOOKUP_FOUND_PATTERN.search(line): return f"{prefix} Finale Entscheidung für Wanne **{m.group(1)}** in Datenbank gefunden."
    if m := OMS_RFID_FOUND_PATTERN.search(line):
        eds = "**Aktiv**" if m.group(1) == '1' else "Inaktiv"
        ltr = "**Aktiv**" if m.group(2) != '0' else "Inaktiv"
        return f"{prefix} Wanne an Weiche erkannt. Status-Prüfung: EDS-Alarm={eds}, LTR-Alarm={ltr}."
    if m := OMS_FINAL_CMD_PATTERN.search(line): return f"{prefix} **Finaler Befehl an Förderanlage gesendet: {map_disposition_to_text(m.group(1))}**"
    if m := OMS_GENERIC_CALL_PATTERN.search(line): return f"{prefix} Systemaufruf: {m.group(1)}"
    
    return None # Ignoriere alle anderen, sich wiederholenden Zeilen

def parse_log_file(file_path, update_progress=None):
    log_records = []; current_year = datetime.now().year; last_month = None
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()
    for i, line in enumerate(lines):
        if update_progress and (i % 500 == 0 or i == len(lines) - 1):
            update_progress(int((i + 1) / len(lines) * 100), os.path.basename(file_path))
        
        if not (ts_match := TS_PATTERN.search(line)): continue
        try:
            dt_no_year = datetime.strptime(ts_match.group(1), "%a %b %d %H:%M:%S")
            year = current_year
            if last_month and dt_no_year.month == 1 and last_month == 12: year -= 1
            dt_object = dt_no_year.replace(year=year); last_month = dt_object.month
        except ValueError: continue

        bag_id_match = BAG_ID_PATTERN.search(line)
        iata_match = IATA_PATTERN.search(line)
        bag_id = bag_id_match.group(1) if bag_id_match else "N/A"
        iata = (iata_match.group(1) or iata_match.group(2)) if iata_match else "N/A"
        if bag_id == "N/A" and iata == "N/A": continue
        
        source = "OMS" if "[OMS:" in line else "Scanner"
        if klartext := parse_line_to_klartext(line, source, bag_id, iata):
            log_records.append({"Timestamp": dt_object, "BagID": bag_id, "IATA": iata, "Source": source, "Klartext": klartext, "OriginalLog": line.strip()})
    return pd.DataFrame(log_records)