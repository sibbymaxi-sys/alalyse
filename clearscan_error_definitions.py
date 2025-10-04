# clearscan_error_definitions.py
import re

# Die erweiterte Liste von Mustern. Spezifische Fehler stehen oben für eine bessere Erkennung.
ERROR_PATTERNS = [
    # --- Kritische Anwendungsfehler (aus app.log) ---
    (re.compile(r"Application going down now", re.IGNORECASE), {
        "Klartext": "Kritischer Fehler: Die Hauptanwendung wurde unerwartet beendet oder neu gestartet.",
        "Aktion": "Prüfen Sie die Logs unmittelbar vor diesem Eintrag auf die eigentliche Fehlerursache. Dies ist oft ein Folgefehler."
    }),
    (re.compile(r"exited abnormally", re.IGNORECASE), {
        "Klartext": "Software-Absturz: Ein Sub-Prozess wurde unerwartet beendet.",
        "Aktion": "Dies deutet auf eine Software-Instabilität hin. Notieren Sie den Zeitstempel und kontaktieren Sie den Support."
    }),

    # --- Bildqualitäts-Testfehler (aus iqtk.log / iqtk_mtf.log) ---
    (re.compile(r"FINAL RESULT: FAIL", re.IGNORECASE), {
        "Klartext": "System-Test fehlgeschlagen: Der automatische Bildqualitätstest (IQTK) ist fehlgeschlagen.",
        "Aktion": "Die Detailergebnisse im Log-Eintrag prüfen (z.B. 'density=... fail'). Möglicherweise ist eine Neukalibrierung oder die Reinigung der Röntgenquelle erforderlich."
    }),

    # --- Datenbankfehler (aus dbm.log) ---
    (re.compile(r"Insert failed", re.IGNORECASE), {
        "Klartext": "Datenbankfehler: Ein Datensatz (vermutlich Gepäck-Info) konnte nicht geschrieben werden.",
        "Aktion": "Datenbank-Service und Festplattenspeicher prüfen. Bei wiederholtem Auftreten den Support kontaktieren."
    }),
    
    # --- Kommunikationsfehler (aus iqs.log / iqs_stream.log) ---
    (re.compile(r"is not connected, can't process", re.IGNORECASE), {
        "Klartext": "Konnektivitätsfehler: Eine Komponente (z.B. CCT) ist nicht verbunden.",
        "Aktion": "Die Netzwerkverbindung und den Betriebsstatus der genannten Komponente prüfen."
    }),
    (re.compile(r"could not locate msg object", re.IGNORECASE), {
        "Klartext": "Kommunikationsfehler: Eine interne Nachricht zwischen Software-Modulen ging verloren.",
        "Aktion": "Kann auf hohe Systemlast hindeuten. System beobachten. Bei häufigem Auftreten Netzwerkverbindungen und Modul-Status prüfen."
    }),
    (re.compile(r"select fails", re.IGNORECASE), {
        "Klartext": "Bild-Server Fehler: Fehler beim Schreiben von Bilddaten.",
        "Aktion": "Dies deutet auf ein Netzwerk- oder Festplattenproblem hin. Systemlast und Speicherplatz prüfen."
    }),

    # --- Allgemeine, aber wichtige Fehler als Fallback ---
    (re.compile(r"Exception", re.IGNORECASE), {
        "Klartext": "Unbehandelte Software-Ausnahme (Exception).",
        "Aktion": "Ein unerwarteter Software-Fehler ist aufgetreten. Die Details im Log-Eintrag sind entscheidend für die Analyse durch den Support."
    }),
    (re.compile(r"ERROR", re.IGNORECASE), {
        "Klartext": "Ein allgemeiner Fehler (ERROR) wurde protokolliert.",
        "Aktion": "Den vollständigen Log-Eintrag auf spezifischere Details untersuchen, um die Ursache zu finden."
    }),
    (re.compile(r"FAIL", re.IGNORECASE), {
        "Klartext": "Ein Fehlschlag (FAIL) wurde protokolliert.",
        "Aktion": "Den vollständigen Log-Eintrag auf spezifischere Details untersuchen, um die Ursache zu finden."
    }),
    (re.compile(r"WARNING", re.IGNORECASE), {
        "Klartext": "Eine Warnung (WARNING) wurde protokolliert.",
        "Aktion": "Den Log-Eintrag prüfen. Warnungen deuten oft auf zukünftige Probleme oder unerwartete Zustände hin."
    })
]

def get_error_details(log_line):
    """
    Durchsucht eine Log-Zeile nach bekannten Mustern und gibt die Klartext-Analyse zurück.
    """
    if not log_line or not isinstance(log_line, str):
        return "Keine Daten", "Keine Aktion"

    for pattern, details in ERROR_PATTERNS:
        if pattern.search(log_line):
            return details["Klartext"], details["Aktion"]
            
    # Fallback, wenn kein Muster passt
    return "Unbekannter Fehler oder allgemeiner Log-Eintrag", "Den Log-Eintrag manuell auf Auffälligkeiten prüfen."