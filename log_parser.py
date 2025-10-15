# log_parser.py
import re
import pandas as pd
from datetime import datetime
import os
import traceback
from tkinter import messagebox

# Externe Parser importieren
from brava_log_parser import parse_log as parse_external_brava_log

try:
    from error_definitions import TD_CODES, SD_CODES
except ImportError:
    TD_CODES, SD_CODES = {}, {}

# === Regex-Muster für alle bekannten Log-Typen ===

# --- Zeitstempel ---
TS_PATTERN_GENERIC = re.compile(r"^(\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2})")
TS_PATTERN_LEGACY = re.compile(r"^([A-Z][a-z]{2}\s+[A-Z][a-z]{2}\s+\d{2}\s+\d{2}:\d{2}:\d{2})")

# --- IDs ---
BAG_ID_PATTERN = re.compile(r'\"(0\d{9})\"')
IATA_RFID_PATTERN = re.compile(
    r"IATA:\s*([\w\d\-]+)"          # Fall 1: IATA: 000L0453 (ohne Anführungszeichen)
    r"|with IATA=\"([^\"]+)\""      # Fall 2: with IATA="1234"
    r"|L='([^']+)'"                 # Fall 3: L='000L0453'
    r"|Tray with RFID:\s*([\w\d\-]+)" # Fall 4: Tray with RFID: 000L0600
    r"|\bRFID:\s*(\d{3,4})\b"       # Fall 5: RFID: 0162
    r"|\bRFID\s+\"(\d{3,4})\""      # Fall 6: RFID "0146"
    , re.IGNORECASE)
# KORRIGIERT: Fehlendes Muster hinzugefügt
DEVICE_ID_PATTERN = re.compile(r'@(CCT\d{4})')

# --- Umfassende Musterliste für Klartext ---
CREATE_BAG_PATTERN = re.compile(r'CreateNewBag')
ASSOCIATED_IATA_PATTERN = re.compile(r'Associated.*with IATA=\"([^\"]+)\"')
MACHINE_DISP_PATTERN = re.compile(r'SetDisposition\[(MACHINE_OBJECT|MACHINE_THREAT)\].*disp=\"(ALARM|CLEAR)\"')
OPERATOR_DISP_PATTERN = re.compile(r'SetDisposition\[OSR\].*disp=\"(CLEAR|ALARM)\".*op=\"([a-zA-Z0-9_]+)\"')
OPERATOR_DISP_LATE_PATTERN = re.compile(r'SetOperatorDisposition.*operator=([a-zA-Z0-9_]+),\s*disposition=(\d)')
FINAL_DECISION_PATTERN = re.compile(r'Final decision:\s*(\w+)', re.IGNORECASE)
IMAGE_ACQ_PATTERN = re.compile(r"Image acquisition started", re.IGNORECASE)
XRAY_ANALYSIS_PATTERN = re.compile(r"X-Ray analysis complete", re.IGNORECASE)
ENTERING_STATE_PATTERN = re.compile(r"Entering state '([\w_]+)'", re.IGNORECASE)
SECURITY_RULE_PATTERN = re.compile(r'Security rule for this bag is now (\w+)')
FINISHED_PATTERN = re.compile(r'Finished\(')
SAVED_PATTERN = re.compile(r'Ok:Saved')
MARK_ALGO_DONE_PATTERN = re.compile(r'BagIoHandler::MarkAlgoDone\[([a-z0-9\.-]+)\]')
ASSIGN_ALGO_PATTERN = re.compile(r'AssignAlgorithms.*assigning (eds-\d\.\d\.\d+|ltr algo object)')
PLC_EVENT_RECEIVED_PATTERN = re.compile(r"TranslatePlcEvent\] Received Event", re.IGNORECASE)
CCT_MSG_PATTERN = re.compile(r"CCT Msg Received: (\w+)", re.IGNORECASE)
BSM_SENT_PATTERN = re.compile(r"BSM Sent to BHS", re.IGNORECASE)
DB_INSERT_PATTERN = re.compile(r"Bag Info Inserted", re.IGNORECASE)
DB_INSERT_FAILED_PATTERN = re.compile(r"Insert failed", re.IGNORECASE)
COMPONENT_NOT_CONNECTED_PATTERN = re.compile(r"is not connected, can't process", re.IGNORECASE)
EXCEPTION_PATTERN = re.compile(r"Exception caught", re.IGNORECASE)
WARNING_PATTERN = re.compile(r"WARNING:", re.IGNORECASE)
IQTK_FAIL_PATTERN = re.compile(r"FINAL RESULT: FAIL", re.IGNORECASE)
DPP_BAG_START_PATTERN = re.compile(r"BAG START", re.IGNORECASE)
DPP_BAG_END_PATTERN = re.compile(r"BAG END", re.IGNORECASE)
DCS_DMA_FULL_PATTERN = re.compile(r"DMA RX Data Queue.*is full", re.IGNORECASE)
RECON_FAIL_PATTERN = re.compile(r"ReconClient: fail on processwrites", re.IGNORECASE)
BAD_TARGET_PATTERN = re.compile(r"Error: bad target", re.IGNORECASE)
OMS_DISPO_LPN_PATTERN = re.compile(r"Found disposition for LPN '(\w+)'")
OMS_PEC_STATUS_PATTERN = re.compile(r"slotSendPECStatus.*from PE \[ (\d+) \] with state \[ (true|false) \]", re.IGNORECASE)
OMS_DIVERTER_ACTION_PATTERN = re.compile(r"slotDiverterAction.*Looking for bag:\s+(\d+)", re.IGNORECASE)
OMS_SET_FINAL_DISP_PATTERN = re.compile(r"setFinalBagDisposition.*final disposition is (\d+)")
OMS_LOOKUP_ENTERING_PATTERN = re.compile(r"lookUpBagDisposition.*Entering")
OMS_LOOKUP_FOUND_PATTERN = re.compile(r"lookUpBagDisposition.*found disposition for\s+\"([^\"]+)\"")
OMS_RFID_FOUND_PATTERN = re.compile(r"RFID FOUND -.*HIGHALERT:\s+EDS:\s+(\d+)\s+LTR:\s+(\d+)")
OMS_SLOT_SEND_TRIC_MSG = re.compile(r"MacHInterface::slotSendTricBagDispositionMsg")
OMS_FINAL_CMD_PATTERN = re.compile(r"writing to PLC diverter cmd:\s+(\d)")
OMS_GENERIC_CALL_PATTERN = re.compile(r"\[OMS:\d+:\w+\]:\s(?:virtual void|void|virtual bool|int)\s+([\w:]+)\(")
PLC_TRACKING_DECISION_PATTERN = re.compile(r"Tracking Decision, Bag \w+, TD (\d+)", re.IGNORECASE)
PLC_SORTING_DECISION_PATTERN = re.compile(r"Sorting Decision, Bag \w+, SD (\d+)", re.IGNORECASE)
PLC_PHOTOCELL_PATTERN = re.compile(r"(IBDR|XBDP) PS:")
BREVA_DIVERTER_REJECT = re.compile(r"Diverter reject: .* IS NOT DIVERTED")
BREVA_SEND_TO_OSR = re.compile(r"SEND TO OSR ([\w\d\-]+)")
BREVA_TRAY_RFID = re.compile(r"Tray with RFID: ([\w\d\-]+)")
BREVA_RESULT_CLEAR = re.compile(r"Result CLEAR for tray ([\w\d\-]+)")
BREVA_STATION_WARNING = re.compile(r"!!!! Warning: Station '([\w\d\-]+)'")

def _parse_line_to_klartext(line, source, bag_id, iata):
    ident = iata if iata and iata not in ["N/A", "NO_READ"] else bag_id
    prefix = f"[{source}]"
    if DCS_DMA_FULL_PATTERN.search(line): return f"{prefix} KRITISCHER HARDWARE-FEHLER: Daten-Warteschlange vom Detektor ist voll."
    if DB_INSERT_FAILED_PATTERN.search(line): return f"{prefix} KRITISCHER FEHLER: Datenbank-Schreibfehler."
    if COMPONENT_NOT_CONNECTED_PATTERN.search(line): return f"{prefix} KRITISCHER FEHLER: Eine Komponente ist nicht verbunden."
    if IQTK_FAIL_PATTERN.search(line): return f"{prefix} KRITISCHER FEHLER: Bildqualitätstest (IQTK) fehlgeschlagen."
    if RECON_FAIL_PATTERN.search(line): return f"{prefix} KRITISCHER FEHLER: Bild-Speicherung fehlgeschlagen."
    if BAD_TARGET_PATTERN.search(line): return f"{prefix} KRITISCHER FEHLER: Kommunikation zwischen Software-Modulen gestört."
    if EXCEPTION_PATTERN.search(line): return f"{prefix} KRITISCHER FEHLER: Software-Exception aufgetreten."
    if WARNING_PATTERN.search(line): return f"{prefix} WARNUNG: {line.split('WARNING:', 1)[-1].strip()}"
    if BREVA_DIVERTER_REJECT.search(line): return f"{prefix} KRITISCHER FEHLER: Weiche hat nicht wie befohlen sortiert!"
    if m := CREATE_BAG_PATTERN.search(line): return f"{prefix} Gepäckstück **{bag_id}** wird im System angelegt."
    if m := ASSIGN_ALGO_PATTERN.search(line): return f"{prefix} Analyse-Algorithmus '{m.group(1)}' wird zugewiesen."
    if m := ASSOCIATED_IATA_PATTERN.search(line): return f"{prefix} Gepäckstück {bag_id} wurde Wanne **{m.group(1)}** zugeordnet."
    if IMAGE_ACQ_PATTERN.search(line): return f"{prefix} Start der Bildaufnahme."
    if XRAY_ANALYSIS_PATTERN.search(line): return f"{prefix} Röntgen-Analyse abgeschlossen."
    if m := MARK_ALGO_DONE_PATTERN.search(line): return f"{prefix} Analyse durch Algorithmus '{m.group(1)}' ist abgeschlossen."
    if m := MACHINE_DISP_PATTERN.search(line):
        sys, disp = m.groups(); return f"{prefix} Maschinelle Entscheidung ({sys}): **{disp}**"
    if m := SECURITY_RULE_PATTERN.search(line): return f"{prefix} Sicherheitsregel ist jetzt: **{m.group(1)}**."
    if m := OPERATOR_DISP_PATTERN.search(line):
        disp, op = m.groups(); return f"{prefix} Finale Operator-Entscheidung von '{op}': **{disp}**"
    if m := OPERATOR_DISP_LATE_PATTERN.search(line):
        op, disp_code = m.groups(); disp_text = "CLEAR" if disp_code == '1' else "ALARM"
        return f"{prefix} Späte Operator-Entscheidung (Nachkontrolle) von '{op}': **{disp_text}**"
    if m := FINAL_DECISION_PATTERN.search(line): return f"{prefix} Finale Systementscheidung ist **{m.group(1)}**."
    if m := ENTERING_STATE_PATTERN.search(line): return f"{prefix} Status: '{m.group(1)}'"
    if SAVED_PATTERN.search(line): return f"{prefix} Bilddaten für Wanne **{ident}** wurden gespeichert."
    if FINISHED_PATTERN.search(line): return f"{prefix} Verarbeitung im Scanner beendet."
    if PLC_EVENT_RECEIVED_PATTERN.search(line): return f"{prefix} Info: Ereignis von der SPS empfangen."
    if m := CCT_MSG_PATTERN.search(line): return f"{prefix} Info: Signal vom Bild-Server (CCT): {m.group(1)}"
    if BSM_SENT_PATTERN.search(line): return f"{prefix} Info: Routing-Info (BSM) an Leitsystem (BHS) gesendet."
    if DB_INSERT_PATTERN.search(line): return f"{prefix} Info: Gepäckdaten in Datenbank geschrieben."
    if DPP_BAG_START_PATTERN.search(line): return f"{prefix} Info: Start der Bildverarbeitung (DPP)."
    if DPP_BAG_END_PATTERN.search(line): return f"{prefix} Info: Ende der Bildverarbeitung (DPP)."
    if OMS_LOOKUP_ENTERING_PATTERN.search(line): return f"{prefix} Sucht nach finaler Entscheidung für Wanne **{ident}** in der Datenbank."
    if m := OMS_LOOKUP_FOUND_PATTERN.search(line): return f"{prefix} Finale Entscheidung für Wanne **{m.group(1)}** in Datenbank gefunden."
    if m := OMS_RFID_FOUND_PATTERN.search(line):
        eds, ltr = ("**Aktiv**" if m.group(1) == '1' else "Inaktiv"), ("**Aktiv**" if m.group(2) != '0' else "Inaktiv")
        return f"{prefix} Wanne **{ident}** an Weiche erkannt. Status: EDS-Alarm={eds}, LTR-Alarm={ltr}."
    if m := OMS_SET_FINAL_DISP_PATTERN.search(line):
        disp_text = "**Freigabe (CLEAR)**" if str(m.group(1)) == '1' else "**Alarm (ALARM)**"
        return f"{prefix} Interne, finale Entscheidung für Wanne **{ident}** wird gesetzt auf: {disp_text}"
    if OMS_SLOT_SEND_TRIC_MSG.search(line): return f"{prefix} System bereitet den Versand der finalen Entscheidung für Wanne **{ident}** an die Anlage vor."
    if m := OMS_FINAL_CMD_PATTERN.search(line):
        disp_text = "**Freigabe (CLEAR)**" if str(m.group(1)) == '1' else "**Alarm (ALARM)**"
        return f"{prefix} **Finaler Befehl an Förderanlage gesendet: {disp_text}**"
    if m := OMS_PEC_STATUS_PATTERN.search(line):
        pe_id, state = m.groups(); state_text = "Unterbrochen" if state.lower() == 'false' else "Frei"
        return f"{prefix} Lichtschranke (PE {pe_id}) meldet Zustand: **{state_text}**"
    if m := OMS_DIVERTER_ACTION_PATTERN.search(line):
        bag_to_find = m.group(1); return f"{prefix} Anlage sucht Wanne **{bag_to_find}** für eine Weichen-Aktion."
    if m := OMS_GENERIC_CALL_PATTERN.search(line): return f"{prefix} Technischer Systemaufruf: {m.group(1)}"
    return None

def _determine_source(filename, line):
    if "[OMS:" in line: return "OMS"
    filename_lower = filename.lower()
    if filename_lower.startswith("scanner_bag"): return "Scanner-Bag"
    if filename_lower.startswith("scanner"): return "Scanner-Sys"
    if filename_lower.startswith("dbm"): return "DBM"
    if filename_lower.startswith("iqs"): return "IQS"
    if filename_lower.startswith("iqtk"): return "IQTK"
    if filename_lower.startswith("img_svr"): return "ImgSvr"
    if filename_lower.startswith("dcs"): return "DCS"
    if filename_lower.startswith("dpp"): return "DPP"
    return filename

def _parse_generic_log(file_path, update_progress):
    """Ein generischer Parser für alle zeilenbasierten Log-Dateien."""
    try:
        log_records = []; filename = os.path.basename(file_path)
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f: lines = f.readlines()
        
        total_lines, last_month, current_year = len(lines), None, datetime.now().year

        for i, line in enumerate(lines):
            if update_progress and i % 500 == 0:
                update_progress(int((i/total_lines)*100), filename)
            
            ts_match = TS_PATTERN_GENERIC.search(line)
            if ts_match:
                try: dt_object = datetime.strptime(ts_match.group(1), "%Y-%m-%d %H:%M:%S")
                except ValueError: continue
            else:
                ts_match = TS_PATTERN_LEGACY.search(line)
                if ts_match:
                    try:
                        dt_no_year = datetime.strptime(ts_match.group(1), "%a %b %d %H:%M:%S")
                        year_to_use = current_year
                        if last_month and dt_no_year.month < last_month: year_to_use -= 1
                        dt_object = dt_no_year.replace(year=year_to_use); last_month = dt_object.month
                    except ValueError: continue
                else: continue

            bag_id_match = BAG_ID_PATTERN.search(line)
            iata_rfid_match = IATA_RFID_PATTERN.search(line)
            device_id_match = DEVICE_ID_PATTERN.search(line)
            
            bag_id = bag_id_match.group(1) if bag_id_match else None
            iata = next((g for g in iata_rfid_match.groups() if g), None) if iata_rfid_match else None
            device_id = device_id_match.group(1) if device_id_match else None
            
            if not bag_id and not iata: continue
            
            source = _determine_source(filename, line)
            if device_id: source = f"{source} ({device_id})"
            
            klartext = _parse_line_to_klartext(line, source, bag_id, iata)
            
            if klartext:
                op_match = OPERATOR_DISP_PATTERN.search(line)
                operator = op_match.group(2) if op_match else (OPERATOR_DISP_LATE_PATTERN.search(line) or (None, None))[1]

                log_records.append({"Timestamp": dt_object, "BagID": bag_id, "IATA": iata, "Source": source, "Klartext": klartext, "OriginalLog": line.strip(), "Operator": operator})
        return pd.DataFrame(log_records)
    except Exception:
        messagebox.showerror("Parser-Fehler", f"Fehler in '{os.path.basename(file_path)}'.\n\n{traceback.format_exc()}"); return pd.DataFrame()

def _parse_brava_log(file_path, update_progress):
    """Wrapper für den externen BRAVA-Parser mit Fehlerbehandlung."""
    try:
        if update_progress: update_progress(50, f"Verarbeite {os.path.basename(file_path)}...")
        df = parse_external_brava_log(file_path)
        if not df.empty:
            df["Klartext"] = df["Ereignis"].apply(lambda e: "[BRAVA] " + e)
            df = df.rename(columns={"Quelle": "Source", "TrayID": "BagID"}); df["IATA"] = df["BagID"]; df["Operator"] = None
        if update_progress: update_progress(100, "Abgeschlossen.")
        return df
    except Exception:
        messagebox.showerror("Parser-Fehler (BRAVA)", f"Fehler in '{os.path.basename(file_path)}'.\n\n{traceback.format_exc()}"); return pd.DataFrame()

def _parse_breva_plclog_csv(file_path, update_progress):
    """Ein spezialisierter Parser für die 6-spaltige PlcLog.csv von Breva."""
    try:
        records = []; filename = os.path.basename(file_path)
        if update_progress: update_progress(10, f"Lese {filename}...")

        df = pd.read_csv(file_path, comment=';', header=None, on_bad_lines='skip', sep=r',\s*', engine='python')
        df.columns = ["Timestamp", "CmpId", "ClassId", "ErrorId", "InfoId", "InfoText"]
        df['Timestamp'] = pd.to_datetime(df['Timestamp'].str.replace('Z', ''), errors='coerce')
        df.dropna(subset=['Timestamp', 'InfoText'], inplace=True)

        severity_map = {1: "INFO", 2: "WARNUNG", 4: "FEHLER"}

        total_lines = len(df)
        for i, row in df.iterrows():
            if update_progress and i % 100 == 0:
                update_progress(10 + int((i / total_lines) * 90), f"Analysiere {filename}...")
            
            info_text = str(row['InfoText'])
            severity = severity_map.get(row['ClassId'], "UNBEKANNT")
            klartext, bag_id_full = "", None

            iata_match = BREVA_TRAY_RFID.search(info_text) or re.search(r"tray ([\w\d\-]+)", info_text, re.IGNORECASE)
            if iata_match: bag_id_full = iata_match.group(1)

            if BREVA_DIVERTER_REJECT.search(info_text): klartext = f"KRITISCHER FEHLER: Weiche hat nicht wie befohlen sortiert!"
            elif m := BREVA_RESULT_CLEAR.search(info_text): klartext = f"Info: Finale Freigabe-Entscheidung für Wanne {m.group(1)}."
            elif m := BREVA_SEND_TO_OSR.search(info_text): klartext = f"Info: Wanne {m.group(1)} wird zur manuellen Kontrolle (OSR) geschickt."
            elif m := BREVA_TRAY_RFID.search(info_text): klartext = f"Position: Wanne {m.group(1)} am RFID-Leser erkannt."
            elif m := BREVA_STATION_WARNING.search(info_text): klartext = f"System-Warnung von Station '{m.group(1)}'."
            else: klartext = info_text
            
            if klartext:
                normalized_id = None
                if bag_id_full:
                    num_part = re.search(r'(\d+)$', bag_id_full)
                    if num_part:
                        try: normalized_id = str(int(num_part.group(1)))
                        except ValueError: pass
                
                records.append({
                    "Timestamp": row['Timestamp'], "BagID": normalized_id, "IATA": bag_id_full,
                    "Source": f"PLC-{severity}", "Klartext": f"[PLC-{severity}] {klartext}", 
                    "OriginalLog": info_text.strip(), "Operator": None
                })

        if update_progress: update_progress(100, "Abgeschlossen.")
        return pd.DataFrame(records)
    except Exception:
        messagebox.showerror("Parser-Fehler (Breva PlcLog.csv)", f"Fehler in '{os.path.basename(file_path)}'.\n\n{traceback.format_exc()}"); return pd.DataFrame()

# --- ZENTRALE DISPATCHER-FUNKTION ---
def parse_log_file(file_path, progress_callback=None):
    """
    Erkennt den Typ der Log-Datei und ruft den passenden Parser auf.
    """
    filename_lower = os.path.basename(file_path).lower()
    if filename_lower == "plclog.csv":
        return _parse_breva_plclog_csv(file_path, progress_callback)
    elif "brava" in filename_lower:
        return _parse_brava_log(file_path, progress_callback)
    else:
        return _parse_generic_log(file_path, progress_callback)