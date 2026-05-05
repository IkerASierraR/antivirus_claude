"""
gui/shared/constants.py

Application-wide constants and quick-scan path resolution.
"""

from __future__ import annotations
import os
import sys
from pathlib import Path

APP_NAME = "RustGuard"
APP_VERSION = "1.0.0"

# ── Colors (dark theme) ───────────────────────
COLOR_BG          = "#1a1a1a"
COLOR_BG_PANEL    = "#242424"
COLOR_BG_CARD     = "#2d2d2d"
COLOR_ACCENT      = "#00d4aa"   # Teal accent
COLOR_SAFE        = "#00c853"   # Green
COLOR_THREAT      = "#ff3d3d"   # Red
COLOR_WARNING     = "#ffab00"   # Amber
COLOR_TEXT        = "#e8e8e8"
COLOR_TEXT_DIM    = "#888888"
COLOR_BORDER      = "#3a3a3a"
COLOR_BUTTON_RED  = "#c0392b"
COLOR_BUTTON_HOVER= "#e74c3c"

# ── Quick-scan paths (OS-aware) ───────────────
def get_quick_scan_paths() -> list[str]:
    """Returns high-risk directories for quick scan."""
    home = Path.home()

    if sys.platform == "win32":
        paths = [
            os.environ.get("TEMP", r"C:\Windows\Temp"),
            os.environ.get("TMP",  r"C:\Windows\Temp"),
            str(home / "Downloads"),
            str(home / "Desktop"),
            str(home / "AppData" / "Roaming"),
            str(home / "AppData" / "Local" / "Temp"),
            r"C:\Windows\System32",
        ]
    elif sys.platform == "darwin":
        paths = [
            "/tmp",
            "/var/folders",
            str(home / "Downloads"),
            str(home / "Desktop"),
            str(home / "Library" / "LaunchAgents"),
        ]
    else:  # Linux
        paths = [
            "/tmp",
            "/var/tmp",
            "/dev/shm",
            str(home / "Downloads"),
            str(home / "Desktop"),
            "/etc/cron.d",
            "/etc/init.d",
        ]

    # Only include paths that actually exist
    return [p for p in paths if Path(p).exists()]


def get_full_scan_path() -> str:
    """Root path for a full system scan."""
    if sys.platform == "win32":
        return "C:\\"
    return str(Path.home())  # Scan home directory on Unix (avoids permission issues)
