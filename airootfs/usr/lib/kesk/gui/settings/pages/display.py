from __future__ import annotations

from PySide6.QtWidgets import QCheckBox, QPlainTextEdit

from ..widgets import SettingsSection, action_bar, small_button
from .base import BasePage


class DisplayPage(BasePage):
    page_key = "display"

    def __init__(self, controller) -> None:
        super().__init__(controller, "Display", "Show the current display stack, expose a safe Night Color toggle, and keep advanced monitor layout inside KDE’s dedicated tools.")
        self.backend = controller.backend
        self._build_ui()
        self.load_state()

    def _build_ui(self) -> None:
        info_section = SettingsSection("Detected display stack")
        self.summary = QPlainTextEdit()
        self.summary.setReadOnly(True)
        info_section.add_widget(self.summary, keywords="display outputs monitors resolution refresh scale")
        self.add_section(info_section)

        control_section = SettingsSection("Safe display preferences")
        self.night_color = QCheckBox("Enable Night Color")
        control_section.add_row("Night Color", "Toggle the Night Color flag inside kwinrc.", self.night_color, keywords="night color display")
        self.add_section(control_section)

        advanced_section = SettingsSection("Advanced display settings")
        open_display = small_button("Open KDE Display Settings")
        open_display.clicked.connect(lambda: self.controller.open_kcm("kcm_kscreen"))
        advanced_section.add_widget(action_bar(open_display), keywords="advanced display kscreen")
        self.add_section(advanced_section)

        apply_button = small_button("Apply", primary=True)
        apply_button.clicked.connect(self.apply_changes)
        revert_button = small_button("Refresh")
        revert_button.clicked.connect(self.load_state)
        actions = SettingsSection("Apply changes")
        actions.add_widget(action_bar(apply_button, revert_button), keywords="apply refresh")
        self.add_section(actions)

    def load_state(self) -> None:
        state = self.backend.display_state()
        self.summary.setPlainText(str(state["output_summary"]))
        self.night_color.setChecked(bool(state["night_color"]))

    def apply_changes(self) -> None:
        result = self.backend.apply_display({"night_color": self.night_color.isChecked()})
        self.show_result(result, "Display")
        self.load_state()

    def on_activated(self) -> None:
        self.load_state()
