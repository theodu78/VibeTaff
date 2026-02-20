# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files

datas = []
datas += collect_data_files('sentence_transformers')
datas += collect_data_files('lancedb')


a = Analysis(
    ['/Users/th30/Documents/Projets/DEV/VibeTaff/backend/main.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=['uvicorn.logging', 'uvicorn.lifespan.on', 'uvicorn.lifespan.off', 'uvicorn.lifespan', 'uvicorn.protocols.http.auto', 'uvicorn.protocols.http.h11_impl', 'uvicorn.protocols.websockets.auto', 'uvicorn.loops.auto', 'uvicorn.loops.asyncio', 'multipart', 'dotenv'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'PIL', 'IPython', 'notebook', 'pytest'],
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
    name='vibetaff-backend',
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
