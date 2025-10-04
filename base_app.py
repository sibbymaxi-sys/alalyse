# base_app.py
import tkinter as tk
from tkinter import ttk, messagebox
import sv_ttk
import config_manager as cfg
# NEU: Wir importieren die benötigten Lizenz-Funktionen
from license_dialog import LicenseDialog
from license_validator import check_license

class BaseApp(tk.Frame):
    def __init__(self, parent, app_name="App", version="1.0", *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        
        self.parent = parent
        self.app_name = app_name
        self.version = version
        
        self.parent.title(f"{self.app_name} - v{self.version}")
        self.parent.geometry("1200x800")
        
        config = cfg.load_config()
        current_theme = config.get("theme", "dark")
        sv_ttk.set_theme(current_theme)
        
        self.pack(fill=tk.BOTH, expand=True)
        self._create_main_menu()

        self.status_bar = ttk.Frame(self, padding=(5, 2))
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.connection_indicator = tk.Canvas(self.status_bar, width=15, height=15, bd=0, highlightthickness=0)
        self.indicator_oval = self.connection_indicator.create_oval(2, 2, 14, 14, fill="gray", outline="gray")
        self.connection_indicator.pack(side=tk.LEFT, padx=(5, 0))
    
    def set_connection_status(self, status):
        colors = {"disconnected": "gray", "connected": "#2E8B57", "error": "#B22222"}
        color = colors.get(status, "gray")
        if hasattr(self, 'connection_indicator'):
            self.connection_indicator.itemconfig(self.indicator_oval, fill=color, outline=color)
            self.update_idletasks()

    def _create_main_menu(self):
        menubar = tk.Menu(self.parent)
        self.parent.config(menu=menubar)
        file_menu = tk.Menu(menubar, tearoff=0); file_menu.add_command(label="Logs von FTP laden...", command=self._open_ftp_dialog); file_menu.add_separator(); file_menu.add_command(label="Beenden", command=self.parent.destroy); menubar.add_cascade(label="Datei", menu=file_menu)
        view_menu = tk.Menu(menubar, tearoff=0); view_menu.add_command(label="Helles Theme", command=lambda: self._set_theme("light")); view_menu.add_command(label="Dunkles Theme", command=lambda: self._set_theme("dark")); menubar.add_cascade(label="Ansicht", menu=view_menu)
        help_menu = tk.Menu(menubar, tearoff=0); help_menu.add_command(label="Anleitung anzeigen", command=self._show_help_window); help_menu.add_separator(); help_menu.add_command(label="Über...", command=self._show_about_dialog); menubar.add_cascade(label="Hilfe", menu=help_menu)

    def _set_theme(self, theme_name):
        sv_ttk.set_theme(theme_name)
        config = cfg.load_config()
        config["theme"] = theme_name
        cfg.save_config(config)

    def _show_about_dialog(self):
        config = cfg.load_config()
        license_user = config.get("license_user", "N/A")
        license_key = config.get("license_key", "Kein Schlüssel gespeichert")

        about_win = tk.Toplevel(self)
        about_win.title(f"Über {self.app_name}")
        about_win.transient(self); about_win.grab_set()
        about_win.resizable(False, False)

        main_frame = ttk.Frame(about_win, padding=20)
        main_frame.pack()

        ttk.Label(main_frame, text=f"{self.app_name} - Version {self.version}", font=("Helvetica", 12, "bold")).pack(pady=(0, 10))
        ttk.Label(main_frame, text="Copyright © 2025, Patrick Oppermann\nAlle Rechte vorbehalten.").pack()
        
        license_frame = ttk.LabelFrame(main_frame, text="Lizenzinformationen", padding=10)
        license_frame.pack(pady=15, fill=tk.X)
    
        ttk.Label(license_frame, text="Lizenzschlüssel:").grid(row=1, column=0, sticky="w")
        ttk.Label(license_frame, text=f"****-****-****-{license_key[-4:]}").grid(row=1, column=1, sticky="w", padx=5)
        
        ttk.Button(main_frame, text="Lizenz ändern oder neu eingeben...", command=self._open_license_dialog).pack(pady=10)
        
    def _open_license_dialog(self):
        """Öffnet den Lizenz-Dialog erneut, nachdem der aktuelle Status geprüft wurde."""
        # KORREKTUR: Wir holen den aktuellen Lizenzstatus, bevor wir den Dialog öffnen.
        current_status = check_license()
        dialog = LicenseDialog(self, license_status=current_status)
        dialog.show()

    def _open_ftp_dialog(self):
        messagebox.showinfo("Info", "Diese Funktion muss in der spezifischen App implementiert werden.")

    def _show_help_window(self):
        messagebox.showinfo("Hilfe", "Keine spezifische Hilfe für diese App gefunden.")