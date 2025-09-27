# base_app.py
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import sv_ttk
import matplotlib.pyplot as plt
import license_validator as lic

class BaseApp(ttk.Frame):
    def __init__(self, parent, app_name="Analyzer", version="1.0", *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.parent = parent
        self.app_name = app_name
        self.version = version
        
        self.status_label = None 
        self._setup_menu()
        self.after(100, lambda: sv_ttk.set_theme("light"))

        # Führe die Lizenzprüfung beim Start durch
        self._check_license_status()

    def _check_license_status(self):
        """ Prüft die Lizenz und passt die Anwendung entsprechend an. """
        license_status = lic.check_license()
        
        if license_status["valid"]:
            expires_info = f" (Gültig bis: {license_status['expires']})"
            self.parent.title(f"{self.app_name} v{self.version} - © 2025 Patrick Oppermann{expires_info}")
            return # Alles in Ordnung

        # --- Lizenz ist ungültig ---
        title = "Lizenzproblem"
        message = ""

        if license_status["reason"] == "NO_FILE":
            if messagebox.askokcancel(title, "Keine Lizenzdatei (license.key) gefunden.\n\nMöchten Sie jetzt einen Lizenzschlüssel eingeben?"):
                self._prompt_for_license()
            else:
                self._deactivate_app("Keine Lizenz")
        elif license_status["reason"] == "EXPIRED":
            message = f"Ihre Lizenz ist am {license_status['expires']} abgelaufen."
            if messagebox.askokcancel(title, f"{message}\n\nMöchten Sie einen neuen Schlüssel eingeben?"):
                self._prompt_for_license()
            else:
                self._deactivate_app(message)
        else: # INVALID_KEY oder INVALID_DATE
            message = "Ihr Lizenzschlüssel ist ungültig."
            if messagebox.askokcancel(title, f"{message}\n\nMöchten Sie einen neuen Schlüssel eingeben?"):
                self._prompt_for_license()
            else:
                self._deactivate_app(message)

    def _prompt_for_license(self):
        """ Fragt den Benutzer nach einem neuen Lizenzschlüssel. """
        key = simpledialog.askstring("Lizenzschlüssel eingeben", "Bitte fügen Sie hier Ihren Lizenzschlüssel ein:", parent=self)
        if key:
            if lic.decode_key(key):
                lic.write_license_key(key)
                messagebox.showinfo("Erfolg", "Lizenzschlüssel wurde akzeptiert. Bitte starten Sie das Programm neu.", parent=self)
                self.parent.quit()
            else:
                messagebox.showerror("Fehler", "Der eingegebene Schlüssel ist ungültig.", parent=self)
                self._deactivate_app("Ungültiger Schlüssel")
        else:
            self._deactivate_app("Keine Lizenz")

    def _deactivate_app(self, reason="Lizenz ungültig"):
        """ Deaktiviert die Hauptfunktionen der App. """
        self.parent.title(f"{self.app_name} v{self.version} - LIZENZ UNGÜLTIG")
        
        # Deaktiviere alle Buttons in der App
        for widget in self.winfo_children():
            if isinstance(widget, ttk.Frame):
                for child in widget.winfo_children():
                    if isinstance(child, ttk.Button):
                        child.config(state="disabled")
        
        if self.status_label:
            self.status_label.config(text=f"FEHLER: {reason}. Bitte kontaktieren Sie den Support.", foreground="red")

    def _setup_menu(self):
        menubar = tk.Menu(self.parent)
        self.parent.config(menu=menubar)
        
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="FTP-Download...", command=self._open_ftp_dialog)
        file_menu.add_separator()
        file_menu.add_command(label="Beenden", command=self.parent.quit)
        menubar.add_cascade(label="Datei", menu=file_menu)
        
        view_menu = tk.Menu(menubar, tearoff=0)
        view_menu.add_command(label="Heller Modus", command=lambda: self._set_theme("light"))
        view_menu.add_command(label="Dunkler Modus", command=lambda: self._set_theme("dark"))
        menubar.add_cascade(label="Ansicht", menu=view_menu)
        
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="Anleitung", command=self._show_help_window)
        help_menu.add_separator()
        help_menu.add_command(label=f"Über {self.app_name}", command=self._show_about_dialog)
        menubar.add_cascade(label="Hilfe", menu=help_menu)

    def _show_help_window(self):
        """ Muss in der Kind-Klasse implementiert werden. """
        messagebox.showinfo("Hilfe", "Die Hilfe-Funktion muss in der spezifischen App implementiert werden.")

    def _open_ftp_dialog(self):
        """ Muss in der Kind-Klasse implementiert werden. """
        raise NotImplementedError("Diese Funktion muss in der spezifischen App implementiert werden.")

    def _set_theme(self, theme):
        sv_ttk.set_theme(theme)
        plt.style.use('dark_background' if theme == "dark" else 'default')

    def _show_about_dialog(self):
        message = (f"{self.app_name} v{self.version}\n\n"
                   f"Copyright © 2025, Patrick Oppermann\n\n"
                   f"Lizenziert für: Vollversion")
        messagebox.showinfo(f"Über {self.app_name}", message)