# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['src/gui/dwh_client.py'],
    pathex=[],
    binaries=[],
    datas=[('resources', 'resources'), ('src', 'src'), ('src/gui/ui_mainwindow.py', 'src/gui/'), ('build/version.txt', './')],
    hiddenimports=['requests'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=2,
)
pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='dwh_client',
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
    icon=['resources/DzlLogoSymmetric.ico'],
)
