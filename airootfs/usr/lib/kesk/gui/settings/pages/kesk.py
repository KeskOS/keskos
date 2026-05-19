from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QCheckBox, QComboBox, QColorDialog, QLabel, QPushButton, QHBoxLayout, QWidget

from ..widgets import SettingsSection, action_bar, populate_combo, select_combo_value, small_button
from .base import BasePage


class KeskPage(BasePage):
    page_key = "kesk"

    def __init__(self, controller) -> None:
        super().__init__(controller, "KeskOS", "Store branded KeskOS behavior here without mixing in repair, developer, or package-management actions.")
        self.backend = controller.backend
        self._build_ui()
        self.load_state()

    def _build_ui(self) -> None:
        section = SettingsSection("KeskOS behavior")
        self.accent_value = QLabel()
        self.accent_value.setMinimumWidth(96)
        self.accent_value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        accent_button = QPushButton("Choose Accent")
        accent_button.clicked.connect(self.choose_accent)
        accent_host = QWidget()
        accent_layout = QHBoxLayout(accent_host)
        accent_layout.setContentsMargins(0, 0, 0, 0)
        accent_layout.setSpacing(8)
        accent_layout.addWidget(self.accent_value)
        accent_layout.addWidget(accent_button)
        self.crt = QCheckBox("Enabled")
        self.scanlines = QCheckBox("Enabled")
        self.prompt_style = QComboBox()
        populate_combo(self.prompt_style, [("keskos", "KeskOS Prompt"), ("minimal", "Minimal Prompt")])
        self.browser_homepage = QCheckBox("Apply the KeskOS homepage to the default browser when supported")
        self.first_run_completed = QCheckBox("First boot welcome already completed")
        self.telemetry = QCheckBox("Enable telemetry")
        self.local_analytics = QCheckBox("Enable future local-only analytics dashboard")
        self.experimental = QCheckBox("Enable experimental features")

        section.add_row("Accent color", "Primary branded accent stored in KeskOS settings.", accent_host, keywords="accent color")
        section.add_row("CRT effects", "Enable the main CRT-style preference for supported branded interfaces.", self.crt, keywords="crt terminal industrial")
        section.add_row("Scanlines", "Enable the scanline overlay preference for supported interfaces.", self.scanlines, keywords="scanlines")
        section.add_row("Prompt style", "Choose the default KeskOS shell prompt overlay.", self.prompt_style, keywords="prompt shell terminal")
        section.add_row("Browser homepage", "Apply the branded homepage to the default browser if a handler exists.", self.browser_homepage, keywords="browser homepage")
        section.add_row("First boot state", "Mark the welcome flow complete or reset it.", self.first_run_completed, keywords="first boot welcome")
        section.add_row("Telemetry", "Reserved toggle for any future telemetry feature.", self.telemetry, keywords="telemetry analytics")
        section.add_row("Local analytics dashboard", "Reserved toggle for a future local-only dashboard.", self.local_analytics, keywords="analytics local")
        section.add_row("Experimental features", "Store an opt-in flag for future experimental KeskOS features.", self.experimental, keywords="experimental features")
        self.add_section(section)

        note = SettingsSection("Notes")
        note.add_note("This page stores branded preferences only. It intentionally does not expose repair tools, package shortcuts, or developer controls.")
        self.add_section(note)

        apply_button = small_button("Apply", primary=True)
        apply_button.clicked.connect(self.apply_changes)
        revert_button = small_button("Revert")
        revert_button.clicked.connect(self.load_state)
        actions = SettingsSection("Apply changes")
        actions.add_widget(action_bar(apply_button, revert_button), keywords="apply revert")
        self.add_section(actions)

    def _set_accent(self, value: str) -> None:
        color = QColor(value)
        if not color.isValid():
            color = QColor("#ce6a35")
        text_color = "#111111" if color.lightness() > 140 else "#f4efe8"
        self.accent_value.setText(color.name().upper())
        self.accent_value.setStyleSheet(f"background-color: {color.name()}; color: {text_color}; border: 1px solid #ce6a35; padding: 6px;")

    def choose_accent(self) -> None:
        color = QColorDialog.getColor(QColor(self.accent_value.text() or "#ce6a35"), self, "Choose KeskOS Accent")
        if color.isValid():
            self._set_accent(color.name())

    def load_state(self) -> None:
        state = self.backend.kesk_state()
        self._set_accent(str(state["accent_color"]))
        self.crt.setChecked(bool(state["crt_effects"]))
        self.scanlines.setChecked(bool(state["scanlines"]))
        select_combo_value(self.prompt_style, str(state["prompt_style"]))
        self.browser_homepage.setChecked(bool(state["browser_homepage_enabled"]))
        self.first_run_completed.setChecked(bool(state["first_run_completed"]))
        self.telemetry.setChecked(bool(state["telemetry_enabled"]))
        self.local_analytics.setChecked(bool(state["local_analytics_dashboard"]))
        self.experimental.setChecked(bool(state["experimental_features"]))

    def apply_changes(self) -> None:
        default_browser = self.controller.backend.default_browser_id()
        values = {
            "accent_color": self.accent_value.text().strip(),
            "crt_effects": self.crt.isChecked(),
            "scanlines": self.scanlines.isChecked(),
            "prompt_style": self.prompt_style.currentData(),
            "browser_homepage_enabled": self.browser_homepage.isChecked(),
            "first_run_completed": self.first_run_completed.isChecked(),
            "telemetry_enabled": self.telemetry.isChecked(),
            "local_analytics_dashboard": self.local_analytics.isChecked(),
            "experimental_features": self.experimental.isChecked(),
        }
        result = self.backend.apply_kesk(values, default_browser)
        self.show_result(result, "KeskOS")
        self.load_state()

    def on_activated(self) -> None:
        self.load_state()
