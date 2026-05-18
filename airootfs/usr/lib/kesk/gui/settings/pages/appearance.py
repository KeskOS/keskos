from __future__ import annotations

from PySide6.QtWidgets import QFrame, QPushButton

from .base import BasePage
from ..widgets import CardFrame, StatusLabel


class AppearancePage(BasePage):
    page_key = "appearance"

    def __init__(self, controller) -> None:
        super().__init__(controller, "Appearance", "SAFE USER-LEVEL VISUAL STATUS")
        self._loaded = False

        accent_card = CardFrame("Accent Preview", "FIXED KESKOS ACCENT")
        swatch = QFrame()
        swatch.setMinimumHeight(48)
        swatch.setStyleSheet("background-color: #ce6a35; border: 1px solid #ce6a35;")
        accent_card.layout.addWidget(swatch)
        self.root_layout.insertWidget(2, accent_card)

        status_card = CardFrame("Theme Status", "CURRENT VISUAL IDENTITY")
        self.fields = {}
        self.labels = {
            "plasma": "Plasma theme",
            "icons": "Icon theme",
            "cursor": "Cursor theme",
            "konsole": "Konsole profile",
            "gtk": "GTK theme",
            "kvantum": "Kvantum theme",
        }
        for key, label in self.labels.items():
            field = StatusLabel(f"{label}: waiting", "work")
            self.fields[key] = field
            status_card.layout.addWidget(field)
        self.root_layout.insertWidget(3, status_card)

        actions_card = CardFrame("Theme Actions", "REPAIR-ROUTED VISUAL ACTIONS")
        reapply = QPushButton("REAPPLY USER THEME")
        reapply.clicked.connect(self.reapply_theme)
        open_repair = QPushButton("OPEN REPAIR THEME OPTIONS")
        open_repair.clicked.connect(lambda: self.controller.show_page("repair"))
        actions_card.layout.addWidget(reapply)
        actions_card.layout.addWidget(open_repair)
        self.root_layout.insertWidget(4, actions_card)

    def on_activated(self) -> None:
        if not self._loaded:
            self.refresh()

    def refresh(self) -> None:
        self._loaded = True
        self.controller.run_json_tool("repair", ["--status", "--json"], self._apply_payload, self.controller.surface_error, timeout=45)

    def _apply_payload(self, payload: dict) -> None:
        active = payload.get("theme_status", {}).get("active", {})
        mapping = {
            "plasma": active.get("plasma_theme", "unknown"),
            "icons": active.get("icon_theme", "unknown"),
            "cursor": active.get("cursor_theme", "unknown"),
            "konsole": active.get("konsole_profile", "unknown"),
            "gtk": active.get("gtk_theme", "unknown"),
            "kvantum": active.get("kvantum_theme", "unknown"),
        }
        for key, value in mapping.items():
            kind = "ok" if value not in {None, "", "unavailable"} else "skip"
            self.fields[key].set_status(f"{self.labels[key]}: {value}", kind)

    def reapply_theme(self) -> None:
        if not self.controller.confirm("Reapply the current KeskOS visual identity now?"):
            return
        self.controller.show_page("repair")
        repair_page = self.controller.page("repair")
        if repair_page is not None:
            for action in repair_page.actions:
                if action.flag == "--visual-identity":
                    repair_page.run_action(action)
                    break
