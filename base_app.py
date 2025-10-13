# base_app.py
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import sv_ttk
import config_manager as cfg
from license_dialog import LicenseDialog
from license_validator import check_license

# Importiert den Text für die rechtlichen Hinweise aus der help_texts.py
from help_texts import LEGAL_NOTICE_TEXT

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
        self.indicator_oval = self.connection_indicator.create_oval(2, 2, 14, 14, fill="gray", outline="")
        self.connection_indicator.pack(side=tk.RIGHT, padx=5)

    def set_connection_status(self, status):
        """Ändert die Farbe des Verbindungsindikators in der Statusleiste."""
        color = {"disconnected": "gray", "connected": "green", "error": "red"}.get(status, "gray")
        self.connection_indicator.itemconfig(self.indicator_oval, fill=color)

    def _create_main_menu(self):
        """Erstellt die Hauptmenüleiste der Anwendung."""
        menubar = tk.Menu(self.parent)
        self.parent.config(menu=menubar)

        # Datei-Menü
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Logs von FTP laden...", command=self._open_ftp_dialog)
        file_menu.add_separator()
        file_menu.add_command(label="Beenden", command=self.parent.destroy)
        menubar.add_cascade(label="Datei", menu=file_menu)

        # Ansicht-Menü
        view_menu = tk.Menu(menubar, tearoff=0)
        self.theme_var = tk.StringVar(value=sv_ttk.get_theme())
        view_menu.add_radiobutton(label="Helles Theme", variable=self.theme_var, value="light", command=self._toggle_theme)
        view_menu.add_radiobutton(label="Dunkles Theme", variable=self.theme_var, value="dark", command=self._toggle_theme)
        menubar.add_cascade(label="Ansicht", menu=view_menu)

        # Hilfe-Menü
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="Anleitung anzeigen", command=self._show_help_window)
        help_menu.add_command(label="Rechtliche Hinweise", command=self._show_legal_notice_window)
        help_menu.add_separator()
        help_menu.add_command(label=f"Über {self.app_name}", command=self._show_about_window)
        menubar.add_cascade(label="Hilfe", menu=help_menu)

    def _toggle_theme(self):
        """Schaltet zwischen hellem und dunklem Design um und speichert die Auswahl."""
        theme = self.theme_var.get()
        sv_ttk.set_theme(theme)
        config = cfg.load_config()
        config["theme"] = theme
        cfg.save_config(config)

    def _show_about_window(self):
        """Zeigt das 'Über'-Fenster mit Versions- und Lizenzinformationen an."""
        license_status, license_key = check_license()
        
        about_win = tk.Toplevel(self.parent)
        about_win.title(f"Über {self.app_name}")
        about_win.transient(self.parent); about_win.grab_set()
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
        """Öffnet den Lizenz-Dialog erneut."""
        current_status = check_license()
        dialog = LicenseDialog(self.parent, initial_status=current_status)
        dialog.show()

    def _show_help_window(self):
        """Platzhalter-Funktion für die Hilfe. Muss in der Haupt-App implementiert werden."""
        messagebox.showinfo("Info", "Diese Funktion muss in der spezifischen App (z.B. gateview_app.py) implementiert werden.", parent=self.parent)
        
    def _open_ftp_dialog(self):
        """Platzhalter-Funktion für den FTP-Dialog. Muss in der Haupt-App implementiert werden."""
        messagebox.showinfo("Info", "Diese Funktion muss in der spezifischen App (z.B. gateview_app.py) implementiert werden.", parent=self.parent)

    def _show_legal_notice_window(self):
        """Öffnet ein Fenster zur Anzeige von Disclaimer und Copyright."""
        legal_win = tk.Toplevel(self.parent)
        legal_win.title("Rechtliche Hinweise")
        legal_win.geometry("600x500")
        legal_win.transient(self.parent)
        legal_win.grab_set()

        text_area = scrolledtext.ScrolledText(legal_win, wrap=tk.WORD, font=("Helvetica", 10), padx=10, pady=10)
        text_area.pack(expand=True, fill=tk.BOTH)
        
        # Fügt den importierten Text in das Textfeld ein
        text_area.insert(tk.INSERT, LEGAL_NOTICE_TEXT)
        text_area.config(state="disabled") # Macht den Text schreibgeschützt

        ttk.Button(legal_win, text="Schließen", command=legal_win.destroy).pack(pady=10)