from __future__ import annotations

from PySide6.QtWidgets import QCheckBox, QComboBox, QLabel

from ..widgets import SupportBadge, SettingsSection, StatusLabel, control_with_hint, populate_combo, select_combo_value, small_button
from .base import BasePage


class AccessibilityPage(BasePage):
    page_key = "accessibility"

    def __init__(self, controller) -> None:
        super().__init__(controller, "Accessibility", "Make the system easier to see, hear and control.")
        self.backend = controller.backend
        self._build_ui()
        self.load_state()

    def _build_ui(self) -> None:
        status_section = SettingsSection("Backend status", "Accessibility direct writes stay conservative and hand off to KDE where the exact keys are still version-sensitive.")
        self.support_badge = SupportBadge("KDE Handoff", "work")
        self.backend_label = StatusLabel("Loading backend status", "work")
        self.status_label = StatusLabel("Loading direct-control status", "work")
        self.note_label = QLabel()
        self.note_label.setWordWrap(True)
        status_section.add_row("Support level", "Official support level for accessibility controls on this system.", self.support_badge, keywords="accessibility support level kde handoff")
        status_section.add_row("Backend", "Primary routing for accessibility controls on this system.", self.backend_label, keywords="backend status accessibility")
        status_section.add_row("Direct controls", "Current availability for the small set of accessibility options wired directly.", self.status_label, keywords="backend status accessibility direct limited")
        status_section.add_widget(self.note_label, keywords="accessibility handoff note kde")
        self.add_section(status_section)

        section = SettingsSection("Assistive controls", "Adjust visual accessibility, motion, and keyboard-assistance preferences.")
        self.large_text = QCheckBox("Enabled")
        self.high_contrast = QCheckBox("Enabled")
        self.high_contrast_hint = control_with_hint(self.high_contrast)
        self.screen_reader = QCheckBox("Enabled")
        self.screen_reader_hint = control_with_hint(self.screen_reader)
        self.reduce_animations = QCheckBox("Enabled")
        self.sticky_keys = QCheckBox("Enabled")
        self.sticky_keys_hint = control_with_hint(self.sticky_keys)
        self.slow_keys = QCheckBox("Enabled")
        self.slow_keys_hint = control_with_hint(self.slow_keys)
        self.bounce_keys = QCheckBox("Enabled")
        self.bounce_keys_hint = control_with_hint(self.bounce_keys)
        self.cursor_size = QComboBox()
        populate_combo(self.cursor_size, [("24", "24 px"), ("32", "32 px"), ("48", "48 px"), ("64", "64 px")])

        section.add_row("Large text", "Increase interface text scale for improved readability.", self.large_text, keywords="large text accessibility")
        section.add_row("High contrast", "Switch to a higher-contrast appearance profile when directly supported.", self.high_contrast_hint, keywords="high contrast")
        section.add_row("Screen reader", "Enable assistive screen-reader integration when supported.", self.screen_reader_hint, keywords="screen reader")
        section.add_row("Reduce animations", "Reduce desktop motion and long transitions.", self.reduce_animations, keywords="reduce animations motion")
        section.add_row("Sticky keys", "Keep modifier keys active until another key is pressed.", self.sticky_keys_hint, keywords="sticky keys")
        section.add_row("Slow keys", "Require keys to be held for longer before they register.", self.slow_keys_hint, keywords="slow keys")
        section.add_row("Bounce keys", "Ignore repeated key presses for a short time.", self.bounce_keys_hint, keywords="bounce keys")
        section.add_row("Cursor size", "Choose a larger pointer size for easier tracking.", self.cursor_size, keywords="cursor size pointer")
        self.advanced_button = small_button("Open KDE Accessibility Settings")
        self.advanced_button.clicked.connect(lambda: self.controller.open_kcm("kcm_access"))
        section.add_row("Advanced tools", "Use KDE's accessibility module for high-contrast, keyboard-assistance, and screen-reader integration.", self.advanced_button, keywords="advanced accessibility keyboard")
        self.add_section(section)

    def load_state(self) -> None:
        self.begin_refresh()
        state = self.backend.accessibility_state()
        status = state["status"]
        self.support_badge.set_support("KDE Handoff")
        self.backend_label.set_status("KDE Handoff", "work")
        self.status_label.set_status(status.display_label, status.ui_kind)
        self.note_label.setText(
            "Advanced accessibility options are handled by KDE Accessibility settings for safety and compatibility.\n\nBasic appearance accessibility options may be controlled here. Advanced toggles like high contrast, sticky keys, slow keys, bounce keys and screen reader are handed off to KDE Accessibility settings."
        )
        self.large_text.setChecked(bool(state["large_text"]))
        self.high_contrast.setChecked(bool(state["high_contrast"]))
        self.screen_reader.setChecked(bool(state["screen_reader"]))
        self.reduce_animations.setChecked(bool(state["reduce_animations"]))
        self.sticky_keys.setChecked(bool(state["sticky_keys"]))
        self.slow_keys.setChecked(bool(state["slow_keys"]))
        self.bounce_keys.setChecked(bool(state["bounce_keys"]))
        select_combo_value(self.cursor_size, str(int(state["cursor_size"])))

        self.large_text.setEnabled(bool(state["supports_large_text"]))
        self.high_contrast_hint.set_enabled(bool(state["supports_high_contrast"]), "Use KDE Accessibility Settings for high contrast.")
        self.screen_reader_hint.set_enabled(bool(state["supports_screen_reader"]), "Use KDE Accessibility Settings for screen reader control.")
        self.reduce_animations.setEnabled(bool(state["supports_reduce_animations"]))
        self.sticky_keys_hint.set_enabled(bool(state["supports_sticky_keys"]), "Use KDE Accessibility Settings for sticky keys.")
        self.slow_keys_hint.set_enabled(bool(state["supports_slow_keys"]), "Use KDE Accessibility Settings for slow keys.")
        self.bounce_keys_hint.set_enabled(bool(state["supports_bounce_keys"]), "Use KDE Accessibility Settings for bounce keys.")
        self.cursor_size.setEnabled(bool(state["supports_cursor_size"]))
        kcm_available = bool(self.backend.tools.get("kcmshell6") or self.backend.tools.get("systemsettings"))
        self.advanced_button.setEnabled(kcm_available)
        self.advanced_button.setToolTip("" if kcm_available else "kcmshell6 or systemsettings is required to open KDE Accessibility Settings.")
        self.finish_refresh()

    def apply_changes(self) -> None:
        values = {
            "large_text": self.large_text.isChecked(),
            "high_contrast": self.high_contrast.isChecked(),
            "screen_reader": self.screen_reader.isChecked(),
            "reduce_animations": self.reduce_animations.isChecked(),
            "sticky_keys": self.sticky_keys.isChecked(),
            "slow_keys": self.slow_keys.isChecked(),
            "bounce_keys": self.bounce_keys.isChecked(),
            "cursor_size": int(self.cursor_size.currentData() or 24),
        }
        result = self.backend.apply_accessibility(values)
        self.show_result(result, "Accessibility")
        self.load_state()

    def on_activated(self) -> None:
        self.load_state()
