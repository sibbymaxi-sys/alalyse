# main_app.py
import tkinter as tk
from tkinter import ttk
import sv_ttk
from gateview_app import GateViewApp
from mv3d_app import MV3DApp

class MainApplication(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Universal Log Analyzer")
        self.geometry("400x250")
        self.protocol("WM_DELETE_WINDOW", self.quit)

        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - (self.winfo_width() // 2)
        y = (self.winfo_screenheight() // 2) - (self.winfo_height() // 2)
        self.geometry(f'+{x}+{y}')
        
        # **NEU:** Start im dunklen Design
        sv_ttk.set_theme("dark")

        main_frame = ttk.Frame(self, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main_frame, text="Bitte wählen Sie ein Analyse-Modul:", font=("Helvetica", 14)).pack(pady=10)
        ttk.Button(main_frame, text="GateView Analyzer öffnen", command=self.open_gateview).pack(pady=10, fill=tk.X)
        ttk.Button(main_frame, text="MV3D Analyzer öffnen", command=self.open_mv3d).pack(pady=10, fill=tk.X)

    def open_gateview(self):
        win = tk.Toplevel(self)
        app = GateViewApp(win)
        app.pack(fill="both", expand=True)

    def open_mv3d(self):
        win = tk.Toplevel(self)
        app = MV3DApp(win)
        app.pack(fill="both", expand=True)

if __name__ == "__main__":
    app = MainApplication()
    app.mainloop()