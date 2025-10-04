# error_definitions.py
import re

# Die erweiterte Wissensdatenbank mit mehr Fehlerfällen
ERROR_DEFINITIONS = {
    # Not-Aus und Sicherheitskreise
    "SCS_EStop": {"description": "Ein Not-Aus wurde im System-Controller (SCS) ausgelöst.", "action": "NOT-AUS am Gerät prüfen und quittieren. Grund für die Betätigung klären."},
    "BHS_EStop": {"description": "Ein Not-Aus wurde von der Förderanlage (BHS) gemeldet.", "action": "Physischen Not-Aus-Taster an der Anlage prüfen. Sicherstellen, dass alle Schutzvorrichtungen geschlossen sind."},
    "SDB2_FAULT": {"description": "Fehler in der SDB2-Einheit (Safety Distribution Board). Kritischer Sicherheitsfehler.", "action": "Spannungsversorgung und Verkabelung der SDB2-Einheit prüfen. Neustart des Systems erforderlich."},
    "LIGHT_CURTAIN_FAULT": {"description": "Lichtschranke im Sicherheitskreis wurde unterbrochen oder ist defekt.", "action": "Prüfen, ob die Lichtschranke blockiert ist. Sensoren reinigen und auf korrekte Ausrichtung prüfen."},

    # Kühlung und Stromversorgung
    "CHILLER_FAULT": {"description": "Störung im Kühlaggregat des Systems. Mögliche Überhitzungsgefahr.", "action": "Kühlmittelstand, Temperatur und Filter des Chillers prüfen. Luftzufuhr sicherstellen."},
    "POWER_SUPPLY_FAULT": {"description": "Fehler in einer der Hauptstromversorgungen (z.B. 24V-Netzteil).", "action": "Netzteile auf Status-LEDs prüfen. Sicherungen und Verkabelung kontrollieren."},

    # Motor- und Antriebssteuerung
    "YASKAWA_FAULT": {"description": "Fehler in der Yaskawa-Motorsteuerung.", "action": "Motor auf Blockaden, Überhitzung und Verkabelung prüfen. Fehlercode am Yaskawa-Controller auslesen."},
    "MOTOR_OVERLOAD": {"description": "Ein Antriebsmotor meldet Überlast.", "action": "Mechanik des betroffenen Förderbandes auf Blockaden oder Schwergängigkeit prüfen."},
    
    # SPS- und Netzwerkkommunikation
    "PLC_CONNECTION_LOSS": {"description": "Die Netzwerkverbindung zur SPS (PLC) ist unterbrochen.", "action": "Netzwerkkabel, Switch-Ports und IP-Konfiguration zwischen Anwendung und SPS prüfen."},
    "BHS_CONNECTION_FAIL": {"description": "Kommunikationsfehler mit der Förderanlagensteuerung (BHS).", "action": "Netzwerkstatus der BHS-Steuerung prüfen. Log-Dateien der BHS auf spezifische Fehler prüfen."},

    # Sensoren und Systemlogik
    "SENSOR_FAULT": {"description": "Ein kritischer Sensor (z.B. Fotozelle) meldet einen Fehler oder liefert unplausible Werte.", "action": "Betroffenen Sensor lokalisieren, reinigen, neu ausrichten oder ggf. austauschen."},
    "ENCODER_ERROR": {"description": "Fehler am Drehgeber eines Antriebs. Positionserfassung ungenau.", "action": "Verkabelung des Encoders prüfen. Encoder auf Beschädigung oder Verschmutzung kontrollieren."},
    "System-Overrun": {"description": "Das System hat einen internen Zähler-Überlauf registriert, was auf eine hohe Last oder einen Verarbeitungsstau hindeutet.", "action": "Systemlast beobachten, ggf. Neustart des betroffenen Subsystems."}
}

# Muster für eine intelligentere Suche. Die Reihenfolge ist wichtig (spezifisch vor allgemein).
ERROR_PATTERNS = [
    (re.compile(r"SCS.*EStop", re.IGNORECASE), "SCS_EStop"),
    (re.compile(r"BHS.*E-?Stop", re.IGNORECASE), "BHS_EStop"),
    (re.compile(r"SDB2_FAULT", re.IGNORECASE), "SDB2_FAULT"),
    (re.compile(r"Light curtain", re.IGNORECASE), "LIGHT_CURTAIN_FAULT"),
    (re.compile(r"CHILLER_FAULT", re.IGNORECASE), "CHILLER_FAULT"),
    (re.compile(r"Power Supply.*(?:Fail|Fault)", re.IGNORECASE), "POWER_SUPPLY_FAULT"),
    (re.compile(r"YASKAWA.*(?:Fail|Fault)", re.IGNORECASE), "YASKAWA_FAULT"),
    (re.compile(r"Motor.*Overload", re.IGNORECASE), "MOTOR_OVERLOAD"),
    (re.compile(r"PLC.*(?:Connection|Link)", re.IGNORECASE), "PLC_CONNECTION_LOSS"),
    (re.compile(r"BHS.*(?:Connection|Link)", re.IGNORECASE), "BHS_CONNECTION_FAIL"),
    (re.compile(r"Sensor.*(?:Fail|Fault)", re.IGNORECASE), "SENSOR_FAULT"),
    (re.compile(r"Encoder.*(?:Error|Fail)", re.IGNORECASE), "ENCODER_ERROR"),
    (re.compile(r"overrunCount", re.IGNORECASE), "System-Overrun"),
]

def check_for_error(log_entry):
    """
    Durchsucht eine Log-Zeile mit regulären Ausdrücken nach bekannten Fehlermustern
    und gibt eine detaillierte Beschreibung und Handlungsempfehlung zurück.
    """
    if not log_entry or not isinstance(log_entry, str):
        return "Ursache nicht eindeutig identifiziert", "Gesamten Zeitverlauf der Logs manuell prüfen."

    # Durchsuche die Log-Zeile nach den vordefinierten Mustern
    for pattern, error_key in ERROR_PATTERNS:
        match = pattern.search(log_entry)
        if match:
            definition = ERROR_DEFINITIONS[error_key]
            return definition["description"], definition["action"]
            
    # Standard-Antwort, wenn kein spezifisches Muster gefunden wird
    return "Allgemeiner System-Fehler", "Logs auf weitere Schlüsselwörter wie ERROR, FAIL, FAULT oder kritische Systemmeldungen prüfen."

# This dictionary is now based on the official "SCS Fault code list"
ERROR_DEFINITIONS = {
    4: {"name": "SDB2_FAULT", "description": "Fault in the Safety Distribution Board (SDB2).", "action": "Check SDB2 unit, power supply, and cabling. A system restart is likely required."},
    9: {"name": "ISHWFAULTCONDITION", "description": "A general hardware fault was reported.", "action": "This is often a symptom of another fault. Check the log for the fault code that occurred immediately before this one."},
    16: {"name": "ESTOP", "description": "An Emergency Stop (E-Stop) was triggered.", "action": "Identify and clear the cause of the E-Stop. Reset the E-Stop button and the system."},
    23: {"name": "ENCODER_FAULT", "description": "The conveyor encoder is reporting an error.", "action": "Check the encoder for physical damage, dirt, or loose connections. Verify conveyor belt movement."},
    24: {"name": "LIGHT_CURTAIN_FAULT", "description": "The light curtain safety feature is blocked or faulty.", "action": "Ensure the light curtain path is clear of obstructions. Clean the sensors and check alignment."},
    27: {"name": "YASKAWA_FAULT", "description": "Fault reported by the Yaskawa motor controller.", "action": "Check the motor for jams or overheating. Read the specific error code from the Yaskawa controller itself."},
    29: {"name": "UPS_FAULT", "description": "The Uninterruptible Power Supply (UPS) has reported a fault.", "action": "Check the UPS status. It may be running on battery or have an internal issue."},
    30: {"name": "HVPS_FAULT", "description": "A fault was detected in the High Voltage Power Supply.", "action": "This is a critical error. Requires a technician to check the HVPS and X-Ray tube. Check trace.log for 'fault flags'."},
    33: {"name": "BMS_ENTRANCE_BAG_JAM", "description": "A bag jam was detected at the machine entrance.", "action": "Clear the bag jam physically. Check entrance photo-cells (IPEC)."},
    51: {"name": "PLC_CONNECTION_LOSS", "description": "The connection to the PLC was lost.", "action": "Check the network cable and switch ports between the System Controller (SCC) and the PLC."},
    52: {"name": "DPP_HIGH_WATERMARK", "description": "The DPP image processing queue is full, indicating a data backlog.", "action": "This can be a symptom of network issues or problems with the IAC. Check scanner_bag.log for exceptions."},
    54: {"name": "CHILLER_FAULT", "description": "Fault in the system's cooling unit.", "action": "Check the chiller's fluid level, temperature, and filters. Ensure proper airflow."},
    55: {"name": "SYSTEMP_AMBIENT", "description": "The ambient temperature has exceeded the allowed threshold.", "action": "Check the environmental conditions of the room. Ensure air conditioning is working."}
}

# Glossary for PLC log codes
TD_CODES = {
    "4": "Properly Tracked Bag",
    "6": "Bag Spacing Error",
    "8": "Entrance Misstrack",
    "9": "Exit Misstrack"
}

SD_CODES = {
    "12": "Machine Clear",
    "13": "Bag Not Analysed (BNA)",
    "14": "Machine Reject",
    "15": "Timeout",
    "21": "Level 2 Operator Reject",
    "22": "Level 2 Operator Clear",
    "25": "Level 2 Operator Timeout",
    "31": "Level 3 Operator Reject",
    "32": "Level 3 Operator Clear",
    "35": "Level 3 Operator Timeout"
}


def get_error_details(error_code):
    """Returns the details for a given numerical error code."""
    if error_code in ERROR_DEFINITIONS:
        return ERROR_DEFINITIONS[error_code]["description"], ERROR_DEFINITIONS[error_code]["action"]
    return "Unknown Fault Code", "No specific action available. Consult documentation."