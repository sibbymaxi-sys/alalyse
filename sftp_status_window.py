# sftp_status_window.py
import tkinter as tk
from tkinter import ttk, scrolledtext

class SFTPStatusWindow(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("SFTP Download-Status")
        self.geometry("600x400")
        self.transient(parent)
        self.grab_set()

        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        self.status_label = ttk.Label(main_frame, text="Initialisiere...", font=("Helvetica", 10, "bold"))
        self.status_label.pack(fill=tk.X, pady=5)

        self.progress_bar = ttk.Progressbar(main_frame, orient="horizontal", mode="determinate")
        self.progress_bar.pack(fill=tk.X, pady=5)

        log_frame = ttk.LabelFrame(main_frame, text="Details", padding=10)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        self.log_text = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, height=15)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        self.log_text.config(state="disabled")

        self.protocol("WM_DELETE_WINDOW", lambda: None) # Verhindert das Schließen durch den Benutzer

    def update_status(self, message, progress=None):
        """ Aktualisiert die UI-Elemente im Haupt-Thread. """
        self.status_label.config(text=message)
        if progress is not None:
            self.progress_bar['value'] = progress
        
        self.log_text.config(state="normal")
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state="disabled")
        self.update_idletasks()

    def close_window(self):
        self.destroy()