# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path
import runpy


project_root = Path(SPECPATH)
release_metadata = runpy.run_path(str(project_root / 'scripts' / 'release_metadata.py'))
version_info_path = release_metadata['write_windows_version_info'](
    project_root,
    Path(workpath) / 'windows_version_info.txt',
)
icon_path = project_root / 'assets' / 'santa-rubi-app.ico'

a = Analysis(
    [str(project_root / 'app.py')],
    pathex=[],
    binaries=[],
    datas=[(str(icon_path), 'assets')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # Dependências opcionais do openpyxl presentes no ambiente global não
    # fazem parte do aplicativo. A exclusão explícita mantém o build igual
    # ao ambiente limpo descrito em requirements-release.txt.
    excludes=['numpy', 'pandas'],
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
    name='Santa Rubi Label Studio',
    icon=str(icon_path),
    version=str(version_info_path),
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
