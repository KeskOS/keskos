from __future__ import annotations

from PySide6.QtWidgets import QLabel

from ..backend import DOC_LINKS
from ..widgets import SettingsSection, action_bar, small_button
from .base import BasePage


class AboutPage(BasePage):
    page_key = "about"

    def __init__(self, controller) -> None:
        super().__init__(controller, "About", "System and build information for the running KeskOS session.")
        self.backend = controller.backend
        self._rows: list[QLabel] = []
        self._build_ui()
        self.load_state()

    def _build_ui(self) -> None:
        info = SettingsSection("System information")
        for label_text, _placeholder in self.backend.about_rows():
            value_label = QLabel()
            info.add_row(label_text, "Current detected value.", value_label, keywords=label_text.lower())
            self._rows.append(value_label)
        self.add_section(info)

        links = SettingsSection("Links")
        buttons = []
        for label, url in DOC_LINKS:
            button = small_button(label)
            button.clicked.connect(lambda _checked=False, target=url: self.controller.open_url(target))
            buttons.append(button)
        links.add_widget(action_bar(*buttons), keywords="website docs github downloads")
        self.add_section(links)

    def load_state(self) -> None:
        rows = self.backend.about_rows()
        for value_label, (_label, value) in zip(self._rows, rows):
            value_label.setText(value)

    def on_activated(self) -> None:
        self.load_state()
