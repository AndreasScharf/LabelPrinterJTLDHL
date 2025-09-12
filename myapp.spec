# myapp.spec  (ONEDIR)
# Run: pyinstaller --clean myapp.spec
# -*- mode: python ; coding: utf-8 -*-

import os
from pathlib import Path
from PyInstaller.utils.hooks import (
    collect_submodules, collect_data_files, collect_dynamic_libs
)
from PyInstaller.building.datastruct import Tree, TOC
import shutil

APP_NAME     = "JTLVersandAufkleber"
ENTRY_SCRIPT = "main.py"

# Use the working directory from which you run `pyinstaller myapp.spec`
PROJECT_DIR   = Path(os.getcwd()).resolve()
ASSETS_SRC    = PROJECT_DIR / "assets"
ASSETS_TARGET = "assets"
ICON_FILE     = ASSETS_SRC / "myicon.ico"

DIST_DIR = PROJECT_DIR / "dist"
EXE_DIR = DIST_DIR  # onefile puts exe directly in dist/
EXE_PATH = EXE_DIR / f"{APP_NAME}.exe"

hiddenimports  = collect_submodules("weasyprint") + collect_submodules("lxml")
weasy_datas    = collect_data_files("weasyprint")
weasy_binaries = collect_dynamic_libs("weasyprint")

if not ASSETS_SRC.is_dir():
    raise FileNotFoundError(f"Expected assets folder at: {ASSETS_SRC}")

a = Analysis(
    [str(PROJECT_DIR / ENTRY_SCRIPT)],
    pathex=[str(PROJECT_DIR)],
    binaries=weasy_binaries,
    datas=weasy_datas,    # library data (not your project assets)
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=APP_NAME,
    console=False,
    icon=str(ICON_FILE) if ICON_FILE.exists() else None,
)

# Everything collected under dist/JTLVersandAufkleber/
collect_items = [exe, a.binaries, a.zipfiles, a.datas]

# This ensures assets end up under dist/JTLVersandAufkleber/assets/
collect_items.append(Tree(str(ASSETS_SRC), prefix=ASSETS_TARGET))

# Optionally drop a couple of files under assets/
extra_files = TOC()
for fname in ("labels.html", ".env"):
    src = PROJECT_DIR / fname
    if src.is_file():
        extra_files.append((os.path.join(ASSETS_TARGET, src.name), str(src), "DATA"))
if extra_files:
    collect_items.append(extra_files)

coll = COLLECT(
    *collect_items,
    strip=False,
    upx=True,
    upx_exclude=[],
    name=APP_NAME,               # <-- creates dist/JTLVersandAufkleber/
    # distpath=str(PROJECT_DIR / "dist"),  # optional, explicit dist path
)


# No COLLECT in onefile; instead finalize and then copy files
# Use a tiny post-build step:
def _post_build():
    INSIDE_EXE_DIR = EXE_DIR / f"{APP_NAME}"
    target_assets = INSIDE_EXE_DIR / "assets"
    print(target_assets)
    if target_assets.exists():
        shutil.rmtree(target_assets)
    shutil.copytree(ASSETS_SRC, target_assets)

# Trigger the post-build copy when spec is executed as a script
_post_build()