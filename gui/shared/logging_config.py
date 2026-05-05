"""
gui/shared/logging_config.py

Centralized logging: writes to both console and rotating log file.
"""

from __future__ import annotations
import logging
import logging.handlers
from pathlib import Path


def setup_logging(log_dir: str | None = None) -> None:
    """Configure root logger with file + console handlers."""
    if log_dir is None:
        app_dir = Path(__file__).parent.parent.parent
        log_dir = str(app_dir / "logs")

    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger("rustguard")
    root.setLevel(logging.DEBUG)

    # Console handler (INFO+)
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S"
    ))

    # Rotating file handler (DEBUG+, max 5 MB × 3 files)
    file_handler = logging.handlers.RotatingFileHandler(
        log_path / "rustguard.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)-8s] %(name)s: %(message)s"
    ))

    root.addHandler(console)
    root.addHandler(file_handler)
