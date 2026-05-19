from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QComboBox, QSlider, QSpinBox

from ..widgets import SettingsSection, action_bar, small_button
from .base import BasePage


class InputPage(BasePage):
    page_key = "input"

    def __init__(self, controller) -> None:
        super().__init__(controller, "Input", "Handle common keyboard and pointer preferences without leaving the settings app.")
        self.backend = controller.backend
        self._build_ui()
        self.load_state()

    def _build_ui(self) -> None:
        section = SettingsSection("Keyboard and pointer")
        self.keyboard_layout = QComboBox()
        self.keyboard_layout.setEditable(True)
        self.keyboard_layout.addItems(["us", "gb", "de", "fr", "nl", "fi", "se"])
        self.repeat_delay = QSpinBox()
        self.repeat_delay.setRange(100, 2000)
        self.repeat_rate = QSpinBox()
        self.repeat_rate.setRange(1, 60)
        self.tap_to_click = QCheckBox("Enabled")
        self.natural_scroll = QCheckBox("Enabled")
        self.mouse_speed = QSlider(Qt.Orientation.Horizontal)
        self.mouse_speed.setRange(0, 100)

        section.add_row("Keyboard layout", "Primary XKB layout entry written to kxkbrc.", self.keyboard_layout, keywords="keyboard layout xkb")
        section.add_row("Repeat delay", "Keyboard repeat delay in milliseconds.", self.repeat_delay, keywords="repeat delay keyboard")
        section.add_row("Repeat rate", "Keyboard repeat rate value written to kcminputrc.", self.repeat_rate, keywords="repeat rate keyboard")
        section.add_row("Tap-to-click", "Store the preferred touchpad tap behavior for KeskOS integration.", self.tap_to_click, keywords="touchpad tap")
        section.add_row("Natural scrolling", "Store natural scrolling preference for touchpads and wheels.", self.natural_scroll, keywords="natural scroll")
        section.add_row("Pointer speed", "Store a branded pointer speed preference for future integrations.", self.mouse_speed, keywords="mouse speed pointer")
        self.add_section(section)

        advanced = SettingsSection("Advanced input settings")
        open_keyboard = small_button("Open KDE Keyboard Settings")
        open_keyboard.clicked.connect(lambda: self.controller.open_kcm("kcm_keyboard"))
        advanced.add_widget(action_bar(open_keyboard), keywords="advanced keyboard kde settings")
        self.add_section(advanced)

        apply_button = small_button("Apply", primary=True)
        apply_button.clicked.connect(self.apply_changes)
        revert_button = small_button("Revert")
        revert_button.clicked.connect(self.load_state)
        actions = SettingsSection("Apply changes")
        actions.add_widget(action_bar(apply_button, revert_button), keywords="apply revert")
        self.add_section(actions)

    def load_state(self) -> None:
        state = self.backend.input_state()
        self.keyboard_layout.setCurrentText(str(state["keyboard_layout"]))
        self.repeat_delay.setValue(int(state["repeat_delay"]))
        self.repeat_rate.setValue(int(state["repeat_rate"]))
        self.tap_to_click.setChecked(bool(state["tap_to_click"]))
        self.natural_scroll.setChecked(bool(state["natural_scroll"]))
        self.mouse_speed.setValue(int(state["mouse_speed"]))

    def apply_changes(self) -> None:
        values = {
            "keyboard_layout": self.keyboard_layout.currentText().strip() or "us",
            "repeat_delay": self.repeat_delay.value(),
            "repeat_rate": self.repeat_rate.value(),
            "tap_to_click": self.tap_to_click.isChecked(),
            "natural_scroll": self.natural_scroll.isChecked(),
            "mouse_speed": self.mouse_speed.value(),
        }
        result = self.backend.apply_input(values)
        self.show_result(result, "Input")
        self.load_state()

    def on_activated(self) -> None:
        self.load_state()
