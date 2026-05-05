"""
gui/infrastructure/repositories/quarantine_repository.py

Manages the quarantine vault:
- Moves infected files to a dedicated folder
- XOR-obfuscates content (prevents accidental execution; not real encryption)
- Keeps a JSON registry with original path for restore
- Implements IQuarantineRepository
"""

from __future__ import annotations
import json
import logging
import os
import shutil
import uuid
from datetime import datetime
from pathlib import Path

from ...domain.entities.models import ThreatRecord, QuarantineEntry

logger = logging.getLogger("rustguard.repo.quarantine")

_DT_FMT = "%Y-%m-%dT%H:%M:%S.%f"
# Simple XOR key — keeps files from accidentally executing; not cryptographic
_XOR_KEY: int = 0xAD


def _xor_file(src: Path, dst: Path) -> None:
    """XOR every byte of src, write result to dst."""
    with src.open("rb") as fin, dst.open("wb") as fout:
        while chunk := fin.read(65536):
            fout.write(bytes(b ^ _XOR_KEY for b in chunk))


def _dexor_file(src: Path, dst: Path) -> None:
    """Reverse XOR (identical operation — XOR is its own inverse)."""
    _xor_file(src, dst)


class JsonQuarantineRepository:
    """
    Quarantine files are stored as: <quarantine_dir>/<entry_id>.quar
    A registry JSON keeps the mapping back to original paths.
    """

    def __init__(self, quarantine_dir: str | None = None) -> None:
        if quarantine_dir is None:
            app_dir = Path(__file__).parent.parent.parent.parent
            quarantine_dir = str(app_dir / "quarantine")

        self._qdir = Path(quarantine_dir)
        self._qdir.mkdir(parents=True, exist_ok=True)
        self._registry_path = self._qdir / "registry.json"

        if not self._registry_path.exists():
            self._registry_path.write_text("[]", encoding="utf-8")

    # ── IQuarantineRepository ──────────────────────

    def quarantine_file(self, threat: ThreatRecord) -> QuarantineEntry:
        entry_id = str(uuid.uuid4())[:12]
        quarantine_path = str(self._qdir / f"{entry_id}.quar")

        src = Path(threat.path)
        dst = Path(quarantine_path)

        if not src.exists():
            raise FileNotFoundError(f"Source file not found: {threat.path}")

        try:
            # XOR-obfuscate into quarantine folder
            _xor_file(src, dst)
            # Remove original
            src.unlink()
        except PermissionError as exc:
            # Clean up partial quarantine file if copy succeeded but unlink failed
            if dst.exists():
                dst.unlink(missing_ok=True)
            raise PermissionError(
                f"Cannot move '{threat.path}' to quarantine (permission denied): {exc}"
            ) from exc

        entry = QuarantineEntry(
            entry_id=entry_id,
            original_path=threat.path,
            quarantine_path=quarantine_path,
            threat_name=threat.threat_name,
            sha256=threat.sha256,
            quarantined_at=datetime.now(),
            file_size=threat.file_size,
        )
        self._add_to_registry(entry)
        return entry

    def restore_file(self, entry_id: str) -> bool:
        entries = self._load_registry()
        entry = next((e for e in entries if e.entry_id == entry_id), None)

        if not entry:
            logger.warning(f"Restore: entry {entry_id} not found in registry")
            return False

        src = Path(entry.quarantine_path)
        dst = Path(entry.original_path)

        if not src.exists():
            logger.error(f"Quarantine file missing: {src}")
            return False

        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            _dexor_file(src, dst)
            src.unlink()
            self._remove_from_registry(entry_id)
            logger.info(f"Restored {entry.original_path}")
            return True
        except Exception as exc:
            logger.error(f"Restore failed for {entry_id}: {exc}", exc_info=True)
            return False

    def delete_quarantined(self, entry_id: str) -> bool:
        entries = self._load_registry()
        entry = next((e for e in entries if e.entry_id == entry_id), None)

        if not entry:
            return False

        try:
            Path(entry.quarantine_path).unlink(missing_ok=True)
            self._remove_from_registry(entry_id)
            return True
        except Exception as exc:
            logger.error(f"Delete quarantine failed: {exc}", exc_info=True)
            return False

    def list_quarantined(self) -> list[QuarantineEntry]:
        return self._load_registry()

    # ── Private helpers ────────────────────────────

    def _load_registry(self) -> list[QuarantineEntry]:
        try:
            raw = json.loads(self._registry_path.read_text(encoding="utf-8"))
            return [self._deserialize(r) for r in raw]
        except Exception as exc:
            logger.error(f"Cannot load quarantine registry: {exc}")
            return []

    def _add_to_registry(self, entry: QuarantineEntry) -> None:
        entries = self._load_registry()
        entries.append(entry)
        self._write_registry(entries)

    def _remove_from_registry(self, entry_id: str) -> None:
        entries = [e for e in self._load_registry() if e.entry_id != entry_id]
        self._write_registry(entries)

    def _write_registry(self, entries: list[QuarantineEntry]) -> None:
        tmp = self._registry_path.with_suffix(".tmp")
        data = [self._serialize(e) for e in entries]
        tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(self._registry_path)

    def _serialize(self, e: QuarantineEntry) -> dict:
        return {
            "entry_id": e.entry_id,
            "original_path": e.original_path,
            "quarantine_path": e.quarantine_path,
            "threat_name": e.threat_name,
            "sha256": e.sha256,
            "quarantined_at": e.quarantined_at.strftime(_DT_FMT),
            "file_size": e.file_size,
        }

    def _deserialize(self, d: dict) -> QuarantineEntry:
        return QuarantineEntry(
            entry_id=d["entry_id"],
            original_path=d["original_path"],
            quarantine_path=d["quarantine_path"],
            threat_name=d.get("threat_name", "Unknown"),
            sha256=d.get("sha256", ""),
            quarantined_at=datetime.strptime(d["quarantined_at"], _DT_FMT),
            file_size=d.get("file_size", 0),
        )
