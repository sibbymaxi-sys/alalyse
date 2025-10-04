# worker.py
import os
import concurrent.futures
from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot
from parser import parse_chunk
from analysis_engine import analyze_log_data

class Worker(QObject):
    finished = pyqtSignal(dict)
    progress = pyqtSignal(int)
    status_update = pyqtSignal(str)
    
    def __init__(self, folderpath):
        super().__init__()
        self.folderpath = folderpath
        self._is_running = True

    @pyqtSlot()
    def run(self):
        self.status_update.emit(f"Durchsuche Ordner: {self.folderpath}")
        all_found_errors_raw = []
        
        try:
            # Phase 1: Find all relevant log files
            log_files = []
            for root, _, files in os.walk(self.folderpath):
                for file in files:
                    if file.endswith(('.log', '.txt')):
                        log_files.append(os.path.join(root, file))
            
            if not log_files:
                self.status_update.emit("Keine Log-Dateien (.log, .txt) im Ordner gefunden.")
                self.finished.emit({})
                return
            
            self.status_update.emit(f"{len(log_files)} Log-Dateien gefunden. Lese Inhalte...")

            # Phase 2: Read all files and create chunks
            chunks = []
            chunk_size = 20000
            line_count_total = 0
            
            chunk = []
            for filepath in log_files:
                if not self._is_running: break
                try:
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                        for line in f:
                            line_count_total += 1
                            # Add file path context to the line for potential future use
                            chunk.append((line_count_total, f"[{os.path.basename(filepath)}] {line}"))
                            if len(chunk) >= chunk_size:
                                chunks.append(chunk)
                                chunk = []
                except Exception as e:
                    self.status_update.emit(f"Konnte Datei nicht lesen: {os.path.basename(filepath)} - {e}")
            if chunk:
                chunks.append(chunk)
            
            if not chunks or not self._is_running:
                self.finished.emit({})
                return

            self.status_update.emit(f"Starte Prozess-Pool mit {os.cpu_count()} Kernen...")

            # Phase 3: Parallel processing (this part remains the same)
            processed_chunks = 0
            with concurrent.futures.ProcessPoolExecutor() as executor:
                future_to_chunk = {executor.submit(parse_chunk, chunk): chunk for chunk in chunks}
                
                for future in concurrent.futures.as_completed(future_to_chunk):
                    if not self._is_running:
                        executor.shutdown(wait=False, cancel_futures=True)
                        break
                    
                    result_from_chunk = future.get()
                    all_found_errors_raw.extend(result_from_chunk)
                    
                    processed_chunks += 1
                    percentage = int((processed_chunks / len(chunks)) * 100)
                    self.progress.emit(percentage)
                    self.status_update.emit(f"Chunk {processed_chunks} von {len(chunks)} analysiert...")

            if self._is_running:
                self.status_update.emit("Erstelle intelligenten Analyse-Report...")
                # Add total file count to the report
                final_report = analyze_log_data(all_found_errors_raw)
                final_report['summary']['total_files'] = len(log_files)
                self.status_update.emit("Analyse und Report erfolgreich abgeschlossen!")
                self.finished.emit(final_report)
            else:
                self.status_update.emit("Analyse abgebrochen.")
                self.finished.emit({})

        except Exception as e:
            self.status_update.emit(f"Ein schwerer Fehler ist aufgetreten: {e}")
            self.finished.emit({})

    def stop(self):
        self.status_update.emit("Abbruch wird eingeleitet...")
        self._is_running = False