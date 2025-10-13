# ftp_dialog_advanced.py
import tkinter as tk
from tkinter import ttk, messagebox
import config_manager as cfg

class AdvancedFTPDialog(tk.Toplevel):
    def __init__(self, parent, app_name="default"):
        super().__init__(parent)
        self.transient(parent)
        self.grab_set()
        self.title("FTP-Profile verwalten und herunterladen")
        self.geometry("450x420") # Höhe angepasst für das neue Feld

        self.result = None
        self.app_name = app_name
        self.ftp_profiles = cfg.load_ftp_profiles()

        main_frame = ttk.Frame(self, padding=15)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- Profilauswahl (editierbar) ---
        profile_frame = ttk.LabelFrame(main_frame, text="1. Profil auswählen oder neuen Namen eingeben", padding=10)
        profile_frame.pack(fill=tk.X)
        
        profile_names = list(self.ftp_profiles.keys())
        self.profile_combo = ttk.Combobox(profile_frame, values=profile_names)
        self.profile_combo.pack(fill=tk.X, expand=True)
        self.profile_combo.bind("<<ComboboxSelected>>", self._on_profile_select)

        # --- Eingabefelder ---
        details_frame = ttk.LabelFrame(main_frame, text="2. Verbindungsdetails", padding=10)
        details_frame.pack(fill=tk.X, pady=10)
        
        details_frame.columnconfigure(1, weight=1)
        ttk.Label(details_frame, text="Host/IP:").grid(row=0, column=0, sticky="w", pady=2)
        self.host_entry = ttk.Entry(details_frame)
        self.host_entry.grid(row=0, column=1, sticky="ew")
        ttk.Label(details_frame, text="Port:").grid(row=1, column=0, sticky="w", pady=2)
        self.port_entry = ttk.Entry(details_frame); self.port_entry.grid(row=1, column=1, sticky="ew")
        self.port_entry.insert(0, "22")
        ttk.Label(details_frame, text="Benutzer:").grid(row=2, column=0, sticky="w", pady=2)
        self.user_entry = ttk.Entry(details_frame); self.user_entry.grid(row=2, column=1, sticky="ew")
        ttk.Label(details_frame, text="Passwort:").grid(row=3, column=0, sticky="w", pady=2)
        self.passwd_entry = ttk.Entry(details_frame, show="*"); self.passwd_entry.grid(row=3, column=1, sticky="ew")

        # --- Manuelles Pfad-Feld (Wiederhergestellt) ---
        manual_path_frame = ttk.LabelFrame(main_frame, text="3. Manuellen Pfad hinzufügen (Optional)", padding=10)
        manual_path_frame.pack(fill=tk.X)
        self.manual_path_entry = ttk.Entry(manual_path_frame)
        self.manual_path_entry.pack(fill=tk.X, expand=True)
        self.manual_path_entry.insert(0, "/vollständiger/pfad/zur/datei.log")

        # --- Buttons zum Verwalten der Profile ---
        profile_mgmt_frame = ttk.Frame(main_frame)
        profile_mgmt_frame.pack(fill=tk.X, pady=(10,0))
        ttk.Button(profile_mgmt_frame, text="Profil speichern", command=self._on_save).pack(side=tk.LEFT)
        ttk.Button(profile_mgmt_frame, text="Profil löschen", command=self._on_delete).pack(side=tk.LEFT, padx=10)
        
        # --- Buttons zum Schließen ---
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        ttk.Button(button_frame, text="Download starten", command=self._on_download, style="Accent.TButton").pack(side=tk.RIGHT)
        ttk.Button(button_frame, text="Abbrechen", command=self.destroy).pack(side=tk.RIGHT, padx=10)

        if profile_names:
            self.profile_combo.set(profile_names[0])
            self._on_profile_select()

    def _on_profile_select(self, event=None):
        profile_name = self.profile_combo.get()
        profile_data = self.ftp_profiles.get(profile_name)
        if not profile_data: return
        
        target_name = next(iter(profile_data.get("targets", {})), None)
        if not target_name: return
        
        details = profile_data["targets"][target_name]
        for entry, key in [(self.host_entry, "host"), (self.port_entry, "port"), 
                           (self.user_entry, "user"), (self.passwd_entry, "passwd")]:
            entry.delete(0, tk.END)
            entry.insert(0, details.get(key, ""))

    def _on_save(self):
        profile_name = self.profile_combo.get()
        if not profile_name:
            messagebox.showerror("Fehler", "Bitte geben Sie einen Profilnamen ein.", parent=self)
            return

        if profile_name not in self.ftp_profiles:
            self.ftp_profiles[profile_name] = {"targets": {"Scanner": {}}}
        
        target_name = next(iter(self.ftp_profiles[profile_name].get("targets", {})), "Scanner")

        profile_details = self.ftp_profiles[profile_name]["targets"][target_name]
        profile_details["host"] = self.host_entry.get()
        profile_details["port"] = self.port_entry.get()
        profile_details["user"] = self.user_entry.get()
        profile_details["passwd"] = self.passwd_entry.get()
        
        cfg.save_ftp_profiles(self.ftp_profiles)
        messagebox.showinfo("Erfolg", f"Profil '{profile_name}' wurde gespeichert.", parent=self)
        
        self.profile_combo['values'] = list(self.ftp_profiles.keys())

    def _on_delete(self):
        profile_name = self.profile_combo.get()
        if not profile_name or profile_name not in self.ftp_profiles:
            messagebox.showerror("Fehler", "Bitte wählen Sie ein gültiges Profil zum Löschen aus.", parent=self)
            return
        
        if messagebox.askyesno("Bestätigen", f"Möchten Sie das Profil '{profile_name}' wirklich löschen?", parent=self):
            del self.ftp_profiles[profile_name]
            cfg.save_ftp_profiles(self.ftp_profiles)
            messagebox.showinfo("Erfolg", f"Profil '{profile_name}' wurde gelöscht.", parent=self)
            
            self.profile_combo.set("")
            for entry in [self.host_entry, self.port_entry, self.user_entry, self.passwd_entry]:
                entry.delete(0, tk.END)
            self.profile_combo['values'] = list(self.ftp_profiles.keys())

    def _on_download(self):
        profile_name = self.profile_combo.get()
        if not profile_name:
            messagebox.showwarning("Kein Profil", "Bitte wählen Sie ein Profil aus.", parent=self)
            return

        final_profile = self.ftp_profiles.get(profile_name, {"targets": {"Scanner": {}}}).copy()
        target_name = next(iter(final_profile.get("targets", {})), "Scanner")
        
        if "targets" not in final_profile: final_profile["targets"] = {}
        if target_name not in final_profile["targets"]: final_profile["targets"][target_name] = {}
            
        target_details = final_profile["targets"][target_name]
        target_details["host"] = self.host_entry.get()
        target_details["port"] = self.port_entry.get()
        target_details["user"] = self.user_entry.get()
        target_details["passwd"] = self.passwd_entry.get()
        
        # Logik für den manuellen Pfad
        manual_path = self.manual_path_entry.get()
        if manual_path and manual_path != "/vollständiger/pfad/zur/datei.log":
            manual_rule = {"type": "specific_file", "path": manual_path}
            if "download_rules" in target_details and isinstance(target_details["download_rules"], list):
                target_details["download_rules"].append(manual_rule)
            else:
                target_details["download_rules"] = [manual_rule]

        self.result = final_profile
        self.destroy()

    def show(self):
        self.wait_window()
        return self.result