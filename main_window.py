# main_window.py
import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QPushButton, QVBoxLayout,
                             QWidget, QProgressBar, QLabel, QTextEdit, QFileDialog,
                             QHBoxLayout)
from PyQt5.QtCore import QThread
from worker import Worker

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MV3D System Analyser v6")
        self.setGeometry(100, 100, 600, 500)

        # Variable for the folder path
        self.log_folderpath = None

        # --- UI Elements ---
        # Layout for folder selection
        folder_selection_layout = QHBoxLayout()
        self.folder_path_label = QLabel("Keinen Ordner ausgewählt.")
        self.select_folder_button = QPushButton("Log-Ordner auswählen...")
        folder_selection_layout.addWidget(self.folder_path_label)
        folder_selection_layout.addWidget(self.select_folder_button)

        self.status_label = QLabel("Bereit. Bitte wählen Sie einen Log-Ordner aus.")
        self.progress_bar = QProgressBar()
        self.analyze_button = QPushButton("Analyse starten")
        self.analyze_button.setEnabled(False) # Disabled until a folder is chosen
        self.cancel_button = QPushButton("Abbrechen")
        self.cancel_button.setEnabled(False)
        self.report_output = QTextEdit()
        self.report_output.setReadOnly(True)
        self.report_output.setFontFamily("Courier New")

        # --- Main Layout ---
        layout = QVBoxLayout()
        layout.addLayout(folder_selection_layout)
        layout.addWidget(self.status_label)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.analyze_button)
        layout.addWidget(self.cancel_button)
        layout.addWidget(QLabel("Analyse-Report:"))
        layout.addWidget(self.report_output)

        central_widget = QWidget()
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

        # --- Worker and Thread ---
        self.thread = None
        self.worker = None

        # --- Connect Signals ---
        self.select_folder_button.clicked.connect(self.open_folder_dialog)
        self.analyze_button.clicked.connect(self.start_analysis)
        self.cancel_button.clicked.connect(self.cancel_analysis)

    def open_folder_dialog(self):
        """
        Opens a dialog to select a folder.
        """
        options = QFileDialog.Options()
        options |= QFileDialog.ShowDirsOnly
        folderpath = QFileDialog.getExistingDirectory(self, "Log-Ordner auswählen", "", options=options)
        if folderpath:
            self.log_folderpath = folderpath
            self.folder_path_label.setText(folderpath)
            self.analyze_button.setEnabled(True)
            self.status_label.setText("Bereit. Analyse kann gestartet werden.")

    def start_analysis(self):
        if not self.log_folderpath:
            self.status_label.setText("Fehler: Bitte zuerst einen Ordner auswählen.")
            return
        
        self.thread = QThread()
        # Pass the folder path to the worker
        self.worker = Worker(folderpath=self.log_folderpath)
        self.worker.moveToThread(self.thread)

        # Connections for safe thread handling
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.on_analysis_complete)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)

        self.worker.progress.connect(self.update_progress_bar)
        self.worker.status_update.connect(self.update_status_label)
        
        self.thread.start()

        self.select_folder_button.setEnabled(False)
        self.analyze_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.progress_bar.setValue(0)
        self.report_output.clear()

    # The other methods (cancel_analysis, update_progress_bar, etc.) remain unchanged.
    def cancel_analysis(self):
        if self.worker:
            self.worker.stop()
        self.cancel_button.setEnabled(False)

    def update_progress_bar(self, percentage):
        self.progress_bar.setValue(percentage)

    def update_status_label(self, message):
        self.status_label.setText(message)

    def on_analysis_complete(self, report):
        self.report_output.clear()
        
        if not report or "summary" not in report:
            self.report_output.setText("Analyse fehlgeschlagen, abgebrochen oder keine Logs gefunden.")
        else:
            # This part for formatting the report remains the same
            text = "========== MV3D Gesamt-Analyse-Report ==========\n\n"
            text += f"Analysierte Log-Dateien: {report['summary'].get('total_files', 'N/A')}\n"
            text += f"Anzahl gefundener Fehler: {report['summary']['total_errors']}\n"
            text += f"Anzahl einzigartiger Fehlertypen: {report['summary']['unique_errors']}\n\n"
            
            text += "---------- Top 5 Fehler ----------\n"
            for error in report['top_errors']:
                text += (f"- {error['code']} ({error['count']}x)\n"
                         f"  Beschreibung: {error['definition'].get('description', 'N/A')}\n"
                         f"  Maßnahme: {error['definition'].get('action', 'N/A')}\n\n")

            text += "---------- Erkannte Muster/Sequenzen ----------\n"
            if report['found_patterns']:
                for pattern in report['found_patterns']:
                    text += f"- Muster '{pattern['name']}' erkannt.\n"
                    text += f"  Grund: {pattern['explanation']}\n\n"
            else:
                text += "Keine bekannten Muster gefunden.\n"
            self.report_output.setText(text)
        
        self.select_folder_button.setEnabled(True)
        self.analyze_button.setEnabled(True)
        self.cancel_button.setEnabled(False)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())