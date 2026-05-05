"""
gui/infrastructure/scanner/rust_engine_adapter.py

Infrastructure layer — concrete implementation of IScanEngine.
Wraps the compiled Rust `scan_engine` PyO3 module.

Falls back to a pure-Python stub if the Rust .so/.pyd is not yet compiled,
so the project can be developed and UI-tested without needing Rust.
"""

from __future__ import annotations
import logging
import os
from pathlib import Path
from typing import Callable

logger = logging.getLogger("rustguard.engine")

# ── Attempt to import compiled Rust module ─────
try:
    import scan_engine as _rust  # type: ignore
    RUST_AVAILABLE = True
    logger.info("Rust scan engine loaded successfully.")
except ImportError:
    RUST_AVAILABLE = False
    logger.warning(
        "Rust scan engine NOT available. Running with Python stub. "
        "Run `maturin develop` to compile it."
    )


# ── Fallback Python stub (dev/testing only) ────────────────────────────────

class _PythonStubResult:
    """Mimics the Rust FileScanResult struct for testing."""
    def __init__(self, path: str):
        self.path = path
        self.sha256 = ""
        self.md5 = ""
        self.is_threat = False
        self.threat_name = ""
        self.detection_method = "clean"
        self.file_size = 0
        self.error = "Rust engine not compiled — stub result"


class _PythonStubSummary:
    def __init__(self):
        self.total_files = 0
        self.threats_found = 0
        self.skipped_files = 0
        self.was_cancelled = False
        self.threats = []


class _PythonStubToken:
    def __init__(self):
        self._cancelled = False

    def cancel(self): self._cancelled = True
    def reset(self): self._cancelled = False
    def is_cancelled(self): return self._cancelled


# ── Concrete Adapter ────────────────────────────────────────────────────────

class RustScanEngineAdapter:
    """
    Implements IScanEngine using the compiled Rust PyO3 library.
    If Rust is unavailable, uses Python stubs (no real scanning).
    """

    def __init__(self, db_path: str | None = None) -> None:
        if db_path is None:
            # Place the DB next to the application
            app_dir = Path(__file__).parent.parent.parent.parent
            db_path = str(app_dir / "signatures" / "signatures.db")

        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._db_path = db_path

    @property
    def db_path(self) -> str:
        """Path to the SQLite signatures database."""
        return self._db_path

    # ── IScanEngine methods ────────────────────────

    def scan_directory(
        self,
        path: str,
        progress_callback: Callable[[str, int, int], None],
        cancellation_token,
    ):
        if not RUST_AVAILABLE:
            logger.warning("scan_directory: Rust stub used")
            return _PythonStubSummary()

        return _rust.scan_directory(
            path,
            self._db_path,
            cancellation_token,
            progress_callback,
        )

    def scan_single_file(self, path: str):
        if not RUST_AVAILABLE:
            return _PythonStubResult(path)

        return _rust.scan_file(path, self._db_path)

    def import_signatures(self, json_path: str) -> int:
        if not RUST_AVAILABLE:
            logger.warning("import_signatures: Rust stub — nothing imported")
            return 0

        return _rust.import_signatures_json(json_path, self._db_path)

    def create_token(self):
        if not RUST_AVAILABLE:
            return _PythonStubToken()

        return _rust.CancellationToken()
