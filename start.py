# -*- coding: utf-8 -*-
# start.py
import tkinter as tk
from tkinter import ttk
import sv_ttk
import traceback
import sys
import multiprocessing # <-- This line was missing

from license_validator import check_license
from license_dialog import LicenseDialog
from mv3d_app import MV3DApp
from gateview_app import GateViewApp

class Launcher(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Programm auswählen")
        self.geometry("400x200")
        sv_ttk.set_theme("dark")
        main_frame = ttk.Frame(self, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        ttk.Label(main_frame, text="Welches Programm möchten Sie starten?", font=("Helvetica", 12)).pack(pady=10)
        ttk.Button(main_frame, text="MV3D System Analyser", command=self.launch_mv3d, style='Accent.TButton').pack(pady=10, fill=tk.X)
        ttk.Button(main_frame, text="Clear Scan Analyser", command=self.launch_gateview).pack(pady=10, fill=tk.X)

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
        if not check_license():
            root = tk.Tk()
            root.withdraw()
            dialog = LicenseDialog(root, license_status=check_license())
            if not dialog.show():
                sys.exit(0)
            root.destroy()
        
        launcher_app = Launcher()
        launcher_app.mainloop()

    except Exception as e:
        with open("launcher_crash_report.log", "w", encoding='utf-8') as f:
            f.write("Ein kritischer Fehler ist im Launcher aufgetreten:\n\n")
            f.write(traceback.format_exc())