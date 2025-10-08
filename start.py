# start.py
import tkinter as tk
from tkinter import ttk, messagebox
import sv_ttk
import traceback
import sys
import multiprocessing
import configparser
from datetime import datetime

# Importiere deine lokalen Module
from license_validator import check_license
from license_dialog import LicenseDialog
from mv3d_app import MV3DApp
from gateview_app import GateViewApp

class Launcher(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Programm auswählen")
        self.geometry("400x250")
        
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - (self.winfo_width() // 2)
        y = (self.winfo_screenheight() // 2) - (self.winfo_height() // 2)
        self.geometry(f'+{x}+{y}')
        
        try:
            import sv_ttk
            sv_ttk.set_theme("dark")
            print("INFO: sv_ttk-Theme erfolgreich angewendet.")
        except Exception as e:
            print(f"WARNUNG: sv_ttk-Theme konnte nicht geladen werden. Fehler: {e}")

        main_frame = ttk.Frame(self, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main_frame, text="Welches Programm möchten Sie starten?", font=("Helvetica", 12)).pack(pady=10)
        
        ttk.Button(main_frame, text="MV3D System Analyser", command=self.launch_mv3d, style='Accent.TButton').pack(pady=10, fill=tk.X)
        ttk.Button(main_frame, text="Clear Scan Analyser", command=self.launch_gateview).pack(pady=10, fill=tk.X)
        
        # Lizenzprüfung beim Start des Launchers
        self.check_and_display_license()

    def check_and_display_license(self):
        license_valid, expiration_date = check_license()
        
        if not license_valid:
            # Zeige den Dialog an, da die Lizenz ungültig ist
            dialog = LicenseDialog(self)
            self.wait_window(dialog) # Warte, bis der Dialog geschlossen wird
            
            # Prüfe die Lizenz erneut, nachdem der Dialog geschlossen wurde
            license_valid, expiration_date = check_license()
        
        # Zeige die Lizenz-Informationen nur an, wenn die Lizenz gültig ist
        if license_valid:
            expiration_str = "UNBEGRENZT" if expiration_date and expiration_date.year == 9999 else expiration_date.strftime('%d.%m.%Y') if expiration_date else 'UNGÜLTIG'
            license_label = ttk.Label(self.nametowidget("!frame"), text=f"Lizenz gültig bis: {expiration_str}", font=("Helvetica", 9, "italic"))
            license_label.pack(pady=5)
        else:
            # Beende die App, wenn keine gültige Lizenz gefunden wird
            messagebox.showerror("Fehler", "Bitte geben Sie einen gültigen Lizenzschlüssel ein, um das Programm zu starten.")
            self.destroy()

    def launch_mv3d(self):
        self.destroy()
        root = tk.Tk()
        app = MV3DApp(root)
        root.mainloop()

    def launch_gateview(self):
        self.destroy()
        root = tk.Tk()
        app = GateViewApp(root)
        root.mainloop()

if __name__ == "__main__":
    multiprocessing.freeze_support()
    
    try:
        app = Launcher()
        app.mainloop()

    except Exception as e:
        with open("launcher_crash_report.log", "w", encoding='utf-8') as f:
            f.write("Ein kritischer Fehler ist im Launcher aufgetreten:\n\n")
            f.write(traceback.format_exc())
        messagebox.showerror("Kritischer Fehler", "Die Anwendung konnte nicht gestartet werden. Eine Absturzdatei wurde erstellt.")
        sys.exit(1)