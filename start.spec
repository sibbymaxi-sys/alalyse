# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['start.py'],
    pathex=[],
    binaries=[],
    datas=[('app_config.json', '.'), ('C:\\Users\\opper\\AppData\\Local\\Programs\\Python\\Python313\\Lib\\site-packages\\sv_ttk', 'sv_ttk'), ('C:\\Users\\opper\\AppData\\Local\\Programs\\Python\\Python313\\Lib\\site-packages\\tkcalendar', 'tkcalendar')],
    hiddenimports=[],
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
    name='start',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
