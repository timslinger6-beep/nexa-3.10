# -*- mode: python ; coding: utf-8 -*-

import os
from pathlib import Path

from PyInstaller.utils.hooks import collect_all

project_root = Path(SPECPATH)
config_path = Path(
    os.environ.get(
        "NEXA_RELEASE_CONFIG_PATH",
        str(project_root / "installer" / "release-config.json"),
    )
)
if not config_path.is_file():
    raise FileNotFoundError(f"Release-Konfiguration fehlt: {config_path}")

crypto_datas, crypto_binaries, crypto_hiddenimports = collect_all("cryptography")

a = Analysis(
    ['installer/NexaInstaller.py'],
    pathex=[str(project_root)],
    binaries=crypto_binaries,
    datas=[
        (str(config_path), '.'),
        (str(project_root / 'NexaRuntime.ico'), '.'),
        *crypto_datas,
    ],
    hiddenimports=crypto_hiddenimports,
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
    name='NexaInstaller',
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
