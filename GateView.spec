# -*- coding: utf-8 -*-
#
# Optimierte Spec-Datei für den Bau der GateView-Anwendung mit PyInstaller.
#
# Ausführung im Terminal (im Projekt-Stammverzeichnis):
# pyinstaller GateView.spec

from PyInstaller.utils.hooks import collect_data_files

# Wir definieren den Namen der Anwendung hier einmal zentral
APP_NAME = 'GateView'

# PyInstaller sollte Tcl/Tk und sv_ttk automatisch finden. 
# Falls nicht, ist dies der saubere Weg, die Daten explizit einzubinden.
datas = collect_data_files('sv_ttk')

# Füge weitere notwendige Dateien hinzu, die im Hauptverzeichnis liegen sollen.
# requirements.txt wird normalerweise nicht für die fertige Anwendung benötigt.
datas += [
    ('config.ini', '.')
]

a = Analysis(
    ['start.py'],  # Der Einstiegspunkt deines Programms
    pathex=['.'],    # Suche nach Modulen im aktuellen Verzeichnis (keine festen Pfade!)
    binaries=[],
    datas=datas,     # Verwendet die oben definierte, saubere Datenliste
    hiddenimports=[
        # Diese Liste ist gut, um sicherzustellen, dass alle deine Module gefunden werden.
        # PyInstaller findet viele davon oft selbst, aber es schadet nicht, sie explizit aufzuführen.
        'tkinter', 'sv_ttk', 'traceback', 'sys', 'multiprocessing', 'os', 're', 
        'datetime', 'pandas', 'shutil', 'numpy', 'tkcalendar', 'reportlab',
        
        # --- Deine Projektmodule ---
        "advanced_search_dialog", "analysis_engine", "base_app", "bhs_log_parser",
        "bms_log_parser", "brava_log_parser", "check_dependencies", 
        "clearscan_error_definitions", "config_manager", "data_processor", 
        "dpp_log_parser", "error_analyzer", "error_definitions", "error_manager", 
        "fault_translator", "fsm_log_parser", "ftp_client", "ftp_dialog_advanced", 
        "gateview_app", "gateview_system_analyzer", "help_texts", "log_parser",
        "license_dialog", "license_validator", "mv3d_app", "mv3d_definitions", 
        "plc_log_parser", "scs_log_parser", "sftp_log_window", "system_analyzer_app",
        "timespan_dialog"
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,               # Wichtig für GUI-Anwendungen: Kein Konsolenfenster
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    
)