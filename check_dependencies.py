# check_dependencies.py
import os
from modulefinder import ModuleFinder
import sys

# Die Hauptdatei, mit der Ihre Anwendung gestartet wird
main_script_to_analyze = 'start.py'
output_filename = 'file_list.txt'
project_directory = os.path.dirname(os.path.abspath(main_script_to_analyze))

print(f"Analysiere das Projekt im Verzeichnis: {project_directory}")
print(f"Starte mit der Hauptdatei: {main_script_to_analyze}\n")

# Finde alle importierten Python-Module
finder = ModuleFinder()
try:
    finder.run_script(main_script_to_analyze)
except Exception as e:
    print(f"FEHLER: Konnte '{main_script_to_analyze}' nicht analysieren. Grund: {e}")
    sys.exit(1)

# Filtere nur die Dateien heraus, die sich in unserem Projektordner befinden
local_project_files = set()
for mod in finder.modules.values():
    # Überprüfe, ob die Modul-Datei existiert und im Projektverzeichnis liegt
    if mod.__file__ and os.path.dirname(os.path.abspath(mod.__file__)).startswith(project_directory):
        relative_path = os.path.relpath(mod.__file__, project_directory)
        local_project_files.add(relative_path.replace('\\', '/'))

# Füge das Hauptskript selbst hinzu, falls es fehlt
local_project_files.add(main_script_to_analyze)

# Suche nach anderen wichtigen Dateitypen im Verzeichnis
for root, _, files in os.walk(project_directory):
    for file in files:
        if file.endswith(('.bat', '.json')):
            relative_path = os.path.relpath(os.path.join(root, file), project_directory)
            local_project_files.add(relative_path.replace('\\', '/'))

# Sortiere die Liste alphabetisch
sorted_files = sorted(list(local_project_files))

print("--- Gefundene und benötigte Projektdateien ---")
with open(output_filename, 'w', encoding='utf-8') as f:
    for file_path in sorted_files:
        print(file_path)
        f.write(file_path + '\n')

print(f"\nFertig! Eine vollständige Liste wurde in der Datei '{output_filename}' gespeichert.")