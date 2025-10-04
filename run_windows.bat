@echo off
:: Wechselt in das Verzeichnis, in dem die .bat-Datei liegt
cd /d "%~dp0"

echo Starting Application (window will minimize)...

:: Der 'start "Titel" /min' Befehl startet das Python-Skript in einem neuen, minimierten Fenster.
:: Der erste Parameter in Anführungszeichen ist ein Fenstertitel und wird benötigt.
start "MV3D GateView Analyzer" /min "C:\Users\opper\AppData\Local\Programs\Python\Python313\python.exe" start.py