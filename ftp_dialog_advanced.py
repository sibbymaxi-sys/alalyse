# ftp_dialog_advanced.py
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import config_manager as cfg

class AdvancedFTPDialog(tk.Toplevel):
    def __init__(self, parent, app_name):
        super().__init__(parent)
        self.transient(parent)
        self.grab_set()
        self.title("Erweiterter FTP Log-Download")
        
        self.parent = parent
        self.app_name = app_name
        self.result = None
        self.profiles = cfg.load_ftp_profiles()
        self.target_widgets = {}

        self._setup_widgets()

        default_profile_name = "Standard MV3D" if self.app_name == "mv3d" else "Standard GateView"
        if default_profile_name in self.profiles:
            self.profile_combo.set(default_profile_name)
            self._on_profile_select()

    def _setup_widgets(self):
        main_frame = ttk.Frame(self, padding=15)
        main_frame.pack(fill=tk.BOTH, expand=True)

        profile_frame = ttk.LabelFrame(main_frame, text="Profile Management", padding=10)
        profile_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(profile_frame, text="Profil auswählen:").pack(side=tk.LEFT, padx=(0,5))
        self.profile_combo = ttk.Combobox(profile_frame, values=list(self.profiles.keys()), state="readonly")
        self.profile_combo.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.profile_combo.bind("<<ComboboxSelected>>", self._on_profile_select)
        ttk.Button(profile_frame, text="Löschen", command=self._delete_profile).pack(side=tk.LEFT, padx=5)

        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill="both", expand=True, pady=10)
        
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10,0))
        ttk.Button(button_frame, text="Profil speichern", command=self._save_profile).pack(side=tk.LEFT)
        ttk.Button(button_frame, text="Download starten", command=self._on_download, style='Accent.TButton').pack(side=tk.RIGHT, padx=10)
        ttk.Button(button_frame, text="Abbrechen", command=self.destroy).pack(side=tk.RIGHT)

    def _on_profile_select(self, event=None):
        profile_name = self.profile_combo.get()
        if not profile_name: return
        
        for i in self.notebook.tabs(): self.notebook.forget(i)
        self.target_widgets = {}

        profile_data = self.profiles.get(profile_name, {})
        targets_data = profile_data.get("targets", {})

        for target_name, data in targets_data.items():
            tab = ttk.Frame(self.notebook, padding=10)
            self.notebook.add(tab, text=target_name)
            widgets = {}
            ttk.Label(tab, text="Host / IP-Adresse:").grid(row=0, column=0, sticky="w", pady=5); widgets['host'] = ttk.Entry(tab, width=40); widgets['host'].grid(row=0, column=1, sticky="ew")
            ttk.Label(tab, text="Port:").grid(row=1, column=0, sticky="w", pady=5); widgets['port'] = ttk.Entry(tab, width=10); widgets['port'].grid(row=1, column=1, sticky="w")
            ttk.Label(tab, text="Benutzername:").grid(row=2, column=0, sticky="w", pady=5); widgets['user'] = ttk.Entry(tab, width=40); widgets['user'].grid(row=2, column=1, sticky="ew")
            ttk.Label(tab, text="Passwort:").grid(row=3, column=0, sticky="w", pady=5); widgets['passwd'] = ttk.Entry(tab, width=40, show="*"); widgets['passwd'].grid(row=3, column=1, sticky="ew")
            ttk.Label(tab, text="Pfade (kommagetrennt):").grid(row=4, column=0, sticky="w", pady=5); widgets['paths'] = ttk.Entry(tab, width=50); widgets['paths'].grid(row=4, column=1, sticky="ew")
            self.target_widgets[target_name] = widgets
            
            widgets['host'].insert(0, data.get("host", "")); widgets['port'].insert(0, data.get("port", "22"))
            widgets['user'].insert(0, data.get("user", "")); widgets['passwd'].insert(0, data.get("passwd", ""))
            widgets['paths'].insert(0, ", ".join(data.get("paths", [])))

    def _save_profile(self):
        profile_name = simpledialog.askstring("Profil speichern", "Geben Sie einen Namen für das Profil ein:", parent=self, initialvalue=self.profile_combo.get())
        if not profile_name: return
        details = self._get_details_from_entries(); self.profiles[profile_name] = details; cfg.save_ftp_profiles(self.profiles)
        self.profile_combo['values'] = list(self.profiles.keys()); self.profile_combo.set(profile_name)
        messagebox.showinfo("Gespeichert", f"Profil '{profile_name}' wurde erfolgreich gespeichert.", parent=self)

    def _delete_profile(self):
        profile_name = self.profile_combo.get()
        if not profile_name: return
        if messagebox.askyesno("Löschen bestätigen", f"Möchten Sie das Profil '{profile_name}' wirklich löschen?", parent=self):
            del self.profiles[profile_name]
            cfg.save_ftp_profiles(self.profiles); self.profile_combo.set(''); self.profile_combo['values'] = list(self.profiles.keys())
            for i in self.notebook.tabs(): self.notebook.forget(i)

    def _get_details_from_entries(self):
        profile_data = {"targets": {}}
        for target_name, widgets in self.target_widgets.items():
            profile_data["targets"][target_name] = {
                "host": widgets['host'].get(), "port": widgets['port'].get(), "user": widgets['user'].get(), "passwd": widgets['passwd'].get(),
                "paths": [p.strip() for p in widgets['paths'].get().split(',') if p.strip()]
            }
        return profile_data

    def _on_download(self):
        details = self._get_details_from_entries()
        if not any(target.get("host") for target in details.get("targets", {}).values()):
            messagebox.showwarning("Fehlende Eingabe", "Mindestens ein Ziel muss eine Host-IP haben.", parent=self); return
        self.result = details; self.destroy()

    def show(self):
        self.parent.wait_window(self); return self.result