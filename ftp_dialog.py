# ftp_dialog.py
import tkinter as tk
from tkinter import ttk, messagebox
import config_manager as cfg

class FTPDialog(tk.Toplevel):
    def __init__(self, parent, app_name="mv3d"):
        super().__init__(parent)
        self.transient(parent)
        self.grab_set()
        self.title("FTP Log-Download")
        
        self.parent = parent
        self.app_name = app_name # 'mv3d' oder 'gateview'
        self.result = None
        
        self.config = cfg.load_config()
        self.profile = self.config.get(f"{app_name}_ftp_profile", {})

        self._setup_widgets()
        self._load_profile()

    def _setup_widgets(self):
        main_frame = ttk.Frame(self, padding=15)
        main_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main_frame, text="Host / IP-Adresse:").grid(row=0, column=0, sticky="w", pady=5)
        self.host_entry = ttk.Entry(main_frame, width=40)
        self.host_entry.grid(row=0, column=1, sticky="ew")
        
        ttk.Label(main_frame, text="Benutzername:").grid(row=1, column=0, sticky="w", pady=5)
        self.user_entry = ttk.Entry(main_frame, width=40)
        self.user_entry.grid(row=1, column=1, sticky="ew")
        
        ttk.Label(main_frame, text="Passwort:").grid(row=2, column=0, sticky="w", pady=5)
        self.pass_entry = ttk.Entry(main_frame, width=40, show="*")
        self.pass_entry.grid(row=2, column=1, sticky="ew")

        # Remote-Pfade
        path_frame = ttk.LabelFrame(main_frame, text="Remote-Pfade der Log-Dateien", padding=10)
        path_frame.grid(row=3, column=0, columnspan=2, sticky="ew", pady=10)
        
        self.path_entries = {}
        systems = ['SCS', 'BHS', 'PLC', 'DPP'] if self.app_name == 'mv3d' else ['Scanner', 'OMS']
        for i, system in enumerate(systems):
            ttk.Label(path_frame, text=f"Pfad für {system}:").grid(row=i, column=0, sticky="w", pady=2)
            entry = ttk.Entry(path_frame, width=50)
            entry.grid(row=i, column=1, sticky="ew", padx=5)
            self.path_entries[system] = entry
        
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=5, column=0, columnspan=2, pady=(10,0))
        ttk.Button(button_frame, text="Download starten", command=self._on_download).pack(side=tk.LEFT, padx=10)
        ttk.Button(button_frame, text="Abbrechen", command=self.destroy).pack(side=tk.LEFT)

    def _load_profile(self):
        """Füllt die Felder mit gespeicherten Daten."""
        self.host_entry.insert(0, self.profile.get("host", ""))
        self.user_entry.insert(0, self.profile.get("user", ""))
        self.pass_entry.insert(0, self.profile.get("passwd", ""))
        
        saved_paths = self.profile.get("remote_paths", {})
        for system, entry in self.path_entries.items():
            entry.insert(0, saved_paths.get(system, f"/remote/path/to/{system.lower()}.log"))

    def _on_download(self):
        """Sammelt die Daten, speichert sie und schließt den Dialog."""
        details = {
            "host": self.host_entry.get(),
            "user": self.user_entry.get(),
            "passwd": self.pass_entry.get(),
            "remote_paths": {system: entry.get() for system, entry in self.path_entries.items()}
        }

        if not all([details["host"], details["user"]]):
            messagebox.showwarning("Fehlende Eingabe", "Host und Benutzername sind erforderlich.", parent=self)
            return

        # Speichere die aktuellen Eingaben für das nächste Mal
        self.config[f"{self.app_name}_ftp_profile"] = details
        cfg.save_config(self.config)
        
        self.result = details
        self.destroy()

    def show(self):
        """Zeigt den Dialog an und gibt das Ergebnis zurück, nachdem er geschlossen wurde."""
        self.parent.wait_window(self)
        return self.result