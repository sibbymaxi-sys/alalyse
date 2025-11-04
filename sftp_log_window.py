# sftp_log_window.py
import tkinter as tk
from tkinter import ttk, scrolledtext

class SFTPLogWindow(tk.Toplevel):
    # --- KORREKTUR: 'title' als optionales Argument hinzugefügt ---
    def __init__(self, parent, title="FTP Log"):
        super().__init__(parent)
        self.title(title) # Setze den Fenstertitel
        self.geometry("800x400")
        self.transient(parent)
        self.grab_set()

        self.log_area = scrolledtext.ScrolledText(self, wrap=tk.WORD, font=("Courier New", 9))
        self.log_area.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)
        self.log_area.config(state="disabled")

    def log(self, message):
        """Fügt eine Nachricht zum Log-Fenster hinzu."""
        self.log_area.config(state="normal")
        self.log_area.insert(tk.END, message + "\n")
        self.log_area.see(tk.END) # Auto-scroll
        self.log_area.config(state="disabled")
        self.update_idletasks()

    def close_window(self):
        """Schließt das Fenster."""
        self.destroy()