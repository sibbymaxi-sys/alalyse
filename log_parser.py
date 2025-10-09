# log_parser.py
import re
import pandas as pd
from datetime import datetime
import os
from brava_log_parser import parse_log as parse_brava_log

TS_PATTERN = re.compile(r"^([A-Z][a-z]{2}\s+[A-Z][a-z]{2}\s+\d{2}\s+\d{2}:\d{2}:\d{2})\.\d+")
BAG_ID_PATTERN = re.compile(r'\"(0\d{9})\"') 
IATA_PATTERN = re.compile(r'(?:with IATA|found disposition for|RFID|tric)\s*=\s*\"([^\"]+)\"|\bRFID\s+([0-9]{4})\b', re.IGNORECASE)

# Scanner-Muster
CREATE_BAG_PATTERN = re.compile(r'CreateNewBag')
ASSIGN_ALGO_PATTERN = re.compile(r'AssignAlgorithms.*assigning (eds-\d\.\d\.\d+|ltr algo object)')
ASSOCIATED_IATA_PATTERN = re.compile(r'Associated.*with IATA=\"([^\"]+)\"')
MARK_ALGO_DONE_PATTERN = re.compile(r'BagIoHandler::MarkAlgoDone\[([a-z0-9\.-]+)\]')
MACHINE_DISP_PATTERN = re.compile(r'SetDisposition\[(MACHINE_OBJECT|MACHINE_THREAT)\].*disp=\"(ALARM|CLEAR)\"')
OPERATOR_DISP_PATTERN = re.compile(r'SetDisposition\[OSR\].*disp=\"(CLEAR|ALARM)\".*op=\"([a-zA-Z0-9_]+)\"')
# NEU: Muster für die Nachkontrolle (Operator 3/4)
OPERATOR_DISP_LATE_PATTERN = re.compile(r'SetOperatorDisposition.*operator=([a-zA-Z0-9_]+),\s*disposition=(\d)')
SECURITY_RULE_PATTERN = re.compile(r'Security rule for this bag is now (\w+)')
FINISHED_PATTERN = re.compile(r'Finished\(')
SAVED_PATTERN = re.compile(r'Ok:Saved')

# OMS-Muster
OMS_LOOKUP_ENTERING_PATTERN = re.compile(r"lookUpBagDisposition.*Entering")
OMS_LOOKUP_FOUND_PATTERN = re.compile(r"lookUpBagDisposition.*found disposition for\s+\"([^\"]+)\"")
OMS_RFID_FOUND_PATTERN = re.compile(r"RFID FOUND -.*HIGHALERT:\s+EDS:\s+(\d+)\s+LTR:\s+(\d+)")
OMS_SET_FINAL_DISP_PATTERN = re.compile(r"setFinalBagDisposition.*final disposition is (\d+)")
OMS_SLOT_SEND_TRIC_MSG = re.compile(r"MacHInterface::slotSendTricBagDispositionMsg")
OMS_FINAL_CMD_PATTERN = re.compile(r"writing to PLC diverter cmd:\s+(\d)")
OMS_GENERIC_CALL_PATTERN = re.compile(r"\[OMS:\d+:\w+\]:\s(?:virtual void|void|virtual bool|int)\s+([\w:]+)\(")

def map_disposition_to_text(code):
    return "**Freigabe (CLEAR)**" if str(code) == '1' else "**Alarm (ALARM)**"

def parse_line_to_klartext(line, source, bag_id, iata):
    ident = iata if iata not in ["N/A", "NO_READ"] else bag_id
    prefix = f"[{source}]"

    # --- Scanner-Logik ---
    if m := CREATE_BAG_PATTERN.search(line): return f"{prefix} Gepäckstück **{bag_id}** wird im System angelegt."
    if m := ASSIGN_ALGO_PATTERN.search(line): return f"{prefix} Analyse-Algorithmus '{m.group(1)}' wird zugewiesen."
    if m := ASSOCIATED_IATA_PATTERN.search(line): return f"{prefix} Gepäckstück {bag_id} wurde Wanne **{m.group(1)}** zugeordnet."
    if m := MARK_ALGO_DONE_PATTERN.search(line): return f"{prefix} Analyse durch Algorithmus '{m.group(1)}' ist abgeschlossen."
    if m := MACHINE_DISP_PATTERN.search(line):
        sys, disp = m.groups(); sys_name = "LTR" if sys == "MACHINE_OBJECT" else "EDS"
        return f"{prefix} Maschinelle Entscheidung ({sys_name}): **{disp}**"
    if m := OPERATOR_DISP_PATTERN.search(line):
        disp, op = m.groups(); return f"{prefix} Finale Operator-Entscheidung von '{op}': **{disp}**"
    # NEU: Logik zur Erkennung der Nachkontrolle
    if m := OPERATOR_DISP_LATE_PATTERN.search(line):
        op, disp_code = m.groups()
        disp_text = "CLEAR" if disp_code == '1' else "ALARM"
        return f"{prefix} Späte Operator-Entscheidung (Nachkontrolle) von '{op}': **{disp_text}**"
    if m := SECURITY_RULE_PATTERN.search(line): return f"{prefix} Sicherheitsregel für dieses Gepäckstück ist jetzt: **{m.group(1)}**."
    if FINISHED_PATTERN.search(line): return f"{prefix} Verarbeitung für Gepäckstück **{bag_id}** im Scanner beendet."
    if SAVED_PATTERN.search(line): return f"{prefix} Bilddaten für Wanne **{ident}** wurden gespeichert."

    # --- OMS-Logik ---
    if OMS_LOOKUP_ENTERING_PATTERN.search(line): return f"{prefix} Sucht nach finaler Entscheidung für Wanne **{ident}** in der Datenbank."
    if m := OMS_LOOKUP_FOUND_PATTERN.search(line): return f"{prefix} Finale Entscheidung für Wanne **{m.group(1)}** in Datenbank gefunden."
    if m := OMS_RFID_FOUND_PATTERN.search(line):
        eds_status = "**Aktiv**" if m.group(1) == '1' else "Inaktiv"; ltr_status = "**Aktiv**" if m.group(2) != '0' else "Inaktiv"
        return f"{prefix} Wanne **{ident}** an Weiche erkannt. Status-Prüfung: EDS-Alarm={eds_status}, LTR-Alarm={ltr_status}."
    if m := OMS_SET_FINAL_DISP_PATTERN.search(line): return f"{prefix} Interne, finale Entscheidung für Wanne **{ident}** wird gesetzt auf: {map_disposition_to_text(m.group(1))}"
    if OMS_SLOT_SEND_TRIC_MSG.search(line): return f"{prefix} System bereitet den Versand der finalen Entscheidung für Wanne **{ident}** an die Anlage vor."
    if m := OMS_FINAL_CMD_PATTERN.search(line): return f"{prefix} **Finaler Befehl an Förderanlage gesendet: {map_disposition_to_text(m.group(1))}**"
    if m := OMS_GENERIC_CALL_PATTERN.search(line): return f"{prefix} Technischer Systemaufruf: {m.group(1)}"
    return None


   #----BREVA-----

def brava_klartext_mapping(eintrag):
    # Beispiel: Mapping typischer BRAVA/PLC-Events ins Deutsche
    if "Diverter reject" in eintrag:
        return "Ausschleuser zurückgewiesen: " + eintrag
    if "Tray with RFID" in eintrag:
        return "Wanne erkannt: " + eintrag
    if "CLEAR" in eintrag:
        return "Frei: " + eintrag
    if "REJECT" in eintrag:
        return "Abgewiesen: " + eintrag
    if "SEND TO" in eintrag:
        return "Finaler Befehl an PLC: " + eintrag
    return eintrag

def parse_log_file(file_path, progress_callback=None):
    # --- Integration des BRAVA-Parsers ---
    if file_path.endswith("PlcLog.csv") or "brava" in file_path.lower():
        df = parse_brava_log(file_path)
        # Mapping/Übersetzung in Klartext
        df["Klartext"] = df["Ereignis"].apply(brava_klartext_mapping)
        # Stelle sicher, dass die DataFrame-Spalten zu deiner Pipeline passen
        # z.B. Timestamp, BagID/TrayID, Klartext, Source/Quelle, etc.
        df["Source"] = "BRAVA"
        df["BagID"] = df.get("TrayID", "")  # oder TrayID → BagID
        return df

def parse_log_file(file_path, update_progress=None):
    # ... (Rest der Funktion bleibt unverändert)
    log_records = []; current_year = datetime.now().year; last_month = None
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f: lines = f.readlines()
    total_lines = len(lines)
    for i, line in enumerate(lines):
        if update_progress and (i % 500 == 0 or i == total_lines - 1):
            progress = int((i + 1) / total_lines * 100); update_progress(progress, os.path.basename(file_path))
        ts_match = TS_PATTERN.search(line)
        if not ts_match: continue
        try:
            dt_no_year = datetime.strptime(ts_match.group(1), "%a %b %d %H:%M:%S")
            year_to_use = current_year
            if last_month and dt_no_year.month == 1 and last_month == 12: year_to_use -= 1
            dt_object = dt_no_year.replace(year=year_to_use); last_month = dt_object.month
        except ValueError: continue
        bag_id_match = BAG_ID_PATTERN.search(line); iata_match = IATA_PATTERN.search(line)
        bag_id = bag_id_match.group(1) if bag_id_match else "N/A"
        iata = (iata_match.group(1) or iata_match.group(2)) if iata_match else "N/A"
        if bag_id == "N/A" and iata == "N/A": continue
        source = "OMS" if "[OMS:" in line else "Scanner"
        klartext = parse_line_to_klartext(line, source, bag_id, iata)
        if klartext:
            log_records.append({"Timestamp": dt_object, "BagID": bag_id, "IATA": iata, "Source": source, "Klartext": klartext, "OriginalLog": line.strip()})
    return pd.DataFrame(log_records)