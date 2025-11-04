# base_app.py
import tkinter as tk
from tkinter import ttk, messagebox
import sv_ttk
import config_manager as cfg
from license_dialog import LicenseDialog
from license_validator import check_license
import sys # <-- Import für sys.exit()
import configparser # <-- Import zum Lesen des Keys für "Über"-Fenster

class BaseApp(tk.Frame):
    def __init__(self, parent, app_name="App", version="1.0", *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        
        self.parent = parent
        self.app_name = app_name
        self.version = version
        
        self.parent.title(f"{self.app_name} - v{self.version}")
        self.parent.geometry("1200x800")
        
        # --- LIZENZPRÜFUNG (KORRIGIERTE LOGIK) ---
        
        # check_license() gibt (bool, date_obj) zurück
        is_valid, expiration_date = check_license()
        
        if not is_valid:
            try:
                self.parent.deiconify()
            except tk.TclError:
                pass
            
            # 1. Dialog erstellen
            dialog = LicenseDialog(self.parent) 
            
            # 2. Dialog anzeigen (blockiert, bis geschlossen)
            dialog.show()
            
            # 3. Status ERNEUT von Festplatte prüfen
            is_valid_now, new_expiration_date = check_license()
            
            if not is_valid_now:
                # Wenn IMMER NOCH ungültig -> Beenden
                try:
                    self.parent.destroy()
                except tk.TclError:
                    pass
                sys.exit() # Beendet das Programm
        
        # Lizenz ist gültig, lade den Schlüssel-String für das "Über"-Fenster
        self.valid_license_key = self._get_license_key_from_config()
        # --- ENDE LIZENZPRÜFUNG ---
        
        config = cfg.load_config()
        current_theme = config.get("theme", "dark")
        sv_ttk.set_theme(current_theme)
        
        self.pack(fill=tk.BOTH, expand=True)
        self._create_main_menu()

        self.status_bar = ttk.Frame(self, padding=(5, 2))
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.connection_indicator = tk.Canvas(self.status_bar, width=15, height=15, bd=0, highlightthickness=0)
        self.indicator_oval = self.connection_indicator.create_oval(3, 3, 13, 13, fill='gray')
        self.connection_indicator.pack(side=tk.RIGHT, padx=5)

    def _get_license_key_from_config(self):
        """Liest den reinen Lizenzschlüssel-String aus der config.ini."""
        try:
            config = configparser.ConfigParser()
            config.read('config.ini')
            return config.get('License', 'Key', fallback="???")
        except Exception:
            return "???"

    def set_connection_status(self, status):
        colors = {"connected": "#4CAF50", "disconnected": "gray", "error": "#F44336", "connecting": "#FFC107"}
        self.connection_indicator.itemconfig(self.indicator_oval, fill=colors.get(status, "gray"))

    def _create_main_menu(self):
        self.menu_bar = tk.Menu(self.parent)
        self.parent.config(menu=self.menu_bar)

        # Datei-Menü
        file_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Datei", menu=file_menu)
        file_menu.add_command(label="FTP-Profile verwalten", command=self._open_ftp_dialog)
        file_menu.add_separator()
        file_menu.add_command(label="Beenden", command=self.parent.destroy)

        # Ansicht-Menü
        view_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Ansicht", menu=view_menu)
        view_menu.add_command(label="Helles Design", command=lambda: self._set_theme("light"))
        view_menu.add_command(label="Dunkles Design", command=lambda: self._set_theme("dark"))

        # Hilfe-Menü
        help_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Hilfe", menu=help_menu)
        help_menu.add_command(label="Anleitung", command=self._show_help_window)
        help_menu.add_command(label="Über...", command=self._show_about_window)

    def _set_theme(self, theme_name):
        sv_ttk.set_theme(theme_name)
        config = cfg.load_config()
        config["theme"] = theme_name
        cfg.save_config(config)

    def _show_help_window(self):
        messagebox.showinfo("Hilfe", "Keine spezifische Hilfe für diese App definiert.", parent=self.parent)

    def _show_about_window(self):
        about_win = tk.Toplevel(self.parent)
        about_win.title(f"Über {self.app_name}")
        about_win.transient(self.parent); about_win.grab_set(); about_win.resizable(False, False)

        main_frame = ttk.Frame(about_win, padding=20); main_frame.pack()

        ttk.Label(main_frame, text=f"{self.app_name} - Version {self.version}", font=("Helvetica", 12, "bold")).pack(pady=(0, 10))
        ttk.Label(main_frame, text="Copyright © 2025, Patrick Oppermann\nAlle Rechte vorbehalten.").pack()
        
        license_frame = ttk.LabelFrame(main_frame, text="Lizenzinformationen", padding=10)
        license_frame.pack(pady=15, fill=tk.X)
    
        license_key_display = self.valid_license_key[-4:] if self.valid_license_key and len(self.valid_license_key) >= 4 else "????"
        ttk.Label(license_frame, text="Lizenzschlüssel:").grid(row=1, column=0, sticky="w")
        ttk.Label(license_frame, text=f"****-****-****-{license_key_display}").grid(row=1, column=1, sticky="w", padx=5)
        
        ttk.Button(main_frame, text="Lizenz ändern oder neu eingeben...", command=self._open_license_dialog).pack(pady=10)
        
    def _open_license_dialog(self):
        """Öffnet den Lizenz-Dialog erneut."""
        current_key = self._get_license_key_from_config() # Lese aktuellen Schlüssel
        
        dialog = LicenseDialog(self.parent, initial_key=current_key) 
        dialog.show()
        
        # Prüfe den Status erneut nach dem Schließen
        is_valid_now, _ = check_license() 
        
        if is_valid_now:
            self.valid_license_key = self._get_license_key_from_config() # Lade den neuen Schlüssel
            messagebox.showinfo("Lizenz aktualisiert", "Ihre Lizenz wurde erfolgreich aktualisiert.", parent=self.parent)
    
    def _open_ftp_dialog(self):
        messagebox.showinfo("FTP-Profile", "Diese Funktion ist in der Haupt-App (z.B. GateView) verfügbar.", parent=self.parent)