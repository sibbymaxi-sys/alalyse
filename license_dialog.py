# license_dialog.py
import tkinter as tk
from tkinter import ttk, messagebox
# Wir importieren Ihre Validierungs- und Speicherlogik
from license_validator import check_license, write_license_key

class LicenseDialog(tk.Toplevel):
    def __init__(self, parent, license_status):
        super().__init__(parent)
        self.title("Lizenz-Aktivierung")
        self.geometry("450x180")
        self.transient(parent)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        
        self.parent = parent
        self.license_ok = False
        
        main_frame = ttk.Frame(self, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Zeige den Grund an, warum die Lizenz ungültig ist
        reason_text = self.get_reason_text(license_status)
        ttk.Label(main_frame, text=reason_text, foreground="red").pack(pady=(0, 10))

        ttk.Label(main_frame, text="Bitte geben Sie einen gültigen Lizenzschlüssel ein:").pack()
        self.key_entry = ttk.Entry(main_frame, width=50)
        self.key_entry.pack(pady=10)
        
        ttk.Button(main_frame, text="Aktivieren", command=self._check_key, style='Accent.TButton').pack()

    def get_reason_text(self, status):
        """Übersetzt den Lizenzstatus in eine für den Benutzer lesbare Nachricht."""
        reason = status.get("reason", "UNKNOWN")
        if reason == "NO_FILE":
            return "Keine Lizenzdatei (license.key) gefunden."
        if reason == "INVALID_KEY":
            return "Der gespeicherte Lizenzschlüssel ist ungültig."
        if reason == "EXPIRED":
            return f"Ihre Lizenz ist am {status.get('expires')} abgelaufen."
        if reason == "INVALID_DATE":
            return "Das Datumsformat im Schlüssel ist ungültig."
        return "Eine gültige Lizenz wird benötigt."

    def _check_key(self):
        user_key = self.key_entry.get().strip()
        if not user_key:
            messagebox.showerror("Fehler", "Bitte geben Sie einen Lizenzschlüssel ein.", parent=self)
            return

        # Schreibe den neuen Schlüssel in die license.key Datei
        if not write_license_key(user_key):
            messagebox.showerror("Fehler", "Der Lizenzschlüssel konnte nicht gespeichert werden.", parent=self)
            return
        
        # Prüfe die Lizenz erneut
        license_status = check_license()
        if license_status.get("valid"):
            messagebox.showinfo("Erfolg", f"Lizenz erfolgreich aktiviert.\nGültig bis: {license_status.get('expires')}", parent=self)
            self.license_ok = True
            self.destroy()
        else:
            messagebox.showerror("Fehler", f"Der eingegebene Lizenzschlüssel ist ungültig oder abgelaufen.", parent=self)

    def _on_close(self):
        if messagebox.askyesno("Beenden", "Möchten Sie das Programm wirklich beenden?", parent=self):
            self.parent.destroy()

    def show(self):
        self.parent.wait_window(self)
        return self.license_ok