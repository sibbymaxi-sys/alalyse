# main_app.py
import tkinter as tk
from tkinter import ttk, messagebox
import sv_ttk
from gateview_app import GateViewApp

# Erbt jetzt von ttk.Frame statt von tk.Tk
class MainApplication(ttk.Frame):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        
        self.parent = parent
        
        self.parent.title("Universal Log Analyzer")
        self.parent.geometry("400x250")
        
        self.pack(fill=tk.BOTH, expand=True)

        sv_ttk.set_theme("dark")

        main_frame = ttk.Frame(self, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main_frame, text="Bitte wählen Sie ein Analyse-Modul:", font=("Helvetica", 14)).pack(pady=10)
        ttk.Button(main_frame, text="GateView Analyzer öffnen", command=self.open_gateview).pack(pady=10, fill=tk.X)
        
        ttk.Button(main_frame, text="MV3D Analyzer öffnen", command=self.open_mv3d).pack(pady=10, fill=tk.X)
        
    def open_gateview(self):
        # Erstelle das neue Fenster
        win = tk.Toplevel(self.parent) 
        app = GateViewApp(win)
        app.pack(fill="both", expand=True)

        # NEU: Sorge dafür, dass das Schließen des Fensters die ganze App beendet
        win.protocol("WM_DELETE_WINDOW", self.parent.destroy)
        
        # NEU: Verstecke das Auswahlfenster, anstatt es zu zerstören
        self.parent.withdraw()

    def open_mv3d(self):
        try:
            from mv3d_app import MV3DApp
            
            # Erstelle das neue Fenster
            win = tk.Toplevel(self.parent)
            app = MV3DApp(win)
            app.pack(fill="both", expand=True)
            
            # NEU: Sorge dafür, dass das Schließen des Fensters die ganze App beendet
            win.protocol("WM_DELETE_WINDOW", self.parent.destroy)

            # NEU: Verstecke das Auswahlfenster, anstatt es zu zerstören
            self.parent.withdraw()
            
        except ImportError as e:
            messagebox.showerror("Fehler", f"MV3D Analyzer konnte nicht geladen werden.\n\nFehler: {e}\n\nStellen Sie sicher, dass alle benötigten Dateien vorhanden sind.")
        except Exception as e:
            messagebox.showerror("Fehler", f"Ein unerwarteter Fehler ist beim Öffnen des MV3D Analyzers aufgetreten:\n\n{e}")