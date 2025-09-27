# ftp_dialog_mv3d.py
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import config_manager as cfg

class FTPDialogMV3D(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("SFTP-Profile für MV3D verwalten")
        self.transient(parent); self.grab_set()
        
        self.result = None
        # Die Log-Ziele wurden an Ihre Struktur angepasst
        self.log_targets = ["SCC", "IAC", "DPP", "IRC"] 
        self.target_widgets = {}
        self.config = cfg.load_profiles()
        self.profiles = self.config.get("ftp_profiles_mv3d", {})

        self._setup_widgets()
        self._load_profile_list()
    
    def _setup_widgets(self):
        main_frame = ttk.Frame(self, padding=20); main_frame.pack(fill=tk.BOTH, expand=True)
        profile_frame = ttk.LabelFrame(main_frame, text="Profil-Verwaltung", padding=10); profile_frame.pack(fill=tk.X, expand=True, pady=(0, 10))
        ttk.Label(profile_frame, text="Profil auswählen:").grid(row=0, column=0, sticky="w", padx=5)
        self.profile_selector = ttk.Combobox(profile_frame, state="readonly", width=25); self.profile_selector.grid(row=0, column=1, sticky="ew", padx=5); self.profile_selector.bind("<<ComboboxSelected>>", self._on_profile_select)
        btn_frame = ttk.Frame(profile_frame); btn_frame.grid(row=0, column=2, padx=10)
        ttk.Button(btn_frame, text="Neu", command=self._create_new_profile).pack(side=tk.LEFT)
        ttk.Button(btn_frame, text="Löschen", command=self._delete_profile).pack(side=tk.LEFT, padx=2)
        login_frame = ttk.LabelFrame(main_frame, text="Allgemeine Login-Daten", padding=10); login_frame.pack(fill=tk.X, expand=True, pady=5)
        ttk.Label(login_frame, text="Benutzer:").grid(row=0, column=0, sticky="w", pady=2); self.user_entry = ttk.Entry(login_frame, width=30); self.user_entry.grid(row=0, column=1, sticky="ew")
        ttk.Label(login_frame, text="Passwort:").grid(row=1, column=0, sticky="w", pady=2); self.pass_entry = ttk.Entry(login_frame, width=30, show="*"); self.pass_entry.grid(row=1, column=1, sticky="ew")
        targets_frame = ttk.LabelFrame(main_frame, text="Rechner-spezifische IPs und Pfade", padding=10); targets_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        ttk.Label(targets_frame, text="Rechner", font=("Helvetica", 10, "bold")).grid(row=0, column=0, padx=5); ttk.Label(targets_frame, text="IP-Adresse", font=("Helvetica", 10, "bold")).grid(row=0, column=1, padx=5); ttk.Label(targets_frame, text="Remote-Verzeichnis", font=("Helvetica", 10, "bold")).grid(row=0, column=2, padx=5)
        for i, target in enumerate(self.log_targets):
            row = i + 1; ttk.Label(targets_frame, text=f"{target}:").grid(row=row, column=0, sticky="w", pady=2)
            ip_entry = ttk.Entry(targets_frame, width=20); ip_entry.grid(row=row, column=1, padx=5, sticky="ew")
            path_entry = ttk.Entry(targets_frame, width=35); path_entry.grid(row=row, column=2, padx=5, sticky="ew")
            self.target_widgets[target] = {"ip": ip_entry, "path": path_entry}
        action_frame = ttk.Frame(main_frame); action_frame.pack(fill=tk.X, pady=10)
        ttk.Button(action_frame, text="Profil speichern", command=self._on_save).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="Herunterladen", command=self._on_download).pack(side=tk.RIGHT, padx=5)

    def _load_profile_list(self):
        profile_names = [p for p in self.profiles.keys() if p != "__last_used"]
        self.profile_selector['values'] = profile_names
        if profile_names:
            last_used = self.profiles.get("__last_used", profile_names[0])
            if last_used in profile_names:
                self.profile_selector.set(last_used)
                self._load_profile_settings(last_used)
            else:
                self.profile_selector.set(profile_names[0])
                self._load_profile_settings(profile_names[0])
        else:
            self._clear_settings(use_defaults=True)

    def _on_profile_select(self, event=None):
        self._load_profile_settings(self.profile_selector.get())

    def _load_profile_settings(self, profile_name):
        profile = self.profiles.get(profile_name, {})
        self.user_entry.delete(0, tk.END); self.user_entry.insert(0, profile.get("user", "root"))
        self.pass_entry.delete(0, tk.END); self.pass_entry.insert(0, profile.get("passwd", "0pp3nheim3r"))
        
        targets = profile.get("targets", {})
        # **NEU:** Standard-Pfade basierend auf Ihrer Verzeichnisstruktur
        defaults = {
            "DPP": {"host": "192.168.7.11", "path": "/var/log/mv3d/dpp"},
            "IAC": {"host": "192.168.7.2", "path": "/opt/eds/log"},
            "SCC": {"host": "192.168.7.10", "path": "/opt/eds/log"},
            "IRC": {"host": "", "path": ""} # Bleibt leer, da nicht spezifiziert
        }

        for target, widgets in self.target_widgets.items():
            target_info = targets.get(target, defaults.get(target, {}))
            widgets["ip"].delete(0, tk.END); widgets["ip"].insert(0, target_info.get("host", ""))
            widgets["path"].delete(0, tk.END); widgets["path"].insert(0, target_info.get("path", ""))

    def _clear_settings(self, use_defaults=False):
        self.user_entry.delete(0, tk.END); self.pass_entry.delete(0, tk.END)
        if use_defaults:
             self._load_profile_settings("__temp_defaults")
        else:
            for widgets in self.target_widgets.values():
                widgets["ip"].delete(0, tk.END); widgets["path"].delete(0, tk.END)

    def _create_new_profile(self):
        new_name = simpledialog.askstring("Neues Profil", "Geben Sie einen Namen für das neue MV3D-Profil ein:", parent=self)
        if new_name and new_name not in self.profiles:
            self.profiles[new_name] = {}
            self.config["ftp_profiles_mv3d"] = self.profiles
            cfg.save_profiles(self.config)
            self._load_profile_list(); self.profile_selector.set(new_name)
            self._load_profile_settings(new_name)
        elif new_name:
            messagebox.showerror("Fehler", "Ein MV3D-Profil mit diesem Namen existiert bereits.", parent=self)

    def _delete_profile(self):
        profile_name = self.profile_selector.get()
        if not profile_name: messagebox.showwarning("Keine Auswahl", "Bitte wählen Sie ein Profil zum Löschen aus.", parent=self); return
        if messagebox.askyesno("Löschen bestätigen", f"Möchten Sie das Profil '{profile_name}' wirklich löschen?", parent=self):
            if profile_name in self.profiles:
                del self.profiles[profile_name]
                self.config["ftp_profiles_mv3d"] = self.profiles
                cfg.save_profiles(self.config); self.profile_selector.set(''); self._load_profile_list()

    def _on_save(self):
        profile_name = self.profile_selector.get()
        if not profile_name: messagebox.showerror("Fehler", "Bitte wählen Sie zuerst ein Profil aus oder erstellen Sie ein neues.", parent=self); return
        
        targets_data = {}
        for target, widgets in self.target_widgets.items():
            targets_data[target] = {"host": widgets["ip"].get(), "path": widgets["path"].get()}
        
        self.profiles[profile_name] = {
            "user": self.user_entry.get(), "passwd": self.pass_entry.get(),
            "targets": targets_data
        }
        self.config["ftp_profiles_mv3d"] = self.profiles
        cfg.save_profiles(self.config)
        messagebox.showinfo("Gespeichert", f"Einstellungen für Profil '{profile_name}' wurden gespeichert.", parent=self)

    def _on_download(self):
        profile_name = self.profile_selector.get()
        if not profile_name: messagebox.showerror("Fehler", "Bitte wählen Sie ein Profil für den Download aus.", parent=self); return
        
        self.profiles["__last_used"] = profile_name
        self.config["ftp_profiles_mv3d"] = self.profiles
        cfg.save_profiles(self.config)
        
        self.result = self.profiles[profile_name]
        self.destroy()

    def show(self):
        self.wm_deiconify(); self.wait_window(); return self.result