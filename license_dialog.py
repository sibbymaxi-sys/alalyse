# license_dialog.py
import tkinter as tk
from tkinter import ttk, messagebox
import sv_ttk
import configparser
from datetime import datetime
import sys # <-- Importiere sys für den Exit-Befehl

# Importiere deine Lizenzprüf-Funktion
from license_validator import check_license

# Füge die Funktion zum Speichern des Schlüssels hier ein
def save_license_key(key):
    print("INFO: Speichere Lizenzschlüssel in config.ini...")
    try:
        config = configparser.ConfigParser()
        config.read('config.ini')
        if 'License' not in config:
            config['License'] = {}
        config['License']['Key'] = key
        with open('config.ini', 'w') as configfile:
            config.write(configfile)
        print("INFO: Lizenzschlüssel erfolgreich gespeichert.")
    except Exception as e:
        print(f"FEHLER: Lizenzschlüssel konnte nicht gespeichert werden: {e}")
        
class LicenseDialog(tk.Toplevel):
    def __init__(self, parent):
        print("INFO: Initialisiere Lizenz-Dialog-Fenster...")
        super().__init__(parent)
        self.title("Lizenz-Aktivierung")
        self.geometry("450x180")
        
        # Zentriert das Fenster
        print("INFO: Zentriere Fenster...")
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - (self.winfo_width() // 2)
        y = (self.winfo_screenheight() // 2) - (self.winfo_height() // 2)
        self.geometry(f'+{x}+{y}')
        
        try:
            import sv_ttk
            sv_ttk.set_theme("dark")
            print("INFO: sv_ttk-Theme erfolgreich angewendet.")
        except Exception as e:
            print(f"WARNUNG: sv_ttk-Theme konnte nicht geladen werden. Verwende Standard-Theme. Fehler: {e}")

        self.transient(parent)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        
        self.parent = parent
        self.license_ok = False
        
        print("INFO: Erstelle UI-Elemente...")
        main_frame = ttk.Frame(self, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main_frame, text="Bitte geben Sie einen gültigen Lizenzschlüssel ein:").pack()
        self.key_entry = ttk.Entry(main_frame, width=50)
        self.key_entry.pack(pady=10)
        
        ttk.Button(main_frame, text="Aktivieren", command=self._check_key, style='Accent.TButton').pack()
        print("INFO: UI-Elemente erstellt. Dialog bereit.")

    def _check_key(self):
        print("INFO: Überprüfe Lizenzschlüssel...")
        entered_key = self.key_entry.get().strip()
        if not entered_key:
            messagebox.showerror("Fehler", "Bitte geben Sie einen Lizenzschlüssel ein.", parent=self)
            return

        # Speichere den neuen Schlüssel
        save_license_key(entered_key)
        
        # Prüfe die Lizenz erneut, um zu sehen, ob sie jetzt gültig ist
        license_valid, expiration_date = check_license()

        if license_valid:
            print("INFO: Lizenzschlüssel ist gültig. Dialog wird geschlossen.")
            # Zeige eine Erfolgsmeldung an und schließe den Dialog
            expiration_str = "UNBEGRENZT" if expiration_date.year == 9999 else expiration_date.strftime('%d.%m.%Y')
            messagebox.showinfo("Erfolg", f"Lizenz erfolgreich aktiviert.\nGültig bis: {expiration_str}", parent=self)
            self.license_ok = True
            self.destroy()
        else:
            print("FEHLER: Eingegebener Lizenzschlüssel ist ungültig oder abgelaufen.")
            # Zeige eine Fehlermeldung an und lösche den gespeicherten Schlüssel
            save_license_key('')
            messagebox.showerror("Fehler", f"Der eingegebene Lizenzschlüssel ist ungültig oder abgelaufen.", parent=self)

    def _on_close(self):
        # Das Fenster wird geschlossen und die gesamte Anwendung beendet
        self.parent.destroy()

    def show(self):
        print("INFO: Starte Modaldialog-Schleife...")
        self.parent.wait_window(self)
        print("INFO: Modaldialog-Schleife beendet.")
        return self.license_ok