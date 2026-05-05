# rustguard.spec
#
# PyInstaller spec file for RustGuard
# Usage: pyinstaller rustguard.spec
#
# This spec file:
#   1. Collects customtkinter's data files (themes, fonts, images)
#   2. Bundles the compiled Rust .pyd/.so as a binary
#   3. Includes signatures/, logs/, quarantine/ directories
#   4. Produces a single-folder distribution (use --onefile flag for .exe)

import sys
import os
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

# ── Project root (where this .spec lives) ────────
ROOT = Path(SPECPATH)

# ── Collect customtkinter themes + assets ────────
ctk_datas = collect_data_files("customtkinter", include_py_files=False)

# ── Collect the compiled Rust scan_engine ────────
# maturin places the .pyd (Windows) or .so (Linux/macOS) in gui/
# We include it as a binary so PyInstaller copies + includes it properly.
import glob
rust_bins = []
for ext in ("*.pyd", "*.so", "*.dylib"):
    found = glob.glob(str(ROOT / "gui" / ext))
    rust_bins.extend((f, ".") for f in found)

# ── Main analysis ─────────────────────────────────
a = Analysis(
    [str(ROOT / "gui" / "main.py")],
    pathex=[str(ROOT)],
    binaries=rust_bins,
    datas=[
        # customtkinter assets
        *ctk_datas,
        # Application data directories (created at runtime if missing)
        (str(ROOT / "signatures"), "signatures"),
    ],
    hiddenimports=[
        "customtkinter",
        "tkinter",
        "tkinter.filedialog",
        "scan_engine",   # Rust extension
        "PIL",
        "PIL.Image",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "matplotlib", "numpy", "pandas", "scipy",   # Not needed
        "test", "unittest",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

# ── Single executable ─────────────────────────────
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="RustGuard",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,                # Use UPX compression if available
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,           # No terminal window on Windows
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon="assets/icon.ico",  # Uncomment and provide icon file
)
