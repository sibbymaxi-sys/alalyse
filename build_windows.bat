@echo off
SETLOCAL

ECHO ----------------------------------------------------
ECHO            GateView Analyzer Build-Skript
ECHO ----------------------------------------------------

ECHO.
ECHO Aktiviere virtuelle Umgebung...
CALL .venv\Scripts\activate

ECHO.
ECHO Loesche alte Build-Verzeichnisse...
IF EXIST build ( RMDIR /S /Q build )
IF EXIST dist ( RMDIR /S /Q dist )

ECHO.
ECHO Starte den Build-Prozess mit PyInstaller...
ECHO Dies kann einige Minuten dauern.
ECHO.

pyinstaller --onefile --windowed --name "GateView Universal Analyzer" ^
--add-data ".venv\Lib\site-packages\sv_ttk;sv_ttk" ^
--add-data ".venv\Lib\site-packages\tkcalendar;tkcalendar" ^
main_app.py

ECHO.
ECHO ----------------------------------------------------
ECHO Build abgeschlossen!
ECHO ----------------------------------------------------
ECHO.
ECHO Sie finden die fertige .exe-Datei im folgenden Verzeichnis:
ECHO %~dp0dist
ECHO.

ENDLOCAL
pause