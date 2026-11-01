# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller specification file for CleanDownloads.

Produces a standalone, optimized single-file Windows x64 executable (cleandownloads.exe)
with embedded PE version metadata and bundled default configuration.
"""

import os
from pathlib import Path

block_cipher = None
project_root = Path(SPECPATH).resolve()

datas = [
    (str(project_root / "config" / "default_rules.json"), "config"),
]

hiddenimports = [
    "cleandownloads",
    "cleandownloads.cli",
    "cleandownloads.config",
    "cleandownloads.safety",
    "cleandownloads.scanner",
    "cleandownloads.classifier",
    "cleandownloads.organizer",
    "cleandownloads.undo",
    "cleandownloads.history",
    "cleandownloads.scheduler",
    "cleandownloads.preview",
    "ctypes",
    "ctypes.wintypes",
    "sqlite3",
    "winreg",
]

excludes = [
    "tkinter",
    "matplotlib",
    "scipy",
    "numpy",
    "IPython",
    "PIL",
    "pytest",
    "unittest",
    "email",
    "xmlrpc",
    "http.server",
]

a = Analysis(
    [str(project_root / "src" / "cleandownloads" / "cli.py")],
    pathex=[str(project_root / "src")],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="cleandownloads",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version="version_info.txt",
)
