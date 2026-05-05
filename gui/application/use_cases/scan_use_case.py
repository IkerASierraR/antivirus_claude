"""
gui/application/use_cases/scan_use_case.py

Application layer — orchestrates domain logic.
No UI dependencies; no direct Rust calls; uses interfaces (ports).
"""

from __future__ import annotations
import uuid
import logging
from datetime import datetime
from typing import Callable

from ...domain.entities.models import (
    ScanSession, ScanType, ScanStatus, ThreatRecord,
    ThreatStatus, DetectionMethod, QuarantineEntry
)
from ...domain.interfaces.ports import IScanEngine, IScanRepository, IQuarantineRepository

logger = logging.getLogger("rustguard.usecase")


class ScanUseCase:
    """
    Orchestrates a complete scan lifecycle:
      1. Create session
      2. Call Rust engine with cancellation support
      3. Map Rust results → domain ThreatRecord list
      4. Persist session to history
    """

    def __init__(
        self,
        engine: IScanEngine,
        scan_repo: IScanRepository,
    ) -> None:
        self._engine = engine
        self._scan_repo = scan_repo
        self._active_token = None  # Current cancellation token

    # ── Public API ────────────────────────────────

    def start_scan(
        self,
        scan_type: ScanType,
        target_path: str,
        progress_callback: Callable[[str, int, int], None],
        on_complete: Callable[[ScanSession], None],
    ) -> None:
        """
        Begin a scan. Designed to be called from a background thread.
        `on_complete` fires when scan finishes (or is cancelled).
        """
        session_id = str(uuid.uuid4())[:8]
        session = ScanSession(
            session_id=session_id,
            scan_type=scan_type,
            target_path=target_path,
            started_at=datetime.now(),
            status=ScanStatus.RUNNING,
        )

        # Create a fresh cancellation token for this run
        self._active_token = self._engine.create_token()

        try:
            logger.info(f"[{session_id}] Starting {scan_type.value} scan on '{target_path}'")

            raw_summary = self._engine.scan_directory(
                path=target_path,
                progress_callback=progress_callback,
                cancellation_token=self._active_token,
            )

            # Map raw Rust results to domain models
            threats = [
                self._map_to_threat(r)
                for r in raw_summary.threats
            ]

            session.finished_at = datetime.now()
            session.total_files = raw_summary.total_files
            session.threats_count = raw_summary.threats_found
            session.skipped_files = raw_summary.skipped_files
            session.threats = threats
            session.status = (
                ScanStatus.CANCELLED if raw_summary.was_cancelled
                else ScanStatus.COMPLETE
            )

            logger.info(
                f"[{session_id}] Finished: {session.total_files} files, "
                f"{session.threats_count} threats, {session.duration_human}"
            )

        except Exception as exc:
            logger.error(f"[{session_id}] Scan error: {exc}", exc_info=True)
            session.finished_at = datetime.now()
            session.status = ScanStatus.ERROR

        finally:
            self._scan_repo.save_session(session)
            on_complete(session)

    def scan_single_file(self, path: str) -> ScanSession:
        """Synchronous single-file scan (used for drag-drop and context menu)."""
        session_id = str(uuid.uuid4())[:8]
        session = ScanSession(
            session_id=session_id,
            scan_type=ScanType.SINGLE,
            target_path=path,
            started_at=datetime.now(),
        )

        try:
            raw = self._engine.scan_single_file(path)
            session.total_files = 1
            session.finished_at = datetime.now()

            if raw.is_threat:
                threat = self._map_to_threat(raw)
                session.threats = [threat]
                session.threats_count = 1

            session.status = ScanStatus.COMPLETE

        except Exception as exc:
            logger.error(f"Single file scan failed: {exc}", exc_info=True)
            session.status = ScanStatus.ERROR
            session.finished_at = datetime.now()

        finally:
            self._scan_repo.save_session(session)

        return session

    def cancel_scan(self) -> None:
        """Called from UI thread when user clicks Cancel."""
        if self._active_token is not None:
            self._active_token.cancel()
            logger.info("Cancellation requested by user.")

    # ── Private helpers ────────────────────────────

    def _map_to_threat(self, raw) -> ThreatRecord:
        """Convert Rust FileScanResult → Python ThreatRecord."""
        try:
            method = DetectionMethod(raw.detection_method)
        except ValueError:
            method = DetectionMethod.HEURISTIC

        return ThreatRecord(
            path=raw.path,
            sha256=raw.sha256,
            md5=raw.md5,
            threat_name=raw.threat_name,
            detection_method=method,
            file_size=raw.file_size,
            detected_at=datetime.now(),
            status=ThreatStatus.DETECTED,
        )


class QuarantineUseCase:
    """Handles quarantine, restore, and delete operations."""

    def __init__(self, quarantine_repo: IQuarantineRepository) -> None:
        self._repo = quarantine_repo

    def quarantine_threat(self, threat: ThreatRecord) -> QuarantineEntry | None:
        try:
            entry = self._repo.quarantine_file(threat)
            threat.status = ThreatStatus.QUARANTINED
            threat.quarantine_path = entry.quarantine_path
            logger.info(f"Quarantined: {threat.path} → {entry.quarantine_path}")
            return entry
        except Exception as exc:
            logger.error(f"Quarantine failed for {threat.path}: {exc}", exc_info=True)
            return None

    def restore_file(self, entry_id: str) -> bool:
        success = self._repo.restore_file(entry_id)
        if success:
            logger.info(f"Restored quarantine entry: {entry_id}")
        return success

    def delete_quarantined(self, entry_id: str) -> bool:
        success = self._repo.delete_quarantined(entry_id)
        if success:
            logger.info(f"Deleted quarantine entry: {entry_id}")
        return success

    def list_quarantined(self) -> list[QuarantineEntry]:
        return self._repo.list_quarantined()


class HistoryUseCase:
    """Reads and manages scan history."""

    def __init__(self, scan_repo: IScanRepository) -> None:
        self._repo = scan_repo

    def get_all_sessions(self) -> list[ScanSession]:
        return sorted(
            self._repo.load_all_sessions(),
            key=lambda s: s.started_at,
            reverse=True,  # Most recent first
        )

    def clear_history(self) -> None:
        for session in self._repo.load_all_sessions():
            self._repo.delete_session(session.session_id)
