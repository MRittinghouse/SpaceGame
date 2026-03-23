# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for SpaceGame (onedir build)."""

import os

block_cipher = None

a = Analysis(
    ["spacegame/main.py"],
    pathex=[],
    binaries=[],
    datas=[
        ("data", "data"),                       # JSON game content
        ("spacegame/data", "spacegame/data"),   # Assets, theme, audio
    ],
    hiddenimports=[
        "tkinter",
        "tkinter.filedialog",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "pytest",
        "black",
        "pylint",
        "mypy",
        "pip",
        "setuptools",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Aurelia",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # Windowed app, no console
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=("spacegame/data/assets/images/icon.ico" if os.path.exists("spacegame/data/assets/images/icon.ico") else None),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="Aurelia",
)
