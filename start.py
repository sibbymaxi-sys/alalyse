# start.py
import tkinter as tk
import multiprocessing
import os
import sys
import traceback
from tkinter import messagebox

# --- WICHTIG: freeze_support() MUSS als ERSTES im Skript stehen ---
# --- (nach den Imports, aber vor JEDEM anderen Code) ---
if __name__ == "__main__":
    multiprocessing.freeze_support()
    print(f"--- Running __main__ block in start.py (PID: {os.getpid()}) ---")

    try:
        # Importiere die Haupt-App-Klasse
        from main_app import MainApplication
        
        # Erstelle das Hauptfenster
        root = tk.Tk()
        # Erstelle die App-Instanz und übergib 'root' als Parent
        app = MainApplication(parent=root) 
        # Starte die App
        root.mainloop()
        
    except Exception as e:
        # Fängt alle Fehler beim Starten ab
        print(f"\n--- FATALER FEHLER BEIM APP-START ---")
        print(f"Fehlertyp: {type(e).__name__}")
        print(f"Meldung: {e}\n")
        print("--- Traceback ---")
        traceback.print_exc()
        try:
            # Versuche, den Fehler in einem Notfall-Fenster anzuzeigen
            root_err = tk.Tk()
            root_err.withdraw()
            messagebox.showerror("Kritischer Startfehler", f"App konnte nicht gestartet werden:\n{e}\n\nSiehe Konsole.")
        except Exception:
            pass # Wenn selbst Tkinter nicht geladen werden kann
        input("\nDrücken Sie Enter, um das Fenster zu schließen...")

    print(f"--- Exiting __main__ block in start.py (PID: {os.getpid()}) ---")