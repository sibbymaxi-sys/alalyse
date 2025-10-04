# sftp_log_window.py
import tkinter as tk
from tkinter import ttk, scrolledtext
from datetime import datetime

class SFTPLogWindow(tk.Toplevel):
    """
    Ein Fenster, das detaillierte Log-Nachrichten für den sequenziellen Download anzeigt.
    """
    def __init__(self, parent):
        super().__init__(parent)
        self.title("SFTP Download-Protokoll")
        self.geometry("600x400")
        self.transient(parent)
        self.grab_set()

        self.log_area = scrolledtext.ScrolledText(self, wrap=tk.WORD, font=("Courier New", 9))
        self.log_area.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)
        self.log_area.config(state="disabled")

    def log(self, message):
        """Fügt eine neue Nachricht zum Log-Fenster hinzu."""
        if self.winfo_exists():
            timestamp = datetime.now().strftime("%H:%M:%S")
            full_message = f"[{timestamp}] {message}\n"
            
            self.log_area.config(state="normal")
            self.log_area.insert(tk.END, full_message)
            self.log_area.see(tk.END) # Auto-scroll
            self.log_area.config(state="disabled")
            self.update_idletasks()

    def close_window(self):
        if self.winfo_exists():
            self.destroy()