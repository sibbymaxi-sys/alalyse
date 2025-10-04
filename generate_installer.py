import os
import sys

# Das Installations- und Deinstallations-Skript wird in Python geschrieben
# und verwendet die Standardbibliothek os und sys

INSTALLER_TEMPLATE = """
import os
import shutil
import subprocess
import sys

def uninstall_app():
    install_dir = os.path.join(os.environ['APPDATA'], "{app_name}")
    
    if os.path.exists(install_dir):
        print(f"Deinstalliere {app_name} von {{install_dir}}...")
        shutil.rmtree(install_dir)
        print("Deinstallation abgeschlossen.")
    else:
        print("Anwendung nicht gefunden. Keine Aktion erforderlich.")

if __name__ == "__main__":
    uninstall_app()
    input("Drücken Sie Enter, um das Fenster zu schließen...")
\"\"\"
    
    uninstaller_path = os.path.join(os.environ['APPDATA'], "{app_name}", "uninstaller.py")
    with open(uninstaller_path, "w") as f:
        f.write(uninstaller_code)

if __name__ == "__main__":
    install_app()
    create_uninstaller_script()
    input("Drücken Sie Enter, um das Installationsprogramm zu beenden...")
"""
# Template für die setup.py Datei von cx_Freeze
SETUP_TEMPLATE = """
import sys
from cx_Freeze import setup, Executable

# Definiere die Haupt-Python-Datei deines Projekts
main_script = '{main_script}'

# Füge alle weiteren Dateien hinzu, die deine App benötigt (z.B. CSV, TXT, etc.)
include_files = [
    # Hier kannst du zusätzliche Dateien auflisten, z.B. ('config.ini', 'config.ini')
]

build_exe_options = {{
    "includes": [{includes}],
    "include_files": include_files,
    "excludes": ["tkinter"],
}}

base = None
if sys.platform == "win32":
    # Verwende 'Win32GUI' für Apps mit grafischer Oberfläche, um die Konsole zu verstecken
    # Für Konsolen-Apps dies auskommentieren: base = "Win32GUI"
    base = "Win32GUI"

setup(
    name="{}",
    version="1.0",
    description="Ein Installer für deine Analyse-App",
    options={{"build_exe": build_exe_options}},
    executables=[Executable(main_script, base=base)]
)
"""

def generate_files():
    """Generiert alle notwendigen Dateien für den Build-Prozess."""
    
    # 1. Benutzerinteraktion zur Bestimmung des Hauptskripts und des App-Namens
    all_py_files = [f for f in os.listdir('.') if f.endswith('.py')]
    print("Gefundene Python-Skripte:")
    for i, f in enumerate(all_py_files):
        print(f"[{i+1}] {f}")
    
    main_script_index = int(input("Wähle das Hauptskript (Nummer): ")) - 1
    main_script = all_py_files[main_script_index]
    
    app_name = input("Gib den Namen deiner App ein: ")
    
    # 2. Generiere die setup.py-Datei
    # Wir nehmen alle anderen .py-Dateien als potentielle Includes an
    includes = [f.replace('.py', '') for f in all_py_files if f != main_script]
    
    with open("setup.py", "w") as f:
        f.write(SETUP_TEMPLATE.format(app_name, main_script=main_script, includes=', '.join(f'"{i}"' for i in includes)))
    print("setup.py erfolgreich erstellt.")
    
    # 3. Generiere die Installer- und Uninstaller-Skripte
    with open("installer.py", "w") as f:
        f.write(INSTALLER_TEMPLATE.format(app_name=app_name))
    print("installer.py erfolgreich erstellt.")

if __name__ == "__main__":
    generate_files()