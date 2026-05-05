"""
gui/infrastructure/monitor/filesystem_monitor.py

Real-time filesystem monitor using watchdog.
Scans every new or modified file with the Rust engine and
fires a callback when a threat is detected.
"""

from __future__ import annotations
import logging
import threading
from typing import Callable

logger = logging.getLogger("rustguard.monitor")

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler, FileSystemEvent
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False
    logger.warning(
        "watchdog not installed — real-time protection unavailable. "
        "Run `pip install watchdog` to enable it."
    )


class _ThreatEventHandler:
    """Stub base; real handler is created only when watchdog is available."""


if WATCHDOG_AVAILABLE:
    class _ThreatEventHandler(FileSystemEventHandler):  # type: ignore[no-redef]
        """
        Handles file-system events by scanning new/modified files.
        Invokes `on_threat_found(path, threat_name, method)` on the caller's
        thread (via the provided callback — caller is responsible for
        scheduling UI updates on the main thread if needed).
        """

        def __init__(self, engine, on_threat_found: Callable[[str, str, str], None]) -> None:
            super().__init__()
            self._engine = engine
            self._on_threat_found = on_threat_found
            # Small set to avoid double-alerting the same path in quick succession
            self._recently_alerted: set[str] = set()
            self._lock = threading.Lock()
            self._cleanup_timers: list[threading.Timer] = []

        def _scan(self, path: str) -> None:
            with self._lock:
                if path in self._recently_alerted:
                    return
                self._recently_alerted.add(path)

            try:
                result = self._engine.scan_single_file(path)
                if result.is_threat:
                    logger.warning(
                        f"[Real-time] Threat detected: {result.threat_name} in {path}"
                    )
                    self._on_threat_found(path, result.threat_name, result.detection_method)
            except Exception as exc:
                logger.debug(f"[Real-time] Could not scan {path}: {exc}")
            finally:
                # Remove from recently_alerted after a short delay so the same
                # file can be re-checked on future modifications.
                timer = threading.Timer(30.0, self._recently_alerted.discard, args=(path,))
                with self._lock:
                    self._cleanup_timers.append(timer)
                timer.start()

        def cancel_timers(self) -> None:
            """Cancel all pending cleanup timers. Called when the observer stops."""
            with self._lock:
                for t in self._cleanup_timers:
                    t.cancel()
                self._cleanup_timers.clear()
                self._recently_alerted.clear()

        def on_created(self, event: FileSystemEvent) -> None:
            if not event.is_directory:
                self._scan(event.src_path)

        def on_modified(self, event: FileSystemEvent) -> None:
            if not event.is_directory:
                self._scan(event.src_path)

        def on_moved(self, event: FileSystemEvent) -> None:
            if not event.is_directory:
                self._scan(event.dest_path)


class FilesystemMonitor:
    """
    Watches a list of directories for new/modified files and runs
    the scan engine on each one.

    Thread-safe start/stop; designed to run as a persistent daemon.
    """

    def __init__(
        self,
        engine,
        watch_paths: list[str],
        on_threat_found: Callable[[str, str, str], None],
    ) -> None:
        self._engine = engine
        self._paths = watch_paths
        self._on_threat_found = on_threat_found
        self._observer = None
        self._handler = None  # kept to allow timer cancellation on stop

    def set_threat_callback(self, callback: Callable[[str, str, str], None]) -> None:
        """Update the threat-found callback (used by the UI after construction)."""
        self._on_threat_found = callback
        if self._handler is not None:
            self._handler._on_threat_found = callback

    # ── Public API ──────────────────────────────────

    def start(self) -> bool:
        """
        Start monitoring. Returns True if started, False if watchdog is
        unavailable or already running.
        """
        if not WATCHDOG_AVAILABLE:
            logger.warning("Cannot start real-time monitor: watchdog not installed.")
            return False

        if self.is_running:
            return True

        handler = _ThreatEventHandler(self._engine, self._on_threat_found)
        self._handler = handler
        self._observer = Observer()

        scheduled = 0
        for path in self._paths:
            try:
                self._observer.schedule(handler, path, recursive=True)
                scheduled += 1
                logger.info(f"[Real-time] Watching: {path}")
            except Exception as exc:
                logger.warning(f"[Real-time] Cannot watch {path}: {exc}")

        if scheduled == 0:
            logger.warning("[Real-time] No valid paths to watch — monitor not started.")
            self._observer = None
            return False

        self._observer.start()
        logger.info("[Real-time] Filesystem monitor started.")
        return True

    def stop(self) -> None:
        """Stop monitoring gracefully."""
        if self._handler is not None and WATCHDOG_AVAILABLE:
            self._handler.cancel_timers()
            self._handler = None
        if self._observer is not None:
            self._observer.stop()
            self._observer.join(timeout=5)
            self._observer = None
            logger.info("[Real-time] Filesystem monitor stopped.")

    @property
    def is_running(self) -> bool:
        return self._observer is not None and self._observer.is_alive()

    @property
    def is_available(self) -> bool:
        return WATCHDOG_AVAILABLE
