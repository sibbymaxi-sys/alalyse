# -*- coding: utf-8 -*-
#
# Spec file for building the GateView application with PyInstaller.
#
# To use, run: pyinstaller --onefile GateView.spec

block_cipher = None

a = Analysis(
    ['start.py'],
    pathex=['D:\\ClearScanAnalyzer\\neue_Vers\\ver3\\test_V5'],  # Pfad zu deinem Projektverzeichnis
    binaries=[],
    datas=[
        # Füge die config.ini hinzu
        ('config.ini', '.'),
        # Füge die requirements.txt hinzu
        ('requirements.txt', '.'),
        # Füge andere nicht-python Dateien hinzu, z.B. aus einem Ordner 'data'
        # ('data/somefile.csv', 'data'),
    ],
    hiddenimports=[
        # Füge alle Python-Module hinzu, die PyInstaller nicht automatisch findet.
        "tkinter"
        "advanced_search_dialog", 
        "analysis_engine", 
        "base_app",
        "bhs_log_parser", 
        "bms_log_parser", 
        "check_dependencies", 
        "clearscan_error_definitions", 
        "config_manager", 
        "data_processor", 
        "dpp_log_parser", 
        "error_analyzer", 
        "error_definitions", 
        "error_manager", 
        "fault_translator", 
        "fsm_log_parser", 
        "ftp_client", 
        "ftp_dialog", 
        "ftp_dialog_advanced", 
        "ftp_dialog_gateview", 
        "ftp_dialog_mv3d", 
        "gateview_app", 
        "gateview_casefile_window", 
        "gateview_system_analyzer", 
        "gatview_example", 
        "generate_installer", 
        "help_texts", 
        "installer", 
        "iqtk_log_parser", 
        "license_dialog", 
        "license_generator", 
        "license_manager", 
        "license_validator", 
        "log_parser", 
        "log_previewer", 
        "main_app", 
        "main_window", 
        "mv3d_app", 
        "mv3d_definitions", 
        "mv3d_log_parser", 
        "parser", 
        "plc_log_parser", 
        "scs_log_parser", 
        "sftp_log_window", 
        "sftp_status_window", 
        "system_analyzer_app", 
        "test_license_system", 
        "timespan_dialog"
    ],
    hookspath=[],
    runtime_hooks=[],
        win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)

# Füge die notwendigen Dateien hinzu, um die .exe auszuführen
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='GateView',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    # This is the line that makes it a single file
    onefile=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)