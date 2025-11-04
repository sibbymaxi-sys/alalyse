# check_import.py
import sys
import os
import importlib.machinery # Alternative Importmethode
import traceback # Fehlenden Import hinzugefügt

print("--- Python Suchpfade (sys.path): ---")
for p in sys.path:
    print(p)
print("-" * 30)

target_file = "mv3d_error_definitions.py"
target_path = os.path.abspath(target_file)
print(f"Versuche Modul zu laden von: {target_path}")

if not os.path.exists(target_path):
    print(f"FEHLER: Datei nicht gefunden: {target_path}")
else:
    try:
        # Versuche, das Modul gezielt über den Pfad zu laden (alternative Methode)
        loader = importlib.machinery.SourceFileLoader("mv3d_error_definitions", target_path)
        mv3d_defs = loader.load_module() # Lade das Modul

        print("--- Modul erfolgreich geladen via Pfad ---")

        # Prüfe, ob die Funktion im geladenen Modul existiert
        if hasattr(mv3d_defs, 'get_mv3d_fc_code_details'):
             print(">>> SUCCESS: Funktion 'get_mv3d_fc_code_details' im Modul gefunden!")
        else:
             print(">>> FEHLER: Funktion 'get_mv3d_fc_code_details' NICHT im geladenen Modul gefunden!")
             print("   Verfügbare Namen im Modul (Auszug):")
             # Zeige verfügbare Namen (ohne interne '__' Namen)
             available_names = [name for name in dir(mv3d_defs) if not name.startswith('_')]
             print(f"   {available_names}")

    except SyntaxError as se:
        print(f"\n--- SYNTAXFEHLER in {target_file} ---")
        print(f"Fehler: {se}")
        print(f"Zeile: {se.lineno}, Position: {se.offset}")
        # Versuche, die fehlerhafte Zeile zu lesen und anzuzeigen
        try:
            with open(target_path, 'r') as f_err:
                lines = f_err.readlines()
                if se.lineno is not None and 1 <= se.lineno <= len(lines):
                     print(f"Codezeile: {lines[se.lineno-1].strip()}")
                else:
                     print(f"Codezeile (konnte nicht ermittelt werden): {se.text.strip() if se.text else 'N/A'}")
        except Exception:
            print(f"Codezeile (konnte nicht gelesen werden): {se.text.strip() if se.text else 'N/A'}")
        print("-" * 30)
    except ImportError as ie: # Fange spezifische ImportErrors innerhalb der Datei ab
         print(f"\n--- IMPORTFEHLER INNERHALB von {target_file} ---")
         print(f"Fehler: {ie}")
         print(f"Traceback:\n{traceback.format_exc()}")
         print("-" * 30)
    except Exception as e:
        print(f"\n--- ANDERER FEHLER beim Laden von {target_file} ---")
        print(f"Fehlertyp: {type(e).__name__}")
        print(f"Meldung: {e}")
        print(f"Traceback:\n{traceback.format_exc()}") # traceback ist jetzt importiert
        print("-" * 30)

input("\nDrücken Sie Enter zum Beenden...")