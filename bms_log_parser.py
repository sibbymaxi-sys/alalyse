# bms_log_parser.py
import re
import pandas as pd
from datetime import datetime
from fault_translator import translate_fault_code

TS_PATTERN = re.compile(r"^([A-Z][a-z]{2}\s+[A-Z][a-z]{2}\s+\d{2}\s+\d{2}:\d{2}:\d{2}\.\d+)")
BAG_DESTROY_PATTERN = re.compile(r'Destroying bag (\d+)')
FAULT_CAUSE_PATTERN = re.compile(r'UpdateScannerStatus - scs_fault_cause = (\d+)')
SCS_STATUS_PATTERN = re.compile(r'UpdateScannerStatus - got SCS Opstate = (\d+)')
FSM_FAULTED_INPUT = re.compile(r"FSM:input=Faulted\(([^)]+)\)")

def parse_line(line):
    # ... (Analyse-Logik unverändert)
    if m := FSM_FAULTED_INPUT.search(line):
        params_str = m.group(1)
        params = dict(item.strip().split("=") for item in params_str.replace(';', ',').split(","))
        flags = {"System-Fehler": params.get('systemFaulted', '0') == '1', "Not-Halt aktiv": params.get('conveyorEStopped', '0') == '1', "Förderanlage gestoppt": params.get('conveyorStopped', '0') == '1', "Fehler an Förderanlage": params.get('conveyorFaulted', '0') == '1', "Scanner bereit": params.get('scsReadyForBags', '0') == '1', "Timeout aufgetreten": params.get('timers', '0') == '1'}
        summary_lines = ["[BMS] Detaillierter Fehler-Statusbericht empfangen:"]
        summary_lines.append(f"    * System-Fehler: {'JA' if flags['System-Fehler'] else 'NEIN'} (systemFaulted={params.get('systemFaulted', '0')})")
        if flags['Not-Halt aktiv']: summary_lines.append(f"    * Not-Halt aktiv: JA (conveyorEStopped={params.get('conveyorEStopped', '0')})")
        if flags['Förderanlage gestoppt']: summary_lines.append(f"    * Förderanlage gestoppt: JA (conveyorStopped={params.get('conveyorStopped', '0')})")
        if flags['Fehler an Förderanlage']: summary_lines.append(f"    * Fehler an Förderanlage: JA (conveyorFaulted={params.get('conveyorFaulted', '0')})")
        if not flags['Scanner bereit']: summary_lines.append(f"    * Scanner bereit: NEIN (scsReadyForBags={params.get('scsReadyForBags', '0')})")
        if flags['Timeout aufgetreten']: summary_lines.append(f"    * Timeout aufgetreten: JA (timers={params.get('timers', '0')})")
        return "\n".join(summary_lines)
    if m := FAULT_CAUSE_PATTERN.search(line):
        fault_code = m.group(1); fault_text = translate_fault_code(fault_code)
        return f"[BMS] Kritische FEHLERURSACHE vom Scanner empfangen: {fault_text} (Code: {fault_code})"
    if m := SCS_STATUS_PATTERN.search(line):
        status_code = m.group(1); status_text = translate_fault_code(status_code)
        if status_code == '0': return f"[BMS] System-Status vom Scanner: {status_text}"
        else: return f"[BMS] Status-Update vom Scanner (SCS): {status_text} (Code: {status_code})"
    if m := BAG_DESTROY_PATTERN.search(line): return f"[BMS] Gepäckstück '{m.group(1)}' wird aus dem aktiven Speicher entfernt."
    return None

def parse_log(file_path):
    records = []
    last_month = None
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            if ts_match := TS_PATTERN.search(line):
                try:
                    # **KORRIGIERTE DATUMS-LOGIK**
                    ts_str_no_year = ts_match.group(1).split('.')[0]
                    dt_no_year = datetime.strptime(ts_str_no_year, "%a %b %d %H:%M:%S")
                    
                    year_to_use = 2025 # Festes Jahr wie besprochen
                    if last_month and dt_no_year.month < last_month:
                        year_to_use += 1
                    
                    dt_object = dt_no_year.replace(year=year_to_use)
                    last_month = dt_object.month

                except ValueError: continue
                
                if klartext := parse_line(line):
                    records.append({"Timestamp": dt_object, "Quelle": "BMS", "Ereignis": klartext, "OriginalLog": line.strip()})
    return pd.DataFrame(records)