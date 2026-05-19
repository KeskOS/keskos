from __future__ import annotations

from PySide6.QtWidgets import QCheckBox, QFileDialog, QHBoxLayout, QLabel, QLineEdit, QSpinBox, QWidget

from ..widgets import SettingsSection, action_bar, small_button
from .base import BasePage


class BootPage(BasePage):
    page_key = "boot"

    def __init__(self, controller) -> None:
        super().__init__(controller, "Boot & Login", "Track boot and login preferences here while keeping system-level root changes explicit and safe.")
        self.backend = controller.backend
        self._build_ui()
        self.load_state()

    def _build_ui(self) -> None:
        info = SettingsSection("Detected system values")
        self.sddm_theme = QLabel()
        self.plymouth_theme = QLabel()
        info.add_row("SDDM theme", "Read-only detection from current system configuration.", self.sddm_theme, keywords="sddm login theme")
        info.add_row("Plymouth theme", "Read-only detection from current system configuration.", self.plymouth_theme, keywords="plymouth boot theme")
        self.add_section(info)

        prefs = SettingsSection("Boot and login preferences")
        self.boot_splash_duration = QSpinBox()
        self.boot_splash_duration.setRange(0, 20)
        self.show_logs = QCheckBox("Show boot logs")
        self.quiet_boot = QCheckBox("Use quiet boot")
        self.login_background = QLineEdit()
        background_button = small_button("Choose File")
        background_button.clicked.connect(self.choose_background)
        background_host = QWidget()
        background_layout = QHBoxLayout(background_host)
        background_layout.setContentsMargins(0, 0, 0, 0)
        background_layout.setSpacing(8)
        background_layout.addWidget(self.login_background, 1)
        background_layout.addWidget(background_button)
        prefs.add_row("Boot splash minimum duration", "Store the desired minimum splash time in seconds.", self.boot_splash_duration, keywords="boot splash duration")
        prefs.add_row("Show boot logs", "Store whether future boot flows should expose logs.", self.show_logs, keywords="boot logs")
        prefs.add_row("Quiet boot", "Store whether future boot flows should default to quiet mode.", self.quiet_boot, keywords="quiet boot")
        prefs.add_row("Login background", "Store the desired login background path for future root-backed apply steps.", background_host, keywords="login background")
        prefs.add_note("System-level SDDM, Plymouth, and bootloader updates are intentionally not applied from the full app process. This page stores preferences and surfaces current values safely.")
        self.add_section(prefs)

        apply_button = small_button("Apply", primary=True)
        apply_button.clicked.connect(self.apply_changes)
        revert_button = small_button("Revert")
        revert_button.clicked.connect(self.load_state)
        actions = SettingsSection("Apply changes")
        actions.add_widget(action_bar(apply_button, revert_button), keywords="apply revert")
        self.add_section(actions)

    def choose_background(self) -> None:
        path, _selected_filter = QFileDialog.getOpenFileName(
            self,
            "Choose Login Background",
            self.login_background.text() or str(self.controller.backend.paths.home / "Pictures"),
            "Images (*.png *.jpg *.jpeg *.webp *.bmp *.svg)",
        )
        if path:
            self.login_background.setText(path)

    def load_state(self) -> None:
        state = self.backend.boot_state()
        self.sddm_theme.setText(str(state["sddm_theme"]))
        self.plymouth_theme.setText(str(state["plymouth_theme"]))
        self.boot_splash_duration.setValue(int(state["boot_splash_min_duration"]))
        self.show_logs.setChecked(bool(state["show_boot_logs"]))
        self.quiet_boot.setChecked(bool(state["quiet_boot"]))
        self.login_background.setText(str(state["login_background"]))

    def apply_changes(self) -> None:
        values = {
            "boot_splash_min_duration": self.boot_splash_duration.value(),
            "show_boot_logs": self.show_logs.isChecked(),
            "quiet_boot": self.quiet_boot.isChecked(),
            "login_background": self.login_background.text().strip(),
        }
        result = self.backend.apply_boot(values)
        self.show_result(result, "Boot & Login")
        self.load_state()

    def on_activated(self) -> None:
        self.load_state()
