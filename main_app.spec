# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main_app.py'],
    pathex=[],
    binaries=[],
    datas=[('C:\\Users\\opper\\AppData\\Local\\Programs\\Python\\Python313\\Lib\\site-packages\\sv_ttk', 'sv_ttk'), ('C:\\Users\\opper\\AppData\\Local\\Programs\\Python\\Python313\\Lib\\site-packages\\tkcalendar', 'tkcalendar'), ('app_config.json', '.')],
    hiddenimports=['pandas', 'sv_ttk', 'tkcalendar', 'reportlab', 'paramiko'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='main_app',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
