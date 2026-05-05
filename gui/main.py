"""
gui/main.py

Application entry point.
Wires together the dependency injection: Infrastructure → Application → Presentation.
"""

from __future__ import annotations
import sys
import logging
from pathlib import Path

# ── Ensure the project root is on the Python path ──
# (needed when running as: python -m gui.main  or  ./RustGuard.exe)
_PROJECT_ROOT = Path(__file__).parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

# ── Logging must be configured first ──────────────
from gui.shared.logging_config import setup_logging
setup_logging()

logger = logging.getLogger("rustguard.main")

# ── Infrastructure ────────────────────────────────
from gui.infrastructure.scanner.rust_engine_adapter import RustScanEngineAdapter
from gui.infrastructure.repositories.scan_repository import JsonScanRepository
from gui.infrastructure.repositories.quarantine_repository import JsonQuarantineRepository
from gui.infrastructure.monitor.filesystem_monitor import FilesystemMonitor

# ── Application use cases ─────────────────────────
from gui.application.use_cases.scan_use_case import (
    ScanUseCase, QuarantineUseCase, HistoryUseCase
)

# ── Presentation ──────────────────────────────────
from gui.presentation.views.main_window import MainWindow


def main() -> None:
    logger.info("RustGuard starting…")

    # ── Build the dependency graph ──
    engine      = RustScanEngineAdapter()
    scan_repo   = JsonScanRepository()
    q_repo      = JsonQuarantineRepository()

    scan_uc      = ScanUseCase(engine, scan_repo)
    quarantine_uc = QuarantineUseCase(q_repo)
    history_uc   = HistoryUseCase(scan_repo)

    from gui.shared.constants import get_quick_scan_paths
    monitor = FilesystemMonitor(
        engine=engine,
        watch_paths=get_quick_scan_paths(),
        on_threat_found=lambda path, name, method: None,  # overridden by MainWindow
    )

    # ── Launch GUI ──
    app = MainWindow(
        scan_uc=scan_uc,
        quarantine_uc=quarantine_uc,
        history_uc=history_uc,
        monitor=monitor,
        engine=engine,
    )
    app.mainloop()

    logger.info("RustGuard exited cleanly.")


if __name__ == "__main__":
    main()
