# ftp_dialog.py
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import config_manager as cfg

class FTPDialog(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("FTP-Profile verwalten & herunterladen")
        self.transient(parent)
        self.grab_set()
        
        self.result = None
        self.log_targets = ["IAC", "IRC", "DPP", "SCS"]
        self.path_entries = {}
        self.config = cfg.load_profiles()
        self.profiles = self.config.get("ftp_profiles", {})

        self._setup_widgets()
        self._load_profile_list()

    def _setup_widgets(self):
        main_frame = ttk.Frame(self, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- Profil-Management ---
        profile_frame = ttk.LabelFrame(main_frame, text="Profil-Verwaltung", padding=10)
        profile_frame.pack(fill=tk.X, expand=True, pady=(0, 10))
        
        ttk.Label(profile_frame, text="Profil auswählen:").grid(row=0, column=0, sticky="w", padx=5)
        self.profile_selector = ttk.Combobox(profile_frame, state="readonly")
        self.profile_selector.grid(row=0, column=1, sticky="ew", padx=5)
        self.profile_selector.bind("<<ComboboxSelected>>", self._on_profile_select)

        btn_frame = ttk.Frame(profile_frame)
        btn_frame.grid(row=0, column=2, padx=10)
        ttk.Button(btn_frame, text="Neu", command=self._create_new_profile).pack(side=tk.LEFT)
        ttk.Button(btn_frame, text="Löschen", command=self._delete_profile).pack(side=tk.LEFT, padx=2)

        # --- Einstellungen (werden je nach Profil geladen) ---
        settings_frame = ttk.Frame(main_frame)
        settings_frame.pack(fill=tk.BOTH, expand=True)

        conn_frame = ttk.LabelFrame(settings_frame, text="Verbindungseinstellungen", padding=10)
        conn_frame.pack(fill=tk.X, expand=True)
        ttk.Label(conn_frame, text="IP-Adresse:").grid(row=0, column=0, sticky="w", pady=2); self.host_entry = ttk.Entry(conn_frame, width=30); self.host_entry.grid(row=0, column=1, sticky="ew")
        ttk.Label(conn_frame, text="Benutzer:").grid(row=1, column=0, sticky="w", pady=2); self.user_entry = ttk.Entry(conn_frame, width=30); self.user_entry.grid(row=1, column=1, sticky="ew")
        ttk.Label(conn_frame, text="Passwort:").grid(row=2, column=0, sticky="w", pady=2); self.pass_entry = ttk.Entry(conn_frame, width=30, show="*"); self.pass_entry.grid(row=2, column=1, sticky="ew")

        path_frame = ttk.LabelFrame(settings_frame, text="Remote-Verzeichnisse der Logs", padding=10)
        path_frame.pack(fill=tk.X, expand=True, pady=10)
        for i, target in enumerate(self.log_targets):
            ttk.Label(path_frame, text=f"{target}-Logs Pfad:").grid(row=i, column=0, sticky="w", pady=2)
            entry = ttk.Entry(path_frame, width=40); entry.grid(row=i, column=1, sticky="ew"); self.path_entries[target] = entry
            
        # --- Haupt-Buttons ---
        action_frame = ttk.Frame(main_frame)
        action_frame.pack(fill=tk.X, pady=10)
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
            self._clear_settings()
            
    def _create_new_profile(self):
        new_name = simpledialog.askstring("Neues Profil", "Geben Sie einen Namen für das neue Profil ein:", parent=self)
        if new_name and new_name not in self.profiles:
            self.profiles[new_name] = {}
            self.config["ftp_profiles"] = self.profiles
            cfg.save_profiles(self.config)
            self._load_profile_list()
            self.profile_selector.set(new_name)
            self._clear_settings()
        elif new_name:
            messagebox.showerror("Fehler", "Ein Profil mit diesem Namen existiert bereits.", parent=self)

    def _delete_profile(self):
        profile_name = self.profile_selector.get()
        if not profile_name:
            messagebox.showwarning("Keine Auswahl", "Bitte wählen Sie ein Profil zum Löschen aus.", parent=self)
            return
        if messagebox.askyesno("Löschen bestätigen", f"Möchten Sie das Profil '{profile_name}' wirklich löschen?", parent=self):
            if profile_name in self.profiles:
                del self.profiles[profile_name]
                self.config["ftp_profiles"] = self.profiles
                cfg.save_profiles(self.config)
                self.profile_selector.set('')
                self._load_profile_list()

    def _on_save(self):
        profile_name = self.profile_selector.get()
        if not profile_name:
            messagebox.showerror("Fehler", "Bitte wählen Sie zuerst ein Profil aus oder erstellen Sie ein neues.", parent=self)
            return
        
        remote_paths = {target: entry.get() for target, entry in self.path_entries.items()}
        self.profiles[profile_name] = {
            "host": self.host_entry.get(), "user": self.user_entry.get(),
            "passwd": self.pass_entry.get(), "remote_paths": remote_paths
        }
        self.config["ftp_profiles"] = self.profiles
        cfg.save_profiles(self.config)
        messagebox.showinfo("Gespeichert", f"Einstellungen für Profil '{profile_name}' wurden gespeichert.", parent=self)

    def _on_download(self):
        profile_name = self.profile_selector.get()
        if not profile_name:
            messagebox.showerror("Fehler", "Bitte wählen Sie ein Profil für den Download aus.", parent=self)
            return

        self.profiles["__last_used"] = profile_name
        self.config["ftp_profiles"] = self.profiles
        cfg.save_profiles(self.config)

        self.result = self.profiles[profile_name]
        self.destroy()

    def _on_profile_select(self, event=None):
        self._load_profile_settings(self.profile_selector.get())

    def _load_profile_settings(self, profile_name):
        profile = self.profiles.get(profile_name, {})
        self.host_entry.delete(0, tk.END); self.host_entry.insert(0, profile.get("host", ""))
        self.user_entry.delete(0, tk.END); self.user_entry.insert(0, profile.get("user", "anonymous"))
        self.pass_entry.delete(0, tk.END); self.pass_entry.insert(0, profile.get("passwd", ""))
        remote_paths = profile.get("remote_paths", {})
        for target, entry in self.path_entries.items():
            entry.delete(0, tk.END); entry.insert(0, remote_paths.get(target, f"/logs/{target.lower()}/"))

    def _clear_settings(self):
        self.host_entry.delete(0, tk.END); self.user_entry.delete(0, tk.END); self.pass_entry.delete(0, tk.END)
        for entry in self.path_entries.values(): entry.delete(0, tk.END)

    def show(self):
        self.wm_deiconify(); self.wait_window(); return self.result