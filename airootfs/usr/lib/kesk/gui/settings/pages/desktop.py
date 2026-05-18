from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QPushButton, QWidget

from .base import BasePage
from ..widgets import CardFrame, OutputConsole, StatusLabel


class DesktopPage(BasePage):
    page_key = "desktop"

    def __init__(self, controller) -> None:
        super().__init__(controller, "Desktop", "PANELS // LAUNCHER // HUD STATUS")
        self._loaded = False

        status_card = CardFrame("Desktop Stack", "CURRENT SESSION AND DESKTOP SHELL")
        self.fields = {}
        for key, text in (
            ("session", "desktop session: waiting"),
            ("panels", "panel status: waiting"),
            ("launcher", "launcher status: waiting"),
            ("hud", "HUD status: waiting"),
        ):
            field = StatusLabel(text, "work")
            self.fields[key] = field
            status_card.layout.addWidget(field)
        self.root_layout.insertWidget(2, status_card)

        buttons = QWidget()
        row = QHBoxLayout(buttons)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)
        for text, callback in (
            ("RESET PANELS", self.reset_panels),
            ("REPAIR LAUNCHER", self.repair_launcher),
            ("RESTART PLASMA", self.restart_plasma),
            ("RESTART HUD", self.restart_hud),
        ):
            button = QPushButton(text)
            button.clicked.connect(callback)
            row.addWidget(button)
        self.root_layout.insertWidget(3, buttons)

        output_card = CardFrame("Desktop Console", "USER-LEVEL DESKTOP ACTIONS")
        self.output_console = OutputConsole()
        output_card.layout.addWidget(self.output_console)
        self.root_layout.insertWidget(4, output_card, 1)

    def on_activated(self) -> None:
        if not self._loaded:
            self.refresh()

    def refresh(self) -> None:
        self._loaded = True
        self.controller.run_json_tool("doctor", ["--json"], self._apply_doctor, self.controller.surface_error)

    def _apply_doctor(self, payload: dict) -> None:
        info = dict(self.controller.about_rows())
        self.fields["session"].set_status(f"desktop session: {info.get('Current desktop', info.get('Desktop session', 'unknown'))}", "ok")
        panels_present = (self.controller.paths.home / ".config" / "plasma-org.kde.plasma.desktop-appletsrc").exists()
        self.fields["panels"].set_status("panel config present" if panels_present else "panel config missing", "ok" if panels_present else "warn")
        launcher_matches = payload.get("launcher_matches", [])
        self.fields["launcher"].set_status(
            "launcher files found" if launcher_matches else "launcher files missing",
            "ok" if launcher_matches else "warn",
        )
        quickshell_matches = payload.get("quickshell_matches", [])
        self.fields["hud"].set_status(
            "HUD config found" if quickshell_matches else "HUD config missing",
            "ok" if quickshell_matches else "skip",
        )

    def reset_panels(self) -> None:
        if not self.controller.confirm("Reset the official Plasma panel layout now?"):
            return
        self.controller.run_stream_tool("repair", ["--panels", "--yes"], self.output_console, lambda code: self.output_console.append_line(f"[ {'OK' if code == 0 else '!!'} ] panel reset exit code: {code}"))

    def repair_launcher(self) -> None:
        if not self.controller.confirm("Repair the Kesk launcher now?"):
            return
        self.controller.run_stream_tool("repair", ["--launcher", "--yes"], self.output_console, lambda code: self.output_console.append_line(f"[ {'OK' if code == 0 else '!!'} ] launcher repair exit code: {code}"))

    def restart_plasma(self) -> None:
        if not self.controller.confirm("Restart the Plasma shell now?"):
            return
        command = ["bash", "-lc", "(kquitapp6 plasmashell || killall plasmashell || true) && kstart plasmashell"]
        self.controller.run_stream_command(command, self.output_console, lambda code: self.output_console.append_line(f"[ {'OK' if code == 0 else '!!'} ] Plasma restart exit code: {code}"))

    def restart_hud(self) -> None:
        if not self.controller.confirm("Restart the Kesk HUD now?"):
            return
        command = [
            "bash",
            "-lc",
            "pkill -x quickshell >/dev/null 2>&1 || true; if command -v keskos-shell >/dev/null 2>&1; then (keskos-shell >/dev/null 2>&1 &); echo HUD restart signal sent.; else echo keskos-shell helper not found.; fi",
        ]
        self.controller.run_stream_command(command, self.output_console, lambda code: self.output_console.append_line(f"[ {'OK' if code == 0 else '!!'} ] HUD restart exit code: {code}"))
