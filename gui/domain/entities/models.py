"""
gui/domain/entities/models.py

Domain layer — pure data models (no framework dependencies).
These mirror the Rust structs but live in Python for type safety and
serialization throughout the app layers.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from pathlib import Path


# ──────────────────────────────────────────────
#  Enumerations
# ──────────────────────────────────────────────

class ScanType(Enum):
    QUICK    = "quick"       # Predefined high-risk paths only
    FULL     = "full"        # Entire drive / home directory
    CUSTOM   = "custom"      # User-selected directory
    SINGLE   = "single"      # Single file


class ThreatStatus(Enum):
    DETECTED    = "detected"    # Found, awaiting action
    QUARANTINED = "quarantined" # Moved to quarantine folder
    DELETED     = "deleted"     # Permanently removed
    IGNORED     = "ignored"     # User dismissed it


class DetectionMethod(Enum):
    SIGNATURE     = "signature"
    SIGNATURE_MD5 = "signature_md5"
    HEURISTIC     = "heuristic"
    CLEAN         = "clean"
    ERROR         = "error"
    INFO_ONLY     = "info_only"


class ScanStatus(Enum):
    IDLE      = auto()
    RUNNING   = auto()
    CANCELLED = auto()
    COMPLETE  = auto()
    ERROR     = auto()


# ──────────────────────────────────────────────
#  Core Entities
# ──────────────────────────────────────────────

@dataclass
class ThreatRecord:
    """
    Represents a detected threat from a scan.
    Immutable after creation; status is tracked separately in repo.
    """
    path: str
    sha256: str
    md5: str
    threat_name: str
    detection_method: DetectionMethod
    file_size: int
    detected_at: datetime = field(default_factory=datetime.now)
    status: ThreatStatus = ThreatStatus.DETECTED
    # Original path before quarantine (filled by quarantine use-case)
    original_path: str = ""
    # Path inside quarantine folder
    quarantine_path: str = ""

    @property
    def filename(self) -> str:
        return Path(self.path).name

    @property
    def size_human(self) -> str:
        """Human-readable file size."""
        for unit in ("B", "KB", "MB", "GB"):
            if self.file_size < 1024:
                return f"{self.file_size:.1f} {unit}"
            self.file_size //= 1024
        return f"{self.file_size:.1f} TB"


@dataclass
class ScanSession:
    """
    Represents a complete scan run (persisted to log history).
    """
    session_id: str
    scan_type: ScanType
    target_path: str
    started_at: datetime
    finished_at: datetime | None = None
    total_files: int = 0
    threats_count: int = 0
    skipped_files: int = 0
    status: ScanStatus = ScanStatus.RUNNING
    threats: list[ThreatRecord] = field(default_factory=list)

    @property
    def was_cancelled(self) -> bool:
        return self.status == ScanStatus.CANCELLED

    @property
    def duration_seconds(self) -> float:
        if self.finished_at:
            return (self.finished_at - self.started_at).total_seconds()
        return 0.0

    @property
    def duration_human(self) -> str:
        secs = int(self.duration_seconds)
        if secs < 60:
            return f"{secs}s"
        return f"{secs // 60}m {secs % 60}s"


@dataclass
class QuarantineEntry:
    """
    Tracks a file that has been moved to quarantine.
    Stored in the quarantine registry (JSON).
    """
    entry_id: str
    original_path: str
    quarantine_path: str
    threat_name: str
    sha256: str
    quarantined_at: datetime
    file_size: int

    @property
    def filename(self) -> str:
        return Path(self.original_path).name
