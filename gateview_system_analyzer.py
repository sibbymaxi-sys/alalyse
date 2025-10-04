# gateview_system_analyzer.py
import os
import re
import pandas as pd

class SystemAnalyzer:
    def __init__(self, progress_callback):
        """
        Initialisiert den Analyzer.
        progress_callback: Eine Funktion, um Status-Updates an die GUI zu senden.
        """
        self.progress_callback = progress_callback
        self.incidents_df = pd.DataFrame()

    def run_analysis(self, dir_path):
        """
        Hauptmethode, die den kompletten Analyse-Prozess steuert.
        """
        log_files = self._find_log_files(dir_path)
        if not log_files:
            return False, "Keine .log-Dateien im Ordner gefunden."

        all_incidents = self._process_files(log_files)
        self.incidents_df = pd.DataFrame(all_incidents)
        return True, f"{len(self.incidents_df)} Systemfehler/-warnungen gefunden."

    def _find_log_files(self, dir_path):
        """Durchsucht einen Ordner rekursiv nach .log-Dateien."""
        self.progress_callback(0, "Suche nach Log-Dateien...")
        log_files = []
        for root, _, files in os.walk(dir_path):
            for file in files:
                if file.lower().endswith('.log'):
                    log_files.append(os.path.join(root, file))
        return log_files

    def _process_files(self, log_files):
        """Liest alle Log-Dateien und sucht nach Fehlern."""
        all_incidents = []
        total_files = len(log_files)
        for i, file_path in enumerate(log_files):
            filename = os.path.basename(file_path)
            self.progress_callback(int(((i + 1) / total_files) * 100), f"Analysiere: {filename}")
            
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    for line_num, line in enumerate(f, 1):
                        # Sucht nach den Schlüsselwörtern (Groß-/Kleinschreibung wird ignoriert)
                        if re.search(r'(ERROR|FAIL|FAULT|WARNING)', line, re.IGNORECASE):
                            # Versucht, einen Zeitstempel zu extrahieren
                            timestamp_match = re.search(r'(\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2})', line)
                            timestamp = timestamp_match.group(1) if timestamp_match else "N/A"
                            
                            all_incidents.append({
                                'Timestamp': timestamp,
                                'SourceFile': filename,
                                'Error': line.strip()
                            })
            except Exception as e:
                print(f"Fehler beim Lesen der Datei {filename}: {e}")
        return all_incidents