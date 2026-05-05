"""
gui/infrastructure/repositories/scan_repository.py

Concrete JSON-backed implementation of IScanRepository.
Stores scan history in a local JSON file that persists across restarts.
"""

from __future__ import annotations
import json
import logging
import uuid
from datetime import datetime
from pathlib import Path

from ...domain.entities.models import (
    ScanSession, ScanType, ScanStatus, ThreatRecord,
    ThreatStatus, DetectionMethod
)

logger = logging.getLogger("rustguard.repo.scan")

_DT_FMT = "%Y-%m-%dT%H:%M:%S.%f"


class JsonScanRepository:
    """
    Stores ScanSession objects as JSON.
    Thread-safe write: atomic file replace pattern.
    """

    def __init__(self, history_file: str | None = None) -> None:
        if history_file is None:
            app_dir = Path(__file__).parent.parent.parent.parent
            history_file = str(app_dir / "logs" / "scan_history.json")

        self._path = Path(history_file)
        self._path.parent.mkdir(parents=True, exist_ok=True)

        if not self._path.exists():
            self._path.write_text("[]", encoding="utf-8")

    # ── IScanRepository ────────────────────────────

    def save_session(self, session: ScanSession) -> None:
        sessions = self._load_raw()

        # Update if session_id already exists (e.g., cancelled then resumed)
        sessions = [s for s in sessions if s.get("session_id") != session.session_id]
        sessions.append(self._serialize(session))

        self._atomic_write(sessions)
        logger.debug(f"Saved session {session.session_id}")

    def load_all_sessions(self) -> list[ScanSession]:
        raw = self._load_raw()
        result = []
        for item in raw:
            try:
                result.append(self._deserialize(item))
            except Exception as exc:
                logger.warning(f"Skipping corrupt session record: {exc}")
        return result

    def delete_session(self, session_id: str) -> None:
        sessions = [s for s in self._load_raw() if s.get("session_id") != session_id]
        self._atomic_write(sessions)

    # ── Private helpers ────────────────────────────

    def _load_raw(self) -> list[dict]:
        try:
            return json.loads(self._path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            logger.error(f"Could not load history: {exc}")
            return []

    def _atomic_write(self, data: list[dict]) -> None:
        """Write to temp file then rename — prevents corruption on crash."""
        tmp = self._path.with_suffix(".tmp")
        try:
            tmp.write_text(
                json.dumps(data, indent=2, ensure_ascii=False),
                encoding="utf-8"
            )
            tmp.replace(self._path)
        except OSError as exc:
            logger.error(f"History write failed: {exc}")

    def _serialize(self, session: ScanSession) -> dict:
        return {
            "session_id": session.session_id,
            "scan_type": session.scan_type.value,
            "target_path": session.target_path,
            "started_at": session.started_at.strftime(_DT_FMT),
            "finished_at": session.finished_at.strftime(_DT_FMT) if session.finished_at else None,
            "total_files": session.total_files,
            "threats_count": session.threats_count,
            "skipped_files": session.skipped_files,
            "status": session.status.name,
            "threats": [self._serialize_threat(t) for t in session.threats],
        }

    def _serialize_threat(self, t: ThreatRecord) -> dict:
        return {
            "path": t.path,
            "sha256": t.sha256,
            "md5": t.md5,
            "threat_name": t.threat_name,
            "detection_method": t.detection_method.value,
            "file_size": t.file_size,
            "detected_at": t.detected_at.strftime(_DT_FMT),
            "status": t.status.value,
            "original_path": t.original_path,
            "quarantine_path": t.quarantine_path,
        }

    def _deserialize(self, d: dict) -> ScanSession:
        threats = [self._deserialize_threat(t) for t in d.get("threats", [])]
        return ScanSession(
            session_id=d["session_id"],
            scan_type=ScanType(d["scan_type"]),
            target_path=d["target_path"],
            started_at=datetime.strptime(d["started_at"], _DT_FMT),
            finished_at=datetime.strptime(d["finished_at"], _DT_FMT) if d.get("finished_at") else None,
            total_files=d.get("total_files", 0),
            threats_count=d.get("threats_count", 0),
            skipped_files=d.get("skipped_files", 0),
            status=ScanStatus[d.get("status", "COMPLETE")],
            threats=threats,
        )

    def _deserialize_threat(self, d: dict) -> ThreatRecord:
        return ThreatRecord(
            path=d["path"],
            sha256=d.get("sha256", ""),
            md5=d.get("md5", ""),
            threat_name=d.get("threat_name", ""),
            detection_method=DetectionMethod(d.get("detection_method", "heuristic")),
            file_size=d.get("file_size", 0),
            detected_at=datetime.strptime(d["detected_at"], _DT_FMT),
            status=ThreatStatus(d.get("status", "detected")),
            original_path=d.get("original_path", ""),
            quarantine_path=d.get("quarantine_path", ""),
        )
