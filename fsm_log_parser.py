# fsm_log_parser.py
import re
import pandas as pd
from datetime import datetime

TS_PATTERN = re.compile(r"^([A-Z][a-z]{2}\s+[A-Z][a-z]{2}\s+\d{2}\s+\d{2}:\d{2}:\d{2}\.\d+)")
FSM_STATE_CHANGE = re.compile(r"FSM:next\((\w+)\)")
# NEU: Erkennt jetzt den Input-Typ und die Parameter separat
FSM_INPUT = re.compile(r"FSM:input=(\w+)\(([^)]+)\)") 

def parse_line(line):
    if m := FSM_STATE_CHANGE.search(line):
        state = m.group(1)
        explanation = {
            "IDLE": "Leerlauf (System wartet auf Aufgabe)",
            "PROCESSING": "Verarbeitung aktiv",
            "BAG_LEAVING": "Gepäckstück verlässt den Prozess",
            "FAULT": "FEHLERZUSTAND"
        }.get(state, f"Unbekannter Zustand '{state}'")
        return f"[FSM] System-Zustand wechselt zu: {explanation}"

    if m := FSM_INPUT.search(line):
        input_type = m.group(1)
        params_str = m.group(2)
        
        # Fall 1: Detaillierter Statusbericht (Faulted, Ready, etc.)
        if "systemFaulted" in params_str:
            params = dict(item.strip().split("=") for item in params_str.replace(';', ',').split(","))
            
            # Die wichtigsten Status-Flags auslesen und direkt übersetzen
            flags = {
                "System-Fehler": params.get('systemFaulted', '0') == '1',
                "Not-Halt aktiv": params.get('conveyorEStopped', '0') == '1',
                "Förderanlage gestoppt": params.get('conveyorStopped', '0') == '1',
                "Fehler an Förderanlage": params.get('conveyorFaulted', '0') == '1',
                "Scanner bereit": params.get('scsReadyForBags', '0') == '1',
                "Timeout aufgetreten": params.get('timers', '0') == '1'
            }

            # Titel basierend auf dem Fehlertyp
            title = f"Detaillierter FEHLER-Statusbericht ({input_type})" if flags["System-Fehler"] else f"Detaillierter System-Statusbericht ({input_type})"
            summary_lines = [f"[FSM] System-Input empfangen: {title}"]
            
            # Baue die Klartext-Ausgabe Punkt für Punkt auf
            summary_lines.append(f"    * System-Fehler: {'JA' if flags['System-Fehler'] else 'NEIN'} (systemFaulted={params.get('systemFaulted', '0')})")
            
            # Zeige nur die relevanten "wahren" oder "falschen" Flags
            if flags['Not-Halt aktiv']:
                summary_lines.append(f"    * Not-Halt aktiv: JA (conveyorEStopped={params.get('conveyorEStopped', '0')})")
            if flags['Förderanlage gestoppt']:
                summary_lines.append(f"    * Förderanlage gestoppt: JA (conveyorStopped={params.get('conveyorStopped', '0')})")
            if flags['Fehler an Förderanlage']:
                summary_lines.append(f"    * Fehler an Förderanlage: JA (conveyorFaulted={params.get('conveyorFaulted', '0')})")
            if not flags['Scanner bereit']:
                summary_lines.append(f"    * Scanner bereit: NEIN (scsReadyForBags={params.get('scsReadyForBags', '0')})")
            if flags['Timeout aufgetreten']:
                summary_lines.append(f"    * Timeout aufgetreten: JA (timers={params.get('timers', '0')})")
                
            return "\n".join(summary_lines)
            
        # Fall 2: Einfacher Input
        else:
            explanation = {
                "BAG_ENTERING": "Gepäckstück läuft ein",
                "BAG_READY": "Gepäckstück ist bereit zur Analyse",
                "BAG_ALARM": "Analyse-Ergebnis: ALARM",
                "BAG_CLEAR": "Analyse-Ergebnis: CLEAR",
                "BAG_EXITED": "Gepäckstück hat das System verlassen",
                "RESET": "Fehler-Reset wurde ausgelöst"
            }.get(input_type, f"Unbekannter Input '{input_type}'")
            return f"[FSM] System-Input empfangen: {explanation}"
            
    return None

def parse_log(file_path):
    records = []
    last_month = None
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            if ts_match := TS_PATTERN.search(line):
                try:
                    ts_str_no_year = ts_match.group(1).split('.')[0]
                    dt_no_year = datetime.strptime(ts_str_no_year, "%a %b %d %H:%M:%S")
                    
                    year_to_use = 2025 
                    if last_month and dt_no_year.month < last_month:
                        year_to_use += 1
                    
                    dt_object = dt_no_year.replace(year=year_to_use)
                    last_month = dt_object.month
                except ValueError: 
                    continue
                
                if klartext := parse_line(line):
                    records.append({
                        "Timestamp": dt_object,
                        "Quelle": "FSM",
                        "Ereignis": klartext,
                        "OriginalLog": line.strip()
                    })
    return pd.DataFrame(records)