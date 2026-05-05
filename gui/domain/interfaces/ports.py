"""
gui/domain/interfaces/ports.py

Abstract interfaces (ports) that the Application layer depends on.
Infrastructure layer provides concrete implementations.
This keeps domain/application independent of Rust, SQLite, filesystem, etc.
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Callable
from ..entities.models import (
    ScanSession, ThreatRecord, QuarantineEntry, ScanType
)


class IScanEngine(ABC):
    """Port: wraps the Rust scan_engine library."""

    @abstractmethod
    def scan_directory(
        self,
        path: str,
        progress_callback: Callable[[str, int, int], None],
        cancellation_token,
    ) -> "RustScanSummary":
        """Scan a directory tree. Calls callback(current_path, scanned, total)."""
        ...

    @abstractmethod
    def scan_single_file(self, path: str) -> "RustFileScanResult":
        """Scan exactly one file."""
        ...

    @abstractmethod
    def import_signatures(self, json_path: str) -> int:
        """Import JSON signatures into the SQLite DB. Returns count imported."""
        ...

    @abstractmethod
    def create_token(self):
        """Return a new CancellationToken."""
        ...


class IScanRepository(ABC):
    """Port: persists scan history."""

    @abstractmethod
    def save_session(self, session: ScanSession) -> None: ...

    @abstractmethod
    def load_all_sessions(self) -> list[ScanSession]: ...

    @abstractmethod
    def delete_session(self, session_id: str) -> None: ...


class IQuarantineRepository(ABC):
    """Port: manages the quarantine vault."""

    @abstractmethod
    def quarantine_file(self, threat: ThreatRecord) -> QuarantineEntry: ...

    @abstractmethod
    def restore_file(self, entry_id: str) -> bool: ...

    @abstractmethod
    def delete_quarantined(self, entry_id: str) -> bool: ...

    @abstractmethod
    def list_quarantined(self) -> list[QuarantineEntry]: ...
