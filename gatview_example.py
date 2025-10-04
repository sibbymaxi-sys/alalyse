# gatview_example.py
from analysis_engine import analyze_log_data
import json # Zur schönen Ausgabe des Dictionaries

def run_gatview_analysis():
    """
    Simuliert eine Analyse, wie sie das gatview-Tool durchführen könnte.
    Es nutzt dieselbe Analyse-Engine, aber ohne GUI.
    """
    print("Starte gatview Kommandozeilen-Analyse...")
    
    # Dummy-Daten, die auch vom Parser kommen könnten
    dummy_log_errors = [
        "Zeile 101: ERROR: YASKAWA_FAULT",
        "Zeile 102: Some other log line",
        "Zeile 103: ERROR: BMS_ENTRANCE_BAG_JAM", # Muster erkannt!
        "Zeile 200: ERROR: CHILLER_FAULT",
        "Zeile 250: ERROR: YASKAWA_FAULT"
    ]
    
    # Dieselbe Funktion aufrufen wie in der GUI-Anwendung!
    report = analyze_log_data(dummy_log_errors)
    
    print("\nAnalyse abgeschlossen. Report wird generiert...")
    
    # Den Report als strukturiertes JSON ausgeben
    print(json.dumps(report, indent=2))

if __name__ == "__main__":
    run_gatview_analysis()