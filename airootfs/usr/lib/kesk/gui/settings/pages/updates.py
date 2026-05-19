from __future__ import annotations

from PySide6.QtWidgets import QCheckBox, QSpinBox

from ..widgets import SettingsSection, action_bar, small_button
from .base import BasePage


class UpdatesPage(BasePage):
    page_key = "updates"

    def __init__(self, controller) -> None:
        super().__init__(controller, "Updates", "Keep update policy here, while the actual update workflow stays in Kesk Upgrade instead of dominating the settings app.")
        self.backend = controller.backend
        self._build_ui()
        self.load_state()

    def _build_ui(self) -> None:
        section = SettingsSection("Update preferences")
        self.notifications = QCheckBox("Show update notifications")
        self.auto_check = QCheckBox("Check for updates automatically")
        self.interval = QSpinBox()
        self.interval.setRange(1, 168)
        self.include_aur = QCheckBox("Include AUR checks")
        self.include_flatpak = QCheckBox("Include Flatpak checks")
        self.include_firmware = QCheckBox("Include firmware checks")
        section.add_row("Notifications", "Allow branded update notifications inside future KeskOS surfaces.", self.notifications, keywords="notifications updates")
        section.add_row("Automatic checks", "Enable or disable periodic update checks.", self.auto_check, keywords="automatic update checks")
        section.add_row("Check interval", "Interval in hours for automatic update checks.", self.interval, keywords="interval hours update")
        section.add_row("AUR", "Include yay/AUR updates when supported.", self.include_aur, keywords="aur yay")
        section.add_row("Flatpak", "Include Flatpak update checks when supported.", self.include_flatpak, keywords="flatpak")
        section.add_row("Firmware", "Include fwupd update checks when supported.", self.include_firmware, keywords="firmware fwupd")
        self.add_section(section)

        open_upgrade = SettingsSection("Kesk Upgrade")
        launch_button = small_button("Open Kesk Upgrade")
        launch_button.clicked.connect(self.controller.launch_upgrade)
        open_upgrade.add_widget(action_bar(launch_button), keywords="open kesk upgrade")
        self.add_section(open_upgrade)

        apply_button = small_button("Apply", primary=True)
        apply_button.clicked.connect(self.apply_changes)
        revert_button = small_button("Revert")
        revert_button.clicked.connect(self.load_state)
        actions = SettingsSection("Apply changes")
        actions.add_widget(action_bar(apply_button, revert_button), keywords="apply revert")
        self.add_section(actions)

    def load_state(self) -> None:
        state = self.backend.updates_state()
        self.notifications.setChecked(bool(state["notifications"]))
        self.auto_check.setChecked(bool(state["auto_check"]))
        self.interval.setValue(int(state["interval"]))
        self.include_aur.setChecked(bool(state["include_aur"]))
        self.include_flatpak.setChecked(bool(state["include_flatpak"]))
        self.include_firmware.setChecked(bool(state["include_firmware"]))

    def apply_changes(self) -> None:
        values = {
            "notifications": self.notifications.isChecked(),
            "auto_check": self.auto_check.isChecked(),
            "interval": self.interval.value(),
            "include_aur": self.include_aur.isChecked(),
            "include_flatpak": self.include_flatpak.isChecked(),
            "include_firmware": self.include_firmware.isChecked(),
        }
        result = self.backend.apply_updates(values)
        self.show_result(result, "Updates")
        self.load_state()

    def on_activated(self) -> None:
        self.load_state()
