# gateview_system_analyzer.py
import os
import re
import pandas as pd
import subprocess
import sys

# FINALE, ERWEITERTE LISTE
RELEVANT_LOG_FILES = [
    "dbm.log", "img_svr.log", "ipi.log", "iqs.log", "iqs_stream.log", 
    "iqtk.log", "iqtk_mtf.log", "optinet.log", "pcscd_bridge.log", 
    "SCS_qdebug.log", "anaconda.log", "current", "scanner.log", "app.log", 
    "scs.log", "bhs.log", "bms.log", "trace.log", "fsm.log", 
    # KORRIGIERT: Der Dateiname ist jetzt großgeschrieben
    "OMS.log", 
    "scanner_bag.log", "plc.log"
]

# Muster für datumsbasierte Logs, die ebenfalls gesucht werden
DATE_BASED_PATTERNS = ["DPP_", "SCS_", "diagserv_"]

class SystemAnalyzer:
    def __init__(self, progress_callback):
        self.progress_callback = progress_callback
        self.incidents_df = pd.DataFrame()

    def run_analysis(self, dir_path):
        log_files = self._find_log_files(dir_path)
        if not log_files:
            return False, "Keine der relevanten Log-Dateien im Ordner gefunden."
        
        all_incidents = self._process_files_robust(log_files)
        
        if not all_incidents:
            return True, "Analyse abgeschlossen. Keine Zeilen mit Fehler-Schlüsselwörtern gefunden."
            
        self.incidents_df = pd.DataFrame(all_incidents)
        return True, f"{len(self.incidents_df)} Systemfehler/-warnungen gefunden."

    def _find_log_files(self, dir_path):
        self.progress_callback(0, "Suche nach relevanten Log-Dateien...")
        log_files = []
        relevant_basenames_lower = [name.lower() for name in RELEVANT_LOG_FILES]

        for root, _, files in os.walk(dir_path):
            for file in files:
                file_lower = file.lower()
                
                for basename in relevant_basenames_lower:
                    is_exact_match = (file_lower == basename)
                    is_rotation = (file_lower.startswith(basename + ".") and file_lower.split('.')[-1].isdigit())
                    if is_exact_match or is_rotation:
                        log_files.append(os.path.join(root, file))
                        break 
                else:
                    for pattern in DATE_BASED_PATTERNS:
                        if file_lower.startswith(pattern.lower()):
                            log_files.append(os.path.join(root, file))
                            break
        return log_files

    def _process_files_robust(self, log_files):
        all_incidents = []
        total_files = len(log_files)
        search_pattern = r'ERROR|FAIL|FAULT|WARNING'

        for i, file_path in enumerate(log_files):
            filename = os.path.basename(file_path)
            self.progress_callback(int(((i + 1) / total_files) * 100), f"Analysiere: {filename}")
            
            found_something = False
            try:
                if sys.platform == "win32":
                    command = ['findstr', '/i', '/c:ERROR', '/c:FAIL', '/c:FAULT', '/c:WARNING', file_path]
                else:
                    command = ['grep', '-E', '-i', search_pattern, file_path]
                result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', errors='ignore')
                
                if result.stdout:
                    found_something = True
                    for line in result.stdout.strip().split('\n'):
                        if not line: continue
                        ts_match = re.search(r'(\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2})', line)
                        all_incidents.append({'Timestamp': ts_match.group(1) if ts_match else "N/A", 'SourceFile': filename, 'Error': line.strip()})
            except Exception as e:
                print(f"Fehler bei Schnell-Analyse von {filename}: {e}")

            if not found_something:
                self.progress_callback(int(((i + 1) / total_files) * 100), f"Fallback-Analyse: {filename}")
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        for line in f:
                            if re.search(search_pattern, line, re.IGNORECASE):
                                ts_match = re.search(r'(\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2})', line)
                                all_incidents.append({'Timestamp': ts_match.group(1) if ts_match else "N/A", 'SourceFile': filename, 'Error': line.strip()})
                except Exception as e:
                    print(f"Fehler bei Fallback-Analyse von {filename}: {e}")
        return all_incidents