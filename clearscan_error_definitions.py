# clearscan_error_definitions.py
import re

# Diese "Datenbank" basiert auf den Informationen aus dem
# ClearScan Troubleshooting Guide, Kapitel 5 (FC CODES).
FC_CODES = {
    # Code-Name: (Kategorie, Deutsche Klartext-Meldung)
    "STAT_VAL_SCS_MACHINE_FAULTCAUSE_NONE": (None, "Keine Fehler"),
    "STAT_VAL_SCS_MACHINE_FAULTCAUSE_DIAG_FAULT": ("Error", "Diagnose-Fehler"),
    "STAT_VAL_SCS_MACHINE_FAULTCAUSE_SCRIPT_FAULT": ("Error", "Skript-Fehler"),
    "STAT_VAL_SCS_MACHINE_FAULTCAUSE_ERROR_MSG": ("Error", "Fehlermeldung (allgemein)"),
    "STAT_VAL_SCS_MACHINE_FAULTCAUSE_ESTOP": ("Fatal", "Not-Halt (E-Stop) wurde betätigt"),
    "STAT_VAL_SCS_MACHINE_FAULTCAUSE_ILOCK": ("Fatal", "Interlock-Fehler (Sicherheitskreis unterbrochen, z.B. Panel)"),
    "STAT_VAL_SCS_MACHINE_FAULTCAUSE_GANTRY_DIRECTION": ("Fatal", "Gantry dreht in die falsche Richtung"),
    "STAT_VAL_SCS_MACHINE_FAULTCAUSE_BAG_JAM": ("Warning", "Taschenstau (Ausgangs-Lichtschranke blockiert)"),
    "STAT_VAL_SCS_MACHINE_FAULTCAUSE_TOO_MANY_BAGS": ("Warning", "Zu viele Taschen im System (Queue voll)"),
    "STAT_VAL_SCS_MACHINE_FAULTCAUSE_WATCHDOG": ("Fatal", "System-Watchdog (Timer-Fehler)"),
    "STAT_VAL_SCS_MACHINE_FAULTCAUSE_DIAG_DISCONNECTION": ("Connection", "Diagnose-Verbindung unterbrochen"),
    "STAT_VAL_SCS_MACHINE_FAULTCAUSE_XRAY_KEY_OFF": ("Info", "Röntgenschlüssel ist auf AUS"),
    "STAT_VAL_SCS_MACHINE_FAULTCAUSE_SUB_FAIL": ("Error", "Sub-System Fehler"),
    "STAT_VAL_SCS_MACHINE_FAULTCAUSE_COMM_FAIL": ("Hardware", "Comm-Board Fehler (Kommunikation)"),
    "STAT_VAL_SCS_MACHINE_FAULTCAUSE_ENCLOSURE_FAIL": ("Hardware", "Detektor-Abdeckung Interlock offen"),
    "STAT_VAL_SCS_MACHINE_FAULTCAUSE_CT_HVPS_FAIL": ("Hardware", "Röntgenquelle (Tank) Fehler"),
    "STAT_VAL_SCS_MACHINE_FAULTCAUSE_LS_HVPS_FAIL": ("Hardware", "Niederspannungs-Netzteil Fehler (nicht verwendet)"),
    "STAT_VAL_SCS_MACHINE_FAULTCAUSE_CT_MOTOR_FAIL": ("Hardware", "Gantry-Motor Fehler"),
    "STAT_VAL_SCS_MACHINE_FAULTCAUSE_LS_MOTOR_FAIL": ("Hardware", "Förderband-Motor Fehler"),
    "STAT_VAL_SCS_MACHINE_FAULTCAUSE_SDB_FAIL": ("Hardware", "SDB-Fehler (Signal Distribution Board)"),
    "STAT_VAL_SCS_MACHINE_FAULTCAUSE_DPP_FAIL": ("Hardware", "DPP-Fehler (GPU Überhitzung?)"),
    "STAT_VAL_SCS_MACHINE_FAULTCAUSE_DCS_FAIL": ("Fatal", "DCS-Fehler (Software Absturz?)"),
    "STAT_VAL_SCS_MACHINE_FAULTCAUSE_DCS_NO_BARKER": ("Hardware", "Barker-Code (Encoder) fehlt oder falsch ausgerichtet"),
    "STAT_VAL_SCS_MACHINE_FAULTCAUSE_DCS_NON_CONTIGUOUS_CNT": ("Hardware", "Encoder-Zählung außer der Reihe"),
    "STAT_VAL_SCS_MACHINE_FAULTCAUSE_DCS_ZERO_HBC_RATE": ("Fatal", "Encoder-Rate ist Null (Gantry steht, Faser-Problem, Strom Gantry)"),
    "STAT_VAL_SCS_MACHINE_FAULTCAUSE_GANTRY_SPEED": ("Hardware", "Gantry-Drehzahl falsch"),
}

def get_fc_code_details(log_line):
    """
    Übersetzt ClearScan-Fehlercodes (FC) in verständlichen Text.
    """
    # Sucht nach "Reported Error - X (STAT_VAL_...)" oder "Reported Error - X ()"
    match = re.search(r'Reported Error - (\d+) \((.*?)\)', log_line)
    if not match:
        return None, None
        
    error_num = match.group(1)
    code_name = match.group(2)
    
    # Fall 1: "Reported Error - 0 ()"
    if error_num == '0' and not code_name:
        return None, None # "Kein Fehler", wird nicht gelistet

    # Fall 2: "Reported Error - 4 (STAT_VAL_...)"
    if code_name in FC_CODES:
        category, message = FC_CODES[code_name]
        if category:
            # Füge den FC-Code zur Meldung hinzu, z.B. "[Fatal] Not-Halt (E-Stop) (FC4)"
            return category, f"{message} (FC{error_num})" 
    
    # Fall 3: "Reported Error - 4 ()" (Unbekannter Code, aber nicht 0)
    if error_num != '0':
        return "Error", f"Unbekannter Fehlercode (FC{error_num})"
        
    return None, None