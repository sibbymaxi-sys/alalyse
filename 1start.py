# start.py
import multiprocessing
import tkinter as tk
from license_dialog import LicenseDialog
from license_validator import check_license
from main_app import MainApplication # Importiere die Klasse

# Dies ist der standardmäßige und sichere Weg, eine Anwendung zu starten.
if __name__ == "__main__":
    multiprocessing.freeze_support()
    
    # Schritt 1: Erstelle das EINZIGE Hauptfenster für die gesamte Anwendung.
    root = tk.Tk()
    root.withdraw() # Halte es unsichtbar, während wir die Lizenz prüfen.

    try:
        license_status = check_license()
        
        if not license_status:
            # Zeige den Dialog. Er "gehört" jetzt zum Hauptfenster.
            dialog = LicenseDialog(root)
            dialog.show()
            license_status = check_license() # Erneut prüfen

        if license_status:
            # Die Lizenz ist gültig. Zerstöre das Fenster NICHT.
            # Lade stattdessen die Hauptanwendung IN das bestehende Fenster.
            root.deiconify() # Mache das Fenster jetzt sichtbar.
            app = MainApplication(root) # Übergib das Hauptfenster an die App.
            root.mainloop()
        else:
            # Keine Lizenz, Programm beenden.
            root.destroy()
            
    except Exception as e:
        print(f"Ein kritischer Fehler ist beim Starten aufgetreten: {e}")
        input("Drücken Sie Enter, um das Fenster zu schließen.")