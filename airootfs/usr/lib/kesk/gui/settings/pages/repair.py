from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtWidgets import QGridLayout, QLabel, QMessageBox, QPushButton, QScrollArea, QWidget

from .base import BasePage
from ..widgets import CardFrame, OutputConsole, StatusLabel


@dataclass(frozen=True)
class RepairAction:
    flag: str
    title: str
    description: str
    details: str
    requires_terminal: bool = False


class RepairPage(BasePage):
    page_key = "repair"

    def __init__(self, controller) -> None:
        super().__init__(controller, "Repair Console", "RESTORE DESKTOP STACK // THEME CHAIN // BOOT IDENTITY")
        self._loaded = False
        self.status_labels: dict[str, StatusLabel] = {}

        status_card = CardFrame("Current Theme Status", "READ-ONLY THEME AND BOOT IDENTITY STATUS")
        for key, label in (
            ("plasma", "Plasma theme"),
            ("colors", "Color scheme"),
            ("icons", "Icon theme"),
            ("cursor", "Cursor theme"),
            ("sddm", "SDDM theme"),
            ("plymouth", "Plymouth theme"),
        ):
            field = StatusLabel(f"{label}: waiting", "work")
            self.status_labels[key] = field
            status_card.layout.addWidget(field)
        refresh_button = QPushButton("REFRESH STATUS")
        refresh_button.clicked.connect(self.refresh_status)
        status_card.layout.addWidget(refresh_button)
        self.root_layout.insertWidget(2, status_card)

        actions_scroll = QScrollArea()
        actions_scroll.setWidgetResizable(True)
        actions_host = QWidget()
        actions_grid = QGridLayout(actions_host)
        actions_grid.setSpacing(12)

        self.actions = [
            RepairAction("--safe", "Run safe repair", "Reapply low-risk user-level KeskOS defaults.", "Creates missing Kesk dirs, reapplies user theme, Konsole, Dolphin where available, and rebuilds caches."),
            RepairAction("--panels", "Reset KDE Plasma panels", "Restore the official KeskOS panel layout.", "Backs up ~/.config/plasma-org.kde.plasma.desktop-appletsrc and restarts Plasma shell."),
            RepairAction("--launcher", "Reset Kesk launcher", "Restore the branded Kesk launcher wiring.", "Repairs pinned launcher state and managed launcher files."),
            RepairAction("--visual-identity", "Reapply full KeskOS visual identity", "Reapply Plasma, icons, cursor, Konsole, Dolphin, and GTK/Kvantum styling.", "Uses targeted user backups in ~/.local/state/kesk/backups/.../repair/ and skips missing assets cleanly."),
            RepairAction("--plasma", "Reapply Plasma theme/colors", "Restore the KeskOS Plasma theme chain.", "May touch kdeglobals, kwinrc, plasmarc, kscreenlockerrc, and ksplashrc."),
            RepairAction("--icons", "Reapply icon theme", "Restore the icon theme fallback chain.", "Updates kdeglobals and GTK icon theme settings."),
            RepairAction("--cursor", "Reapply cursor theme", "Restore the cursor theme fallback chain.", "Updates kcminputrc and GTK cursor settings."),
            RepairAction("--konsole", "Reapply Konsole profile", "Restore the orange/black terminal profile.", "Backs up konsolerc and only overwrites Kesk-managed profile assets."),
            RepairAction("--dolphin", "Reapply Dolphin config", "Restore Dolphin defaults if a staged template exists.", "Skips safely if no official Dolphin template is shipped."),
            RepairAction("--gtk-kvantum", "Reapply GTK/Kvantum styling", "Refresh GTK and Kvantum theme bindings.", "Touches gtk-3.0/settings.ini, gtk-4.0/settings.ini, and Kvantum config when assets exist."),
            RepairAction("--sddm", "Reapply SDDM login theme", "Restore the official login theme.", "Affects the login screen and may require sudo. Backs up /etc/sddm.conf and drop-ins first.", requires_terminal=True),
            RepairAction("--plymouth", "Reapply Plymouth boot theme", "Restore the official boot splash.", "Affects the boot splash and may rebuild initramfs. Requires sudo.", requires_terminal=True),
            RepairAction("--quickshell", "Repair Quickshell HUD", "Restore the packaged HUD config if Quickshell is present.", "Backs up ~/.config/quickshell and avoids duplicate autostarts."),
            RepairAction("--cache", "Rebuild icon/font cache", "Refresh KDE, icon, and font caches.", "Runs kbuildsycoca, fc-cache, and safe icon cache refreshes where available."),
        ]

        for index, action in enumerate(self.actions):
            card = CardFrame(action.title, action.description)
            run_button = QPushButton("RUN")
            run_button.clicked.connect(lambda _checked=False, meta=action: self.run_action(meta))
            detail_button = QPushButton("DETAILS")
            detail_button.clicked.connect(lambda _checked=False, meta=action: self.show_details(meta))
            card.layout.addWidget(run_button)
            card.layout.addWidget(detail_button)
            actions_grid.addWidget(card, index // 2, index % 2)

        export_card = CardFrame("Export repair report", "WRITE ~/kesk-repair-report.txt")
        export_run = QPushButton("RUN")
        export_run.clicked.connect(self.export_report)
        export_card.layout.addWidget(export_run)
        actions_grid.addWidget(export_card, len(self.actions) // 2 + 1, 0)

        actions_scroll.setWidget(actions_host)
        self.root_layout.insertWidget(3, actions_scroll, 1)

        output_card = CardFrame("Repair Output", "LIVE COMMAND OUTPUT AND TERMINAL HANDOFFS")
        self.output_console = OutputConsole()
        output_card.layout.addWidget(self.output_console)
        self.root_layout.insertWidget(4, output_card, 1)

    def on_activated(self) -> None:
        if not self._loaded:
            self.refresh_status()

    def refresh_status(self) -> None:
        self._loaded = True
        self.output_console.append_line("[ .. ] refreshing repair status")
        self.controller.run_json_tool("repair", ["--status", "--json"], self._apply_status, self.controller.surface_error, timeout=45)

    def _apply_status(self, payload: dict) -> None:
        active = payload.get("theme_status", {}).get("active", {})
        mapping = {
            "plasma": ("Plasma theme", active.get("plasma_theme", "unknown")),
            "colors": ("Color scheme", active.get("color_scheme", "unknown")),
            "icons": ("Icon theme", active.get("icon_theme", "unknown")),
            "cursor": ("Cursor theme", active.get("cursor_theme", "unknown")),
            "sddm": ("SDDM theme", active.get("sddm_theme", "unknown")),
            "plymouth": ("Plymouth theme", active.get("plymouth_theme", "unknown")),
        }
        for key, (label, value) in mapping.items():
            kind = "ok" if value not in {None, "", "unavailable"} else "skip"
            self.status_labels[key].set_status(f"{label}: {value}", kind)
        self.output_console.append_line("[ OK ] repair status refreshed")

    def show_details(self, action: RepairAction) -> None:
        QMessageBox.information(
            self,
            action.title.upper(),
            f"{action.description}\n\n{action.details}\n\nBackups:\n- ~/.local/state/kesk/backups/YYYYMMDD-HHMMSS/repair/\n- /var/lib/kesk/backups/YYYYMMDD-HHMMSS/repair/ when system files are touched",
        )

    def run_action(self, action: RepairAction) -> None:
        if not self.controller.confirm(f"Continue with '{action.title}'?"):
            self.output_console.append_line("[ -- ] repair action cancelled")
            return
        self.output_console.append_line(f"[ .. ] starting repair action: {action.title}")
        if action.requires_terminal:
            self.controller.launch_tool_in_terminal("repair", [action.flag, "--yes"], "repair", self.output_console)
            return
        self.controller.run_stream_tool("repair", [action.flag, "--yes"], self.output_console, self._action_finished)

    def _action_finished(self, exit_code: int) -> None:
        self.output_console.append_line(f"[ {'OK' if exit_code == 0 else '!!'} ] repair exit code: {exit_code}")
        self.refresh_status()

    def export_report(self) -> None:
        self.output_console.append_line("[ .. ] exporting repair report")
        self.controller.run_stream_tool("repair", ["--export-report"], self.output_console, self._report_finished)

    def _report_finished(self, exit_code: int) -> None:
        self.output_console.append_line(f"[ {'OK' if exit_code == 0 else '!!'} ] repair report export finished with exit code {exit_code}")
