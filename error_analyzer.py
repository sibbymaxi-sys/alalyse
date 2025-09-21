# error_analyzer.py
import pandas as pd
import re
from fault_translator import translate_fault_code

# Muster für primäre Fehler, die eine Analyse auslösen
PRIMARY_FAULT_PATTERNS = [
    re.compile(r"FEHLERURSACHE gemeldet: (\d+) - '(.+?)'"),
    re.compile(r"FEHLER: Anlagenteil '([\w-]+)' antwortet nicht."),
    re.compile(r"Bildqualitäts-Test: .*FAIL")
]

def analyze_errors(df):
    """
    Durchsucht den kombinierten DataFrame nach Fehlern und erstellt Fehler-Reports.
    """
    error_reports = []
    
    # Finde alle primären Fehlerereignisse
    for index, row in df.iterrows():
        for pattern in PRIMARY_FAULT_PATTERNS:
            match = pattern.search(row['Ereignis'])
            if match:
                error_time = row['Timestamp']
                fault_description = match.group(0)
                
                # Definiere ein Zeitfenster um den Fehler herum
                time_window_before = error_time - pd.Timedelta(seconds=5)
                time_window_after = error_time + pd.Timedelta(seconds=1)
                
                # Suche nach relevanten Ereignissen in diesem Zeitfenster
                context_df = df[(df['Timestamp'] >= time_window_before) & (df['Timestamp'] <= time_window_after)]
                
                report = generate_report(fault_description, context_df)
                error_reports.append(report)
                break 

    return error_reports if error_reports else ["Keine kritischen Fehler in den geladenen Log-Dateien gefunden."]

def generate_report(fault, context_df):
    """Erstellt einen einzelnen, formatierten Fehler-Report."""
    report = []
    report.append("--- Fehler-Analyse Report ---")
    report.append(f"Primärer Fehler: {fault}")
    report.append("\nBeweiskette (Ereignisse rund um den Fehler):")
    
    for _, row in context_df.iterrows():
        ts = row['Timestamp'].strftime('%H:%M:%S.%f')[:-3]
        report.append(f"  - [{ts}] {row['Ereignis']}")
        
    diagnosis = get_diagnosis(fault, context_df)
    report.append("\nDiagnose & Empfehlung:")
    report.append(diagnosis)
    report.append("---------------------------------\n")
    return "\n".join(report)

def get_diagnosis(fault, context_df):
    """Gibt eine expertenbasierte Diagnose basierend auf dem Fehlertext und Kontext zurück."""
    if "DPP RTR DOWN" in fault:
        if not context_df[context_df['Ereignis'].str.contains("DPP", na=False)].empty:
            return "Die wahrscheinlichste Ursache ist ein Verbindungsabbruch zum Data Processing Proxy (DPP), oft durch Netzwerkprobleme. Prüfen Sie die Netzwerkverbindung und den Zustand des DPP-Computers."
    if "antwortet nicht" in fault:
        return "Dies deutet auf ein Hardware-Problem oder eine Kommunikationsstörung mit dem genannten Anlagenteil hin. Eine Überprüfung der Komponente vor Ort durch einen Techniker ist erforderlich."
    if "FAIL" in fault:
        return "Die Röntgenanlage ist wahrscheinlich verschmutzt oder dekalibriert. Eine Wartung oder Kalibrierung ist erforderlich, um die Bildqualität sicherzustellen."
    return "Keine spezifische Diagnose verfügbar. Bitte analysieren Sie die Beweiskette manuell."