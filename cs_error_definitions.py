# cs_error_definitions.py
import re

# --- LOGIK AUS plc_definitions.py ---
_PLC_ALARM_PATTERN = re.compile(r'received alarm with id (\d+)')
_PLC_ALARM_MESSAGES = {
    "10101": "PLC Alarm: Not-Aus Kette 1",
    "10102": "PLC Alarm: Not-Aus Kette 2",
    "10201": "PLC Alarm: Motorschutzschalter M1",
    # ...
}

# --- LOGIK AUS bhs_log_parser.py ---
_BHS_ERROR_PATTERNS = [
    {'Pattern': re.compile(r'BHS_Connection::ConnectTo.*?Failed', re.IGNORECASE), 'Severity': 'Error', 'Description': 'BHS: Verbindung zur Förderanlage fehlgeschlagen.'},
    {'Pattern': re.compile(r'BHS_Connection.*LoginRequest.*Failed', re.IGNORECASE), 'Severity': 'Error', 'Description': 'BHS: Login-Anfrage an Förderanlage fehlgeschlagen.'},
    {'Pattern': re.compile(r'BHS_Connection.*Connection refused', re.IGNORECASE), 'Severity': 'Error', 'Description': 'BHS: Verbindung verweigert.'},
]

# --- LOGIK AUS bms_log_parser.py ---
_BMS_ERROR_PATTERNS = [
    {'Pattern': re.compile(r'BMS_Connection::ConnectTo.*?Failed', re.IGNORECASE), 'Severity': 'Error', 'Description': 'BMS: Verbindung zum BMS fehlgeschlagen.'},
    {'Pattern': re.compile(r'BMS_Connection.*LoginRequest.*Failed', re.IGNORECASE), 'Severity': 'Error', 'Description': 'BMS: Login-Anfrage an BMS fehlgeschlagen.'},
]

# --- LOGIK AUS dpp_log_parser.py ---
_DPP_ERROR_PATTERNS = [
    {'Pattern': re.compile(r'Failed to register DPP client', re.IGNORECASE), 'Severity': 'Error', 'Description': 'DPP: Registrierung fehlgeschlagen.'},
    {'Pattern': re.compile(r'Failed to process image block', re.IGNORECASE), 'Severity': 'Error', 'Description': 'DPP: Bildverarbeitung fehlgeschlagen.'},
    {'Pattern': re.compile(r'GPU temperature threshold exceeded', re.IGNORECASE), 'Severity': 'Warning', 'Description': 'DPP: GPU Temperatur zu hoch.'},
]

# --- LOGIK AUS fsm_log_parser.py ---
_FSM_ERROR_PATTERNS = [
    {'Pattern': re.compile(r'Failed to handle message.*?BHS_Message', re.IGNORECASE), 'Severity': 'Warning', 'Description': 'FSM: Konnte BHS-Nachricht nicht verarbeiten.'},
    {'Pattern': re.compile(r'Invalid bag state transition requested', re.IGNORECASE), 'Severity': 'Warning', 'Description': 'FSM: Ungültiger Statusübergang angefordert.'},
]

# --- LOGIK AUS scs_log_parser.py (ERWEITERT) ---
_SCS_SPECIFIC_PATTERNS = [
    # Höchste Priorität
    {'Pattern': re.compile(r'XRAY state changed to FAULT', re.IGNORECASE), 'Severity': 'Fatal', 'Description': 'SCS: Röntgenstatus wechselte zu FAULT.'},
    {'Pattern': re.compile(r'Failed to initialize X-Ray generator', re.IGNORECASE), 'Severity': 'Fatal', 'Description': 'SCS: Röntgengenerator Initialisierung fehlgeschlagen.'},
    # Fehler
    {'Pattern': re.compile(r'ERROR_BAG_JAM', re.IGNORECASE), 'Severity': 'Error', 'Description': 'SCS: Taschenstau (Bag Jam) erkannt.'}, # Aus qdebug
    {'Pattern': re.compile(r'Detector calibration failed', re.IGNORECASE), 'Severity': 'Error', 'Description': 'SCS: Detektor-Kalibrierung fehlgeschlagen.'},
    {'Pattern': re.compile(r'failed to connect to FSM', re.IGNORECASE), 'Severity': 'Error', 'Description': 'SCS: Verbindung zum FSM fehlgeschlagen.'},
    # Warnungen / Info
    {'Pattern': re.compile(r'Interlock status changed.*OPEN', re.IGNORECASE), 'Severity': 'Warning', 'Description': 'SCS: Interlock geöffnet (Hinweis).'},
]

# --- LOGIK FÜR dbm.log (ERWEITERT) ---
_DBM_ERROR_PATTERNS = [
    {'Pattern': re.compile(r'terminate called after throwing an instance', re.IGNORECASE), 'Severity': 'Fatal', 'Description': 'DBM: Kritische C++ Exception (Absturz wahrscheinlich).'},
    {'Pattern': re.compile(r'Database query failed', re.IGNORECASE), 'Severity': 'Error', 'Description': 'DBM: Datenbankabfrage fehlgeschlagen.'},
    {'Pattern': re.compile(r'record NOT found for bagId', re.IGNORECASE), 'Severity': 'Error', 'Description': 'DBM: Erwarteter Gepäck-Datensatz nicht in DB gefunden.'}, # Neuer Eintrag
    {'Pattern': re.compile(r'Connection pool empty', re.IGNORECASE), 'Severity': 'Warning', 'Description': 'DBM: Verbindungspool leer (Performance?).'},
    {'Pattern': re.compile(r'Bag record exists', re.IGNORECASE), 'Severity': 'Warning', 'Description': 'DBM: Gepäckstück bereits in Cache vorhanden.'},
]

# --- LOGIK FÜR optinet.log ---
_OPTINET_ERROR_PATTERNS = [
    {'Pattern': re.compile(r'Connection to .* lost', re.IGNORECASE), 'Severity': 'Connection', 'Description': 'OptiNet: Verbindung verloren.'},
    {'Pattern': re.compile(r'Failed to send message', re.IGNORECASE), 'Severity': 'Connection', 'Description': 'OptiNet: Senden der Nachricht fehlgeschlagen.'},
    {'Pattern': re.compile(r'Connection attempt failed', re.IGNORECASE), 'Severity': 'Connection', 'Description': 'OptiNet: Verbindungsversuch fehlgeschlagen.'},
]

# --- LOGIK FÜR scanner.log ---
_SCANNER_ERROR_PATTERNS = [
    {'Pattern': re.compile(r'License check failed', re.IGNORECASE), 'Severity': 'License', 'Description': 'Scanner: Lizenzprüfung fehlgeschlagen.'},
    {'Pattern': re.compile(r'Failed to load algorithm', re.IGNORECASE), 'Severity': 'Error', 'Description': 'Scanner: Algorithmus konnte nicht geladen werden.'},
    {'Pattern': re.compile(r'Configuration error:', re.IGNORECASE), 'Severity': 'Config', 'Description': 'Scanner: Konfigurationsfehler.'},
    {'Pattern': re.compile(r'Device Error:', re.IGNORECASE), 'Severity': 'Hardware', 'Description': 'Scanner: Gerätefehler.'},
    {'Pattern': re.compile(r'Exception caught in.*?Scanner', re.IGNORECASE), 'Severity': 'Error', 'Description': 'Scanner: Allgemeine Exception abgefangen.'},
]

# --- LOGIK FÜR diagserv ---
_DIAGSERV_ERROR_PATTERNS = [
    {'Pattern': re.compile(r'!!!! Warning:.*?Fault:\s*(.*)', re.IGNORECASE), 'Severity': 'Warning', 'Description': 'DiagServ Station Fault: {}'},
]


# --- IHR "Reported Error" PARSER ---
_FC_CODES = {
    # (Liste unverändert)
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

def _parse_fc_codes(log_line):
    # (Funktion unverändert)
    match = re.search(r'Reported Error - (\d+) \((.*?)\)', log_line);
    if not match: return None, None
    error_num = match.group(1); code_name = match.group(2)
    if error_num == '0' and not code_name: return None, None
    if code_name in _FC_CODES:
        category, message = _FC_CODES[code_name]
        if category: return category, f"{message} (FC{error_num})"
    if error_num != '0': return "Error", f"Unbekannter Fehlercode (FC{error_num})"
    return None, None

# === Private Helper ===
def _check_patterns(line, patterns):
    # (Funktion unverändert)
    line_lower = line.lower() # Suche case-insensitive im Text
    for item in patterns:
        match = item['Pattern'].search(line) # Suche im Original für Extraktion
        if match:
            desc = item['Description']
            if '{}' in desc and match.groups():
                try: desc = desc.format(match.group(1).strip())
                except IndexError: pass
            return item['Severity'], desc
    return None, None

def _parse_plc(line):
    # (Funktion unverändert)
    match = _PLC_ALARM_PATTERN.search(line)
    if match:
        alarm_id = match.group(1); description = _PLC_ALARM_MESSAGES.get(alarm_id, f"Unbekannter PLC Alarm (ID: {alarm_id})")
        return "Error", description
    return None, None

# === DIE MASTER-FUNKTION (ROUTER) ===
def get_system_error_details(filename, line):
    """Analysiert eine Log-Zeile basierend auf dem Dateinamen."""
    filename_lower = filename.lower()

    # --- SCS & SysError ---
    # Prüfe SCS spezifische Muster ZUERST, da sie oft spezifischer sind als FC Codes
    if filename_lower.startswith(('scs_', 'syserror_')):
        cat, msg = _check_patterns(line, _SCS_SPECIFIC_PATTERNS) # SCS spezifisch zuerst
        if cat: return cat, msg
        cat, msg = _parse_fc_codes(line) # Dann FC Codes
        if cat: return cat, msg
        return None, None

    # --- DiagServ ---
    if filename_lower.startswith('diagserv_'):
         cat, msg = _check_patterns(line, _DIAGSERV_ERROR_PATTERNS)
         if cat: return cat, msg

    # --- PLC ---
    if 'plclog' in filename_lower:
        return _parse_plc(line)

    # --- Scanner ---
    if filename_lower.startswith('scanner.') or filename_lower == 'scanner.log':
        cat, msg = _check_patterns(line, _SCANNER_ERROR_PATTERNS)
        if cat: return cat, msg

    # --- DBM ---
    if filename_lower.startswith('dbm.') or filename_lower == 'dbm.log':
        cat, msg = _check_patterns(line, _DBM_ERROR_PATTERNS)
        if cat: return cat, msg

    # --- OptiNet ---
    if filename_lower.startswith('optinet.') or filename_lower == 'optinet.log':
        cat, msg = _check_patterns(line, _OPTINET_ERROR_PATTERNS)
        if cat: return cat, msg

    # --- Andere BHS-Komponenten ---
    if filename_lower.startswith('bhs_'):
        return _check_patterns(line, _BHS_ERROR_PATTERNS)
    if filename_lower.startswith('bms_'):
        return _check_patterns(line, _BMS_ERROR_PATTERNS)
    if filename_lower.startswith('dpp_'):
        return _check_patterns(line, _DPP_ERROR_PATTERNS)
    if filename_lower.startswith('fsm_'):
        return _check_patterns(line, _FSM_ERROR_PATTERNS)

    # Wenn kein spezifischer Parser getroffen hat
    return None, None