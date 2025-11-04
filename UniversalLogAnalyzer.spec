# UniversalLogAnalyzer.spec

import sys
import os

# --- KORREKTER PFAD ---
# Nutzt den exakten Pfad, den du angegeben hast
site_packages_path = r"C:\Users\opper\AppData\Local\Programs\Python\Python313\Lib\site-packages"

# Liste aller deiner lokalen .py-Module, die PyInstaller finden muss
local_modules = [
    'base_app',
    'config_manager',
    'help_texts',
    'license_dialog',
    'license_validator',
    'log_previewer',
    
    # GateView / ClearScan Module
    'gateview_app',
    'system_analyzer_app',
    'log_parser',
    'oms_log_parser',
    'brava_log_parser',
    'data_processor',
    'advanced_search_dialog',
    'ftp_dialog_advanced',
    'ftp_client',
    'sftp_log_window',
    'gateview_casefile_window',
    'clearscan_error_definitions', # Originalname
    'cs_error_definitions',        # Umbenannter Name (sicherheitshalber beide)
    
    # MV3D Module
    'mv3d_app',
    'mv3d_system_analyzer_app',
    'mv3d_log_parser',
    'mv3d_casefile_window',
    'mv3d_definitions',
    'mv3d_error_definitions',
    'ftp_dialog', # Wird von mv3d_app genutzt
    
    # Geteilte Parser-Module
    'scs_log_parser',
    'bhs_log_parser',
    'bms_log_parser',
    'dpp_log_parser',
    'fsm_log_parser',
    'plc_definitions',
    'fault_translator'
]

# Liste externer Bibliotheken
external_libs = [
    'pandas',
    'sv_ttk',
    'tkcalendar',
    'paramiko', # Für SSH/SFTP
    'reportlab',
    'reportlab.platypus',
    'reportlab.lib.pagesizes',
    'reportlab.lib.styles',
    'reportlab.lib.enums'
]

# Datendateien, die PyInstaller kopieren muss
data_files = []
try:
    # Prüfe, ob die Pfade existieren
    sv_ttk_path = os.path.join(site_packages_path, 'sv_ttk')
    tkcalendar_path = os.path.join(site_packages_path, 'tkcalendar')

    if os.path.exists(sv_ttk_path):
        data_files.append((sv_ttk_path, 'sv_ttk'))
    else:
        print(f"WARNUNG: sv_ttk-Datenpfad nicht gefunden: {sv_ttk_path}")

    if os.path.exists(tkcalendar_path):
        data_files.append((tkcalendar_path, 'tkcalendar'))
    else:
        print(f"WARNUNG: tkcalendar-Datenpfad nicht gefunden: {tkcalendar_path}")
        
    # --- app_config.json HINZUGEFÜGT ---
    if os.path.exists('app_config.json'):
        data_files.append(('app_config.json', '.')) # Kopiert app_config.json ins Hauptverzeichnis
    else:
        print("WARNUNG: 'app_config.json' nicht im Hauptverzeichnis gefunden.")
        
except Exception as e:
    print(f"FEHLER beim Erstellen der data_files-Liste: {e}")


a = Analysis(
    ['main_app.py'], # Dein Haupt-Startskript
    pathex=[],
    binaries=[],
    datas=data_files,
    hiddenimports=local_modules + external_libs, # Fügt alle Module hinzu
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='UniversalLogAnalyzer', # Name der .exe Datei
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False, # WICHTIG: False = Fenster-Anwendung (keine Konsole)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None # KEIN ICO wie gewünscht
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='UniversalLogAnalyzer' # Name des Ausgabeordners
)