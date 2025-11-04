@echo off
cd /d "%~dp0"

set PYTHON_EXE="C:\Users\opper\AppData\Local\Programs\Python\Python313\python.exe"

echo Starte den ultimativen Test...
%PYTHON_EXE% ultimate_test.py

pause