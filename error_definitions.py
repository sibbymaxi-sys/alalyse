# error_definitions.py
import re

# Jedes Tupel: (Regex-Muster, "Was ist das Problem?", "Was passiert in der Anlage?")
ERROR_PATTERNS = [
    (
        re.compile(r"ERROR: Element '([\w-]+)' failed to respond"),
        "Das Baggage Handling System (BHS) meldet, dass eine physische Komponente (z.B. eine Weiche oder ein Förderband), hier '{match}', nicht auf einen Befehl reagiert.",
        "Dies deutet auf ein Hardware-Problem oder eine Kommunikationsstörung mit diesem spezifischen Anlagenteil hin. Der Betrieb in diesem Sektor wird gestoppt, bis das Problem behoben ist. Umliegende Log-Einträge im 'plc.log' können weitere Details liefern."
    ),
    (
        re.compile(r"FEHLERURSACHE gemeldet: \d+ - '(.+?)'"),
        "Das Bag Management System (BMS) hat einen spezifischen, schwerwiegenden Fehlerzustand vom Scanner Control System (SCS) empfangen: '{match}'.",
        "Dies ist eine hochrangige Fehlermeldung, die den gesamten Scanner betrifft. Die genaue Ursache muss in den umgebenden Log-Einträgen der anderen Systeme (insbesondere FSM, SCS, DPP) analysiert werden, um den ursprünglichen Auslöser zu finden."
    ),
    (
        re.compile(r"Client::read\(\) -- exiting\(3\)"),
        "Eine Client-Verbindung zum Data Processing Proxy (DPP) wurde unerwartet beendet. Dies deutet auf einen Netzwerkfehler oder einen Timeout hin.",
        "Häufige Vorkommnisse können zu Datenverlust oder Systemstillstand führen, da die Kommunikation zwischen den Software-Modulen unterbrochen wird. Dies ist oft ein Vorbote für größere Systemfehler."
    ),
    (
        re.compile(r"Bildqualitäts-Test: .*(FAIL)"),
        "Der automatische Bildqualitäts-Test (IQTK) ist fehlgeschlagen.",
        "Das deutet darauf hin, dass die Röntgenanlage oder die Detektoren möglicherweise verschmutzt oder dekalibriert sind. Eine Wartung oder Kalibrierung des Scanners ist dringend erforderlich, um die Bildqualität und damit die Erkennungsleistung sicherzustellen."
    ),
    (
        re.compile(r"PlcWrite - ERROR!!! PLC not connected"),
        "Das Baggage Handling System (BHS) kann keine Verbindung zur speicherprogrammierbaren Steuerung (SPS/PLC) herstellen.",
        "Dies ist ein kritischer Fehler, da die Software die physische Förderanlage nicht mehr steuern kann. Alle Bandbewegungen werden gestoppt, bis die Netzwerk- oder Hardware-Verbindung zur SPS wiederhergestellt ist."
    )
]

def check_for_error(log_entry):
    """Prüft einen Log-Eintrag und gibt bei einem Treffer die Erklärung zurück."""
    for pattern, problem, consequence in ERROR_PATTERNS:
        match = pattern.search(log_entry)
        if match:
            problem_text = problem.format(match=match.group(1) if match.groups() else "")
            return problem_text, consequence
    return None, None