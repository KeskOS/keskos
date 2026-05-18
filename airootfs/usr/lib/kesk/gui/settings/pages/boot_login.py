from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QPushButton, QWidget

from .base import BasePage
from ..widgets import CardFrame, OutputConsole, StatusLabel


class BootLoginPage(BasePage):
    page_key = "boot_login"

    def __init__(self, controller) -> None:
        super().__init__(controller, "Boot & Login", "SDDM // PLYMOUTH // BOOT IDENTITY")
        self._loaded = False

        status_card = CardFrame("Boot Identity", "LOGIN SCREEN AND BOOT SPLASH STATUS")
        self.sddm_status = StatusLabel("SDDM theme: waiting", "work")
        self.plymouth_status = StatusLabel("Plymouth theme: waiting", "work")
        status_card.layout.addWidget(self.sddm_status)
        status_card.layout.addWidget(self.plymouth_status)
        self.root_layout.insertWidget(2, status_card)

        actions = QWidget()
        row = QHBoxLayout(actions)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)
        for text, callback in (
            ("REAPPLY SDDM THEME", self.reapply_sddm),
            ("REAPPLY PLYMOUTH THEME", self.reapply_plymouth),
            ("OPEN BOOT DOCS", lambda: self.controller.open_url("https://docs.keskos.org")),
        ):
            button = QPushButton(text)
            button.clicked.connect(callback)
            row.addWidget(button)
        self.root_layout.insertWidget(3, actions)

        output_card = CardFrame("Boot Console", "PRIVILEGED BOOT AND LOGIN ACTIONS")
        self.output_console = OutputConsole()
        output_card.layout.addWidget(self.output_console)
        self.root_layout.insertWidget(4, output_card, 1)

    def on_activated(self) -> None:
        if not self._loaded:
            self.refresh()

    def refresh(self) -> None:
        self._loaded = True
        self.controller.run_json_tool("repair", ["--status", "--json"], self._apply_payload, self.controller.surface_error, timeout=45)

    def _apply_payload(self, payload: dict) -> None:
        active = payload.get("theme_status", {}).get("active", {})
        sddm = active.get("sddm_theme", "unknown")
        plymouth = active.get("plymouth_theme", "unknown")
        self.sddm_status.set_status(f"SDDM theme: {sddm}", "ok" if sddm not in {None, '', 'unavailable'} else "warn")
        self.plymouth_status.set_status(f"Plymouth theme: {plymouth}", "ok" if plymouth not in {None, '', 'unavailable'} else "skip")

    def reapply_sddm(self) -> None:
        if not self.controller.confirm("Reapply the KeskOS SDDM theme? This affects the login screen and may require sudo."):
            return
        self.controller.launch_tool_in_terminal("repair", ["--sddm", "--yes"], "repair", self.output_console)

    def reapply_plymouth(self) -> None:
        if not self.controller.confirm("Reapply the KeskOS Plymouth theme? This affects the boot splash and may rebuild initramfs."):
            return
        self.controller.launch_tool_in_terminal("repair", ["--plymouth", "--yes"], "repair", self.output_console)
