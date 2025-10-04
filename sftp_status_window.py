# sftp_status_window.py
import tkinter as tk
from tkinter import ttk

class SFTPStatusWindow(tk.Toplevel):
    """
    Ein kleines Fenster zur Anzeige des Live-Status von SFTP-Operationen.
    """
    def __init__(self, parent):
        super().__init__(parent)
        self.title("SFTP Status")
        self.geometry("450x130")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        # UI-Elemente
        self.status_label = ttk.Label(self, text="Initialisiere Verbindung...", font=("Helvetica", 10))
        self.status_label.pack(pady=(15, 5), padx=10, anchor="w")
        
        self.progress_bar = ttk.Progressbar(self, orient="horizontal", mode="determinate")
        self.progress_bar.pack(fill=tk.X, expand=True, padx=10)
        
        self.percent_label = ttk.Label(self, text="0%", font=("Helvetica", 10))
        self.percent_label.pack(pady=5)

    def update_status(self, message, progress=None):
        """Aktualisiert die angezeigte Nachricht und den Fortschrittsbalken."""
        if self.winfo_exists():
            self.status_label.config(text=message)
            if progress is not None:
                self.progress_bar['value'] = progress
                self.percent_label.config(text=f"{progress}%")
            self.update_idletasks()

    def close_window(self):
        """Schließt das Fenster sicher."""
        if self.winfo_exists():
            self.destroy()