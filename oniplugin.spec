# -*- mode: python ; coding: utf-8 -*-

import os
import sys
from pathlib import Path

# Ensure we collect all necessary dependencies
block_cipher = None

def get_pandas_path():
    import pandas
    return os.path.dirname(pandas.__file__)

def get_site_packages():
    import site
    return site.getsitepackages()[0]

# Add any additional data files needed
added_files = [
    ('version.py', '.'),
    # Add any other data files your program needs
]

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=added_files,
    hiddenimports=[
        'packaging',
        'packaging.version',
        'packaging.specifiers',
        'packaging.requirements',
        'pathlib',
        'ctypes',
        'json',
        'logging',
        'shutil',
        'subprocess',
        'site',
        'os',
        'sys',
        'pip',
        'pip._internal',
        'pip._internal.commands',
        'pip._internal.commands.install',
        'setuptools',
        'distutils',
        'pkg_resources',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False
)

pyz = PYZ(
    a.pure,
    a.zipped_data,
    cipher=block_cipher
)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='OniPlugin',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico' if os.path.exists('icon.ico') else None,
    version_info=None  # Remove version file reference since we're using version_info
)

# Create dist directory if it doesn't exist
if not os.path.exists('dist'):
    os.makedirs('dist')

