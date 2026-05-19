from __future__ import annotations

from PySide6.QtWidgets import QCheckBox, QComboBox, QSpinBox

from ..backend import POWER_PROFILES
from ..widgets import SettingsSection, action_bar, populate_combo, select_combo_value, small_button
from .base import BasePage


class PowerPage(BasePage):
    page_key = "power"

    def __init__(self, controller) -> None:
        super().__init__(controller, "Power", "Keep the common profile and timeout controls here, with deeper tuning still available in KDE’s dedicated power modules.")
        self.backend = controller.backend
        self._build_ui()
        self.load_state()

    def _build_ui(self) -> None:
        section = SettingsSection("Power profile")
        self.profile = QComboBox()
        populate_combo(self.profile, [(value, value.replace("-", " ").title()) for value in POWER_PROFILES])
        self.blank_timeout = QSpinBox()
        self.blank_timeout.setRange(1, 240)
        self.sleep_timeout = QSpinBox()
        self.sleep_timeout.setRange(1, 480)
        self.battery_percent = QCheckBox("Show battery percentage in branded surfaces")
        section.add_row("Profile", "Use power-profiles-daemon if available.", self.profile, keywords="power profile performance balanced saver")
        section.add_row("Screen blank timeout", "Stored KeskOS preference in minutes.", self.blank_timeout, keywords="screen blank timeout")
        section.add_row("Sleep timeout", "Stored KeskOS preference in minutes.", self.sleep_timeout, keywords="sleep suspend timeout")
        section.add_row("Battery percentage", "Store whether battery percentages should remain visible.", self.battery_percent, keywords="battery percentage")
        self.add_section(section)

        advanced = SettingsSection("Advanced power settings")
        open_power = small_button("Open KDE Power Settings")
        open_power.clicked.connect(lambda: self.controller.open_kcm("kcm_powerdevilglobalconfig"))
        advanced.add_widget(action_bar(open_power), keywords="advanced power")
        self.add_section(advanced)

        apply_button = small_button("Apply", primary=True)
        apply_button.clicked.connect(self.apply_changes)
        revert_button = small_button("Revert")
        revert_button.clicked.connect(self.load_state)
        actions = SettingsSection("Apply changes")
        actions.add_widget(action_bar(apply_button, revert_button), keywords="apply revert")
        self.add_section(actions)

    def load_state(self) -> None:
        state = self.backend.power_state()
        select_combo_value(self.profile, str(state["profile"]))
        self.blank_timeout.setValue(int(state["blank_timeout"]))
        self.sleep_timeout.setValue(int(state["sleep_timeout"]))
        self.battery_percent.setChecked(bool(state["show_battery_percent"]))

    def apply_changes(self) -> None:
        values = {
            "profile": self.profile.currentData(),
            "blank_timeout": self.blank_timeout.value(),
            "sleep_timeout": self.sleep_timeout.value(),
            "show_battery_percent": self.battery_percent.isChecked(),
        }
        result = self.backend.apply_power(values)
        self.show_result(result, "Power")
        self.load_state()

    def on_activated(self) -> None:
        self.load_state()
