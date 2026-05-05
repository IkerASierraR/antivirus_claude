"""
gui/presentation/views/main_window.py

Presentation layer — Main application window using CustomTkinter.
Implements: Scan controls, real-time progress, threat panel, settings tabs.
All long operations run in background threads to keep UI responsive.
"""

from __future__ import annotations
import threading
import time
import logging
from datetime import datetime
from pathlib import Path
from tkinter import filedialog
import tkinter as tk

import customtkinter as ctk

from ...application.use_cases.scan_use_case import (
    ScanUseCase, QuarantineUseCase, HistoryUseCase
)
from ...domain.entities.models import (
    ScanSession, ThreatRecord, ScanStatus, ScanType,
    QuarantineEntry
)
from ...shared.constants import (
    COLOR_BG, COLOR_BG_PANEL, COLOR_BG_CARD,
    COLOR_ACCENT, COLOR_SAFE, COLOR_THREAT, COLOR_WARNING,
    COLOR_TEXT, COLOR_TEXT_DIM, COLOR_BORDER,
    COLOR_BUTTON_RED,
    APP_NAME, APP_VERSION,
    get_quick_scan_paths, get_full_scan_path,
)

logger = logging.getLogger("rustguard.ui")

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


# ── Reusable card widget ────────────────────────────────────────────────────

class Card(ctk.CTkFrame):
    """Styled card with rounded corners."""
    def __init__(self, master, **kwargs):
        super().__init__(
            master,
            fg_color=COLOR_BG_CARD,
            corner_radius=10,
            border_width=1,
            border_color=COLOR_BORDER,
            **kwargs,
        )


# ── Threat row widget (inside threat list) ─────────────────────────────────

class ThreatRow(ctk.CTkFrame):
    """
    A single row in the threats panel.
    Shows threat name, path, detection method, and action buttons.
    """

    def __init__(
        self,
        master,
        threat: ThreatRecord,
        on_quarantine: callable,
        on_delete: callable,
        **kwargs,
    ):
        super().__init__(master, fg_color=COLOR_BG_CARD, corner_radius=8, **kwargs)
        self.threat = threat
        self._build(on_quarantine, on_delete)

    def _build(self, on_quarantine, on_delete):
        # ── Left info block ──
        info = ctk.CTkFrame(self, fg_color="transparent")
        info.pack(side="left", fill="x", expand=True, padx=12, pady=8)

        # Threat name badge
        badge_color = COLOR_THREAT if "heuristic" not in self.threat.detection_method.value else COLOR_WARNING
        ctk.CTkLabel(
            info,
            text=f"  ⚠  {self.threat.threat_name[:60]}  ",
            fg_color=badge_color,
            text_color="white",
            corner_radius=4,
            font=ctk.CTkFont(size=11, weight="bold"),
        ).pack(anchor="w")

        # Path (truncated)
        path_display = self.threat.path
        if len(path_display) > 70:
            path_display = "…" + path_display[-67:]
        ctk.CTkLabel(
            info,
            text=path_display,
            text_color=COLOR_TEXT_DIM,
            font=ctk.CTkFont(size=10),
        ).pack(anchor="w", pady=(2, 0))

        # Meta row
        meta = f"  {self.threat.detection_method.value.upper()}  |  {self.threat.size_human}  |  {self.threat.detected_at.strftime('%H:%M:%S')}"
        ctk.CTkLabel(
            info, text=meta,
            text_color=COLOR_TEXT_DIM,
            font=ctk.CTkFont(size=9),
        ).pack(anchor="w")

        # ── Right buttons ──
        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.pack(side="right", padx=8, pady=8)

        ctk.CTkButton(
            btns, text="🔒 Cuarentena",
            width=110, height=28,
            fg_color="#1565C0", hover_color="#1976D2",
            font=ctk.CTkFont(size=11),
            command=lambda: on_quarantine(self.threat),
        ).pack(pady=(0, 4))

        ctk.CTkButton(
            btns, text="🗑 Eliminar",
            width=110, height=28,
            fg_color=COLOR_BUTTON_RED, hover_color="#e74c3c",
            font=ctk.CTkFont(size=11),
            command=lambda: on_delete(self.threat),
        ).pack()


# ── Main Application Window ─────────────────────────────────────────────────

class MainWindow(ctk.CTk):
    """
    Root window. Hosts a tab view with:
      - Tab 1: Scanner (main scan controls + results)
      - Tab 2: Cuarentena
      - Tab 3: Historial / Ajustes
    """

    def __init__(
        self,
        scan_uc: ScanUseCase,
        quarantine_uc: QuarantineUseCase,
        history_uc: HistoryUseCase,
    ):
        super().__init__()

        self._scan_uc = scan_uc
        self._quarantine_uc = quarantine_uc
        self._history_uc = history_uc

        # ── State ──
        self._scan_thread: threading.Thread | None = None
        self._is_scanning = False
        self._current_session: ScanSession | None = None
        self._detected_threats: list[ThreatRecord] = []

        self._setup_window()
        self._build_ui()

    # ── Window setup ───────────────────────────────

    def _setup_window(self):
        self.title(f"{APP_NAME}  v{APP_VERSION}")
        self.geometry("980x700")
        self.minsize(860, 600)
        self.configure(fg_color=COLOR_BG)

        # Center on screen
        self.update_idletasks()
        x = (self.winfo_screenwidth()  - 980) // 2
        y = (self.winfo_screenheight() - 700) // 2
        self.geometry(f"+{x}+{y}")

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ── UI Construction ─────────────────────────────

    def _build_ui(self):
        # ── Header bar ──
        header = ctk.CTkFrame(self, fg_color=COLOR_BG_PANEL, height=60, corner_radius=0)
        header.pack(fill="x")
        header.pack_propagate(False)

        ctk.CTkLabel(
            header,
            text=f"🛡  {APP_NAME}",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color=COLOR_ACCENT,
        ).pack(side="left", padx=20, pady=12)

        self._status_dot = ctk.CTkLabel(
            header, text="● PROTEGIDO",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=COLOR_SAFE,
        )
        self._status_dot.pack(side="right", padx=20)

        # ── Tab view ──
        self._tabs = ctk.CTkTabview(
            self,
            fg_color=COLOR_BG_PANEL,
            segmented_button_fg_color=COLOR_BG_CARD,
            segmented_button_selected_color=COLOR_ACCENT,
            segmented_button_selected_hover_color="#00b894",
            segmented_button_unselected_color=COLOR_BG_CARD,
        )
        self._tabs.pack(fill="both", expand=True, padx=12, pady=(8, 12))

        self._tabs.add("🔍  Escáner")
        self._tabs.add("🔒  Cuarentena")
        self._tabs.add("📋  Historial")

        self._build_scanner_tab(self._tabs.tab("🔍  Escáner"))
        self._build_quarantine_tab(self._tabs.tab("🔒  Cuarentena"))
        self._build_history_tab(self._tabs.tab("📋  Historial"))

    # ══════════════════════════════════════════════
    #  TAB 1 — ESCÁNER
    # ══════════════════════════════════════════════

    def _build_scanner_tab(self, parent):
        parent.configure(fg_color=COLOR_BG)

        # ── Scan type buttons ──
        btn_row = ctk.CTkFrame(parent, fg_color="transparent")
        btn_row.pack(fill="x", padx=4, pady=(12, 6))

        btn_cfg = dict(height=42, corner_radius=8, font=ctk.CTkFont(size=13, weight="bold"))

        self._btn_quick = ctk.CTkButton(
            btn_row, text="⚡ Escaneo Rápido",
            fg_color=COLOR_ACCENT, hover_color="#00b894", text_color="#000",
            command=self._start_quick_scan, **btn_cfg,
        )
        self._btn_quick.pack(side="left", padx=(0, 6), expand=True, fill="x")

        self._btn_full = ctk.CTkButton(
            btn_row, text="🌐 Escaneo Completo",
            fg_color="#2d2d2d", hover_color="#3a3a3a",
            command=self._start_full_scan, **btn_cfg,
        )
        self._btn_full.pack(side="left", padx=6, expand=True, fill="x")

        self._btn_custom = ctk.CTkButton(
            btn_row, text="📁 Personalizado",
            fg_color="#2d2d2d", hover_color="#3a3a3a",
            command=self._start_custom_scan, **btn_cfg,
        )
        self._btn_custom.pack(side="left", padx=6, expand=True, fill="x")

        self._btn_single = ctk.CTkButton(
            btn_row, text="📄 Archivo Único",
            fg_color="#2d2d2d", hover_color="#3a3a3a",
            command=self._start_single_scan, **btn_cfg,
        )
        self._btn_single.pack(side="left", padx=(6, 0), expand=True, fill="x")

        # ── Progress area ──
        prog_card = Card(parent)
        prog_card.pack(fill="x", padx=4, pady=6)

        # Stats row
        stats_row = ctk.CTkFrame(prog_card, fg_color="transparent")
        stats_row.pack(fill="x", padx=16, pady=(12, 4))

        self._lbl_files = ctk.CTkLabel(
            stats_row, text="Archivos: 0",
            font=ctk.CTkFont(size=13),
            text_color=COLOR_TEXT,
        )
        self._lbl_files.pack(side="left")

        self._lbl_threats = ctk.CTkLabel(
            stats_row, text="Amenazas: 0",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=COLOR_SAFE,
        )
        self._lbl_threats.pack(side="left", padx=24)

        self._lbl_eta = ctk.CTkLabel(
            stats_row, text="",
            font=ctk.CTkFont(size=11),
            text_color=COLOR_TEXT_DIM,
        )
        self._lbl_eta.pack(side="right")

        # Progress bar
        self._progress = ctk.CTkProgressBar(
            prog_card,
            progress_color=COLOR_ACCENT,
            fg_color=COLOR_BG,
            height=8,
            corner_radius=4,
        )
        self._progress.set(0)
        self._progress.pack(fill="x", padx=16, pady=(0, 6))

        # Current file label
        self._lbl_current = ctk.CTkLabel(
            prog_card, text="Listo para escanear.",
            font=ctk.CTkFont(size=10),
            text_color=COLOR_TEXT_DIM,
            anchor="w",
        )
        self._lbl_current.pack(fill="x", padx=16, pady=(0, 8))

        # Cancel button (hidden when not scanning)
        self._btn_cancel = ctk.CTkButton(
            prog_card,
            text="✕  Cancelar Escaneo",
            fg_color=COLOR_BUTTON_RED,
            hover_color="#e74c3c",
            height=34,
            corner_radius=6,
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._cancel_scan,
        )
        # Not packed initially

        # ── Results panel ──
        results_card = Card(parent)
        results_card.pack(fill="both", expand=True, padx=4, pady=(0, 4))

        results_header = ctk.CTkFrame(results_card, fg_color="transparent")
        results_header.pack(fill="x", padx=16, pady=(10, 4))

        self._lbl_results_title = ctk.CTkLabel(
            results_header, text="Resultados",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=COLOR_TEXT,
        )
        self._lbl_results_title.pack(side="left")

        # Summary label (replaces listing thousands of safe files)
        self._lbl_summary = ctk.CTkLabel(
            results_header, text="",
            font=ctk.CTkFont(size=11),
            text_color=COLOR_TEXT_DIM,
        )
        self._lbl_summary.pack(side="right")

        # Scrollable threat list
        self._threat_scroll = ctk.CTkScrollableFrame(
            results_card,
            fg_color="transparent",
            label_text="",
        )
        self._threat_scroll.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        # Placeholder when no threats
        self._lbl_no_threats = ctk.CTkLabel(
            self._threat_scroll,
            text="✔  No se encontraron amenazas.",
            font=ctk.CTkFont(size=14),
            text_color=COLOR_SAFE,
        )
        self._lbl_no_threats.pack(pady=40)

    # ══════════════════════════════════════════════
    #  TAB 2 — CUARENTENA
    # ══════════════════════════════════════════════

    def _build_quarantine_tab(self, parent):
        parent.configure(fg_color=COLOR_BG)

        header = ctk.CTkFrame(parent, fg_color="transparent")
        header.pack(fill="x", padx=4, pady=(12, 6))

        ctk.CTkLabel(
            header, text="🔒  Archivos en Cuarentena",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=COLOR_TEXT,
        ).pack(side="left")

        ctk.CTkButton(
            header, text="↻ Actualizar",
            width=100, height=32,
            fg_color=COLOR_ACCENT, hover_color="#00b894", text_color="#000",
            font=ctk.CTkFont(size=11),
            command=self._refresh_quarantine_tab,
        ).pack(side="right")

        self._q_scroll = ctk.CTkScrollableFrame(parent, fg_color=COLOR_BG_PANEL, corner_radius=8)
        self._q_scroll.pack(fill="both", expand=True, padx=4, pady=4)

        self._q_empty_label = ctk.CTkLabel(
            self._q_scroll, text="La cuarentena está vacía.",
            font=ctk.CTkFont(size=13), text_color=COLOR_TEXT_DIM,
        )
        self._q_empty_label.pack(pady=40)

    def _refresh_quarantine_tab(self):
        # Clear current rows
        for widget in self._q_scroll.winfo_children():
            widget.destroy()

        entries = self._quarantine_uc.list_quarantined()

        if not entries:
            ctk.CTkLabel(
                self._q_scroll, text="La cuarentena está vacía.",
                font=ctk.CTkFont(size=13), text_color=COLOR_TEXT_DIM,
            ).pack(pady=40)
            return

        for entry in entries:
            self._add_quarantine_row(entry)

    def _add_quarantine_row(self, entry: QuarantineEntry):
        row = ctk.CTkFrame(self._q_scroll, fg_color=COLOR_BG_CARD, corner_radius=8)
        row.pack(fill="x", padx=4, pady=3)

        info = ctk.CTkFrame(row, fg_color="transparent")
        info.pack(side="left", fill="x", expand=True, padx=12, pady=8)

        ctk.CTkLabel(
            info, text=f"⚠  {entry.threat_name[:55]}",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=COLOR_WARNING,
        ).pack(anchor="w")

        path_display = entry.original_path
        if len(path_display) > 65:
            path_display = "…" + path_display[-62:]
        ctk.CTkLabel(
            info, text=path_display,
            font=ctk.CTkFont(size=10), text_color=COLOR_TEXT_DIM,
        ).pack(anchor="w")

        ctk.CTkLabel(
            info,
            text=f"Cuarentenado: {entry.quarantined_at.strftime('%d/%m/%Y %H:%M')}",
            font=ctk.CTkFont(size=9), text_color=COLOR_TEXT_DIM,
        ).pack(anchor="w")

        btns = ctk.CTkFrame(row, fg_color="transparent")
        btns.pack(side="right", padx=8, pady=8)

        ctk.CTkButton(
            btns, text="↩ Restaurar",
            width=100, height=28,
            fg_color="#1565C0", hover_color="#1976D2",
            font=ctk.CTkFont(size=10),
            command=lambda e=entry, r=row: self._restore_quarantine(e, r),
        ).pack(pady=(0, 4))

        ctk.CTkButton(
            btns, text="🗑 Eliminar",
            width=100, height=28,
            fg_color=COLOR_BUTTON_RED, hover_color="#e74c3c",
            font=ctk.CTkFont(size=10),
            command=lambda e=entry, r=row: self._delete_quarantine(e, r),
        ).pack()

    def _restore_quarantine(self, entry: QuarantineEntry, row_widget):
        if self._quarantine_uc.restore_file(entry.entry_id):
            row_widget.destroy()
            self._show_toast("✔ Archivo restaurado correctamente.")
        else:
            self._show_toast("✗ No se pudo restaurar el archivo.", error=True)

    def _delete_quarantine(self, entry: QuarantineEntry, row_widget):
        if self._quarantine_uc.delete_quarantined(entry.entry_id):
            row_widget.destroy()
            self._show_toast("🗑 Archivo eliminado permanentemente.")
        else:
            self._show_toast("✗ No se pudo eliminar.", error=True)

    # ══════════════════════════════════════════════
    #  TAB 3 — HISTORIAL
    # ══════════════════════════════════════════════

    def _build_history_tab(self, parent):
        parent.configure(fg_color=COLOR_BG)

        header = ctk.CTkFrame(parent, fg_color="transparent")
        header.pack(fill="x", padx=4, pady=(12, 6))

        ctk.CTkLabel(
            header, text="📋  Historial de Escaneos",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=COLOR_TEXT,
        ).pack(side="left")

        ctk.CTkButton(
            header, text="↻ Actualizar",
            width=100, height=32,
            fg_color=COLOR_ACCENT, hover_color="#00b894", text_color="#000",
            font=ctk.CTkFont(size=11),
            command=self._refresh_history_tab,
        ).pack(side="right")

        ctk.CTkButton(
            header, text="Limpiar historial",
            width=120, height=32,
            fg_color=COLOR_BG_CARD, hover_color=COLOR_BG,
            font=ctk.CTkFont(size=11),
            command=self._clear_history,
        ).pack(side="right", padx=6)

        self._hist_scroll = ctk.CTkScrollableFrame(parent, fg_color=COLOR_BG_PANEL, corner_radius=8)
        self._hist_scroll.pack(fill="both", expand=True, padx=4, pady=4)

        self._refresh_history_tab()

    def _refresh_history_tab(self):
        for widget in self._hist_scroll.winfo_children():
            widget.destroy()

        sessions = self._history_uc.get_all_sessions()

        if not sessions:
            ctk.CTkLabel(
                self._hist_scroll, text="No hay escaneos registrados aún.",
                font=ctk.CTkFont(size=13), text_color=COLOR_TEXT_DIM,
            ).pack(pady=40)
            return

        for session in sessions:
            self._add_history_row(session)

    def _add_history_row(self, session: ScanSession):
        row = ctk.CTkFrame(self._hist_scroll, fg_color=COLOR_BG_CARD, corner_radius=8)
        row.pack(fill="x", padx=4, pady=3)

        # Status color
        if session.status == ScanStatus.COMPLETE and session.threats_count == 0:
            status_color, status_icon = COLOR_SAFE, "✔"
        elif session.threats_count > 0:
            status_color, status_icon = COLOR_THREAT, "⚠"
        elif session.status == ScanStatus.CANCELLED:
            status_color, status_icon = COLOR_WARNING, "⊘"
        else:
            status_color, status_icon = COLOR_TEXT_DIM, "?"

        ctk.CTkLabel(
            row, text=status_icon,
            font=ctk.CTkFont(size=20),
            text_color=status_color,
            width=40,
        ).pack(side="left", padx=(12, 6), pady=10)

        info = ctk.CTkFrame(row, fg_color="transparent")
        info.pack(side="left", fill="x", expand=True, pady=8)

        ctk.CTkLabel(
            info,
            text=f"{session.scan_type.value.capitalize()} — {session.started_at.strftime('%d/%m/%Y %H:%M')}",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=COLOR_TEXT,
        ).pack(anchor="w")

        summary = (
            f"{session.total_files:,} archivos  |  "
            f"{session.threats_count} amenaza{'s' if session.threats_count != 1 else ''}  |  "
            f"{session.duration_human}  |  {session.status.name}"
        )
        ctk.CTkLabel(
            info, text=summary,
            font=ctk.CTkFont(size=10), text_color=COLOR_TEXT_DIM,
        ).pack(anchor="w")

        path_display = session.target_path
        if len(path_display) > 60:
            path_display = "…" + path_display[-57:]
        ctk.CTkLabel(
            info, text=path_display,
            font=ctk.CTkFont(size=9), text_color=COLOR_TEXT_DIM,
        ).pack(anchor="w")

    def _clear_history(self):
        self._history_uc.clear_history()
        self._refresh_history_tab()
        self._show_toast("Historial limpiado.")

    # ══════════════════════════════════════════════
    #  SCAN ORCHESTRATION
    # ══════════════════════════════════════════════

    def _start_quick_scan(self):
        paths = get_quick_scan_paths()
        if not paths:
            self._show_toast("No se encontraron rutas de escaneo rápido en este sistema.", error=True)
            return
        # Scan first quick-scan path (most risky one)
        # For a real quick scan, iterate all; here we use the first for demo
        self._begin_scan(ScanType.QUICK, paths[0])

    def _start_full_scan(self):
        self._begin_scan(ScanType.FULL, get_full_scan_path())

    def _start_custom_scan(self):
        directory = filedialog.askdirectory(
            title="Seleccionar carpeta para escanear",
            mustexist=True,
        )
        if directory:
            self._begin_scan(ScanType.CUSTOM, directory)

    def _start_single_scan(self):
        filepath = filedialog.askopenfilename(
            title="Seleccionar archivo para escanear",
        )
        if filepath:
            self._begin_single_scan(filepath)

    def _begin_scan(self, scan_type: ScanType, target: str):
        if self._is_scanning:
            return

        self._is_scanning = True
        self._detected_threats.clear()
        self._start_time = time.time()

        # Reset UI
        self._update_progress_ui(0, 0, 0, f"Iniciando escaneo {scan_type.value}…")
        self._clear_threat_list()
        self._lbl_no_threats.pack_forget()
        self._lbl_summary.configure(text="")
        self._set_scan_buttons_state("disabled")
        self._btn_cancel.pack(fill="x", padx=16, pady=(0, 8))

        self._scan_thread = threading.Thread(
            target=self._scan_uc.start_scan,
            args=(scan_type, target, self._progress_callback, self._on_scan_complete),
            daemon=True,
        )
        self._scan_thread.start()

    def _begin_single_scan(self, path: str):
        if self._is_scanning:
            return
        self._is_scanning = True
        self._detected_threats.clear()
        self._start_time = time.time()

        self._clear_threat_list()
        self._lbl_no_threats.pack_forget()
        self._update_progress_ui(0, 0, 1, f"Escaneando: {path}")
        self._set_scan_buttons_state("disabled")

        def _run():
            session = self._scan_uc.scan_single_file(path)
            self._on_scan_complete(session)

        threading.Thread(target=_run, daemon=True).start()

    def _cancel_scan(self):
        """UI thread handler for Cancel button."""
        if self._is_scanning:
            self._scan_uc.cancel_scan()
            self._lbl_current.configure(text="Cancelando…")
            self._btn_cancel.configure(state="disabled", text="Cancelando…")

    # ── Progress callback (called from Rust thread via PyO3) ──────────────

    def _progress_callback(self, current_path: str, scanned: int, total: int):
        """
        Called by Rust engine for every scanned file.
        IMPORTANT: This runs in the scan background thread, so we must use
        `after()` to safely update Tkinter widgets from the main thread.
        """
        self.after(0, self._update_progress_ui, scanned, len(self._detected_threats), total, current_path)

    def _update_progress_ui(self, scanned: int, threats: int, total: int, current_path: str):
        """Runs in main thread — safe to update widgets."""
        # Progress bar
        if total > 0:
            self._progress.set(scanned / total)
        else:
            self._progress.set(0)

        # Stats
        self._lbl_files.configure(text=f"Archivos: {scanned:,}")
        threat_color = COLOR_THREAT if threats > 0 else COLOR_SAFE
        self._lbl_threats.configure(
            text=f"Amenazas: {threats}",
            text_color=threat_color,
        )

        # ETA
        elapsed = time.time() - getattr(self, "_start_time", time.time())
        if scanned > 0 and total > 0 and elapsed > 1:
            rate = scanned / elapsed
            remaining = (total - scanned) / rate if rate > 0 else 0
            self._lbl_eta.configure(text=f"~{int(remaining)}s restantes")

        # Current file (truncated to 80 chars)
        display = current_path
        if len(display) > 80:
            display = "…" + display[-77:]
        self._lbl_current.configure(text=display)

    # ── Scan complete callback ─────────────────────

    def _on_scan_complete(self, session: ScanSession):
        """Called from scan thread when scan finishes."""
        self._current_session = session
        self._detected_threats = session.threats
        # Schedule UI update on main thread
        self.after(0, self._render_scan_results, session)

    def _render_scan_results(self, session: ScanSession):
        """Runs on main thread — renders final results."""
        self._is_scanning = False
        self._set_scan_buttons_state("normal")
        self._btn_cancel.pack_forget()

        # Final progress
        self._progress.set(1.0 if session.status == ScanStatus.COMPLETE else self._progress.get())
        self._lbl_current.configure(text="Escaneo completado." if not session.was_cancelled else "Escaneo cancelado por el usuario.")

        # Summary text
        status_icon = "✔" if session.threats_count == 0 else "⚠"
        summary_text = (
            f"{status_icon}  {session.total_files:,} archivos analizados  |  "
            f"{session.threats_count} amenaza{'s' if session.threats_count != 1 else ''}  |  "
            f"{session.duration_human}"
        )
        if session.was_cancelled:
            summary_text += "  [CANCELADO]"
        self._lbl_summary.configure(
            text=summary_text,
            text_color=COLOR_THREAT if session.threats_count > 0 else COLOR_SAFE,
        )

        # Render threat rows
        self._clear_threat_list()
        if not session.threats:
            self._lbl_no_threats.pack(pady=40)
        else:
            for threat in session.threats:
                self._add_threat_row(threat)

        # Header dot
        if session.threats_count > 0:
            self._status_dot.configure(text=f"● {session.threats_count} AMENAZA(S)", text_color=COLOR_THREAT)
        else:
            self._status_dot.configure(text="● PROTEGIDO", text_color=COLOR_SAFE)

        # Refresh history tab silently
        self._refresh_history_tab()

    def _add_threat_row(self, threat: ThreatRecord):
        row = ThreatRow(
            self._threat_scroll,
            threat,
            on_quarantine=self._handle_quarantine,
            on_delete=self._handle_delete_threat,
        )
        row.pack(fill="x", padx=4, pady=3)

    def _clear_threat_list(self):
        for widget in self._threat_scroll.winfo_children():
            widget.destroy()

    # ── Threat action handlers ─────────────────────

    def _handle_quarantine(self, threat: ThreatRecord):
        entry = self._quarantine_uc.quarantine_threat(threat)
        if entry:
            self._show_toast(f"🔒 '{threat.filename}' movido a cuarentena.")
            self._refresh_quarantine_tab()
            # Remove row (re-render threats)
            self._detected_threats = [t for t in self._detected_threats if t.path != threat.path]
            self._clear_threat_list()
            for t in self._detected_threats:
                self._add_threat_row(t)
            if not self._detected_threats:
                self._lbl_no_threats.pack(pady=40)
        else:
            self._show_toast("✗ No se pudo mover a cuarentena.", error=True)

    def _handle_delete_threat(self, threat: ThreatRecord):
        try:
            from pathlib import Path as _P
            _P(threat.path).unlink(missing_ok=True)
            self._show_toast(f"🗑 '{threat.filename}' eliminado.")
            self._detected_threats = [t for t in self._detected_threats if t.path != threat.path]
            self._clear_threat_list()
            for t in self._detected_threats:
                self._add_threat_row(t)
            if not self._detected_threats:
                self._lbl_no_threats.pack(pady=40)
        except PermissionError as exc:
            logger.error(f"Delete threat failed: {exc}")
            self._show_toast("✗ Sin permisos para eliminar el archivo.", error=True)

    # ── Utility helpers ─────────────────────────────

    def _set_scan_buttons_state(self, state: str):
        for btn in (self._btn_quick, self._btn_full, self._btn_custom, self._btn_single):
            btn.configure(state=state)

    def _show_toast(self, message: str, error: bool = False, duration_ms: int = 3500):
        """Non-blocking toast notification at bottom of window."""
        color = COLOR_THREAT if error else COLOR_SAFE
        toast = ctk.CTkLabel(
            self,
            text=f"  {message}  ",
            fg_color=color,
            text_color="white",
            corner_radius=6,
            font=ctk.CTkFont(size=12),
        )
        toast.place(relx=0.5, rely=0.97, anchor="s")
        self.after(duration_ms, toast.destroy)

    def _on_close(self):
        if self._is_scanning:
            self._scan_uc.cancel_scan()
            # Give thread time to stop cleanly
            self.after(400, self.destroy)
        else:
            self.destroy()
