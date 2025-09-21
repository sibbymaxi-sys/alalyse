@echo off
SETLOCAL

ECHO ----------------------------------------------------
ECHO  Ueberpruefe und installiere notwendige Bibliotheken
ECHO ----------------------------------------------------

REM Pruefe, ob die 'py' oder 'python' Befehle funktionieren
py --version >NUL 2>&1
IF %ERRORLEVEL% NEQ 0 (
    ECHO Der 'py' Befehl wurde nicht gefunden. Versuche 'python' stattdessen.
    python --version >NUL 2>&1
    IF %ERRORLEVEL% NEQ 0 (
        ECHO Kritischer Fehler: Weder 'py' noch 'python' ist im Systempfad.
        ECHO Bitte stellen Sie sicher, dass Python korrekt installiert ist und zum PATH hinzugefuegt wurde.
        ECHO Moeglicherweise muessen Sie Python neu installieren und die Option 'Add Python to PATH' waehlen.
        pause
        ENDLOCAL
        EXIT /B 1
    )
)

ECHO Erstelle und aktiviere virtuelle Umgebung...
IF NOT EXIST .venv (
  py -3 -m venv .venv
)

CALL .venv\Scripts\activate

ECHO Installiere Python-Abhaengigkeiten aus requirements.txt...
pip install -r requirements.txt

ECHO Starte den GateView Log Analyzer...
python main_app.py

ENDLOCAL
pause