from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QComboBox, QLabel, QSlider

from ..backend import FOCUS_POLICIES, TITLEBAR_LAYOUTS, WINDOW_BORDER_SIZES
from ..widgets import SettingsSection, action_bar, populate_combo, select_combo_value, small_button
from .base import BasePage


class WindowsPage(BasePage):
    page_key = "windows"

    def __init__(self, controller) -> None:
        super().__init__(controller, "Window Behavior", "Adjust KWin focus, borders, compositing, and snap behavior through user-level Plasma settings.")
        self.backend = controller.backend
        self._build_ui()
        self.load_state()

    def _build_ui(self) -> None:
        section = SettingsSection("KWin behavior")
        self.focus_policy = QComboBox()
        populate_combo(self.focus_policy, FOCUS_POLICIES)
        self.border_size = QComboBox()
        populate_combo(self.border_size, [(value, value) for value in WINDOW_BORDER_SIZES])
        self.titlebar_layout = QComboBox()
        populate_combo(self.titlebar_layout, [(name, name) for name in TITLEBAR_LAYOUTS])
        self.animation_speed = QSlider(Qt.Orientation.Horizontal)
        self.animation_speed.setRange(0, 200)
        self.animation_label = QLabel("1.00x")
        self.animation_speed.valueChanged.connect(self._sync_animation_label)

        self.compositor = QCheckBox("Enabled")
        self.blur = QCheckBox("Enabled")
        self.transparency = QCheckBox("Enabled")
        self.snap = QCheckBox("Enabled")

        section.add_row("Focus policy", "Choose click-to-focus or focus-follows-mouse.", self.focus_policy, keywords="focus follows mouse click focus")
        section.add_row("Window border size", "Adjust KWin decoration border size.", self.border_size, keywords="border size window decoration")
        section.add_row("Titlebar layout", "Choose a supported titlebar button arrangement.", self.titlebar_layout, keywords="titlebar buttons layout")
        section.add_row("Animation speed", "Adjust the KDE animation duration factor.", self.animation_speed, self.animation_label, keywords="animation speed")
        section.add_row("Compositor", "Toggle KWin compositing where supported.", self.compositor, keywords="compositor")
        section.add_row("Blur", "Toggle the blur effect flag in KWin config.", self.blur, keywords="blur effect")
        section.add_row("Transparency", "Toggle translucency flags in KWin config.", self.transparency, keywords="transparency translucency")
        section.add_row("Window snapping", "Toggle screen-edge tiling behavior.", self.snap, keywords="snap tiling windows")
        self.add_section(section)

        apply_button = small_button("Apply", primary=True)
        apply_button.clicked.connect(self.apply_changes)
        revert_button = small_button("Revert")
        revert_button.clicked.connect(self.load_state)
        actions = SettingsSection("Apply changes")
        actions.add_widget(action_bar(apply_button, revert_button), keywords="apply revert")
        self.add_section(actions)

    def _sync_animation_label(self) -> None:
        factor = self.animation_speed.value() / 100
        self.animation_label.setText(f"{factor:.2f}x")

    def load_state(self) -> None:
        state = self.backend.window_state()
        select_combo_value(self.focus_policy, str(state["focus_policy"]))
        select_combo_value(self.border_size, str(state["border_size"]))
        select_combo_value(self.titlebar_layout, str(state["titlebar_layout"]))
        self.animation_speed.setValue(int(float(state["animation_speed"]) * 100))
        self._sync_animation_label()
        self.compositor.setChecked(bool(state["compositor_enabled"]))
        self.blur.setChecked(bool(state["blur_enabled"]))
        self.transparency.setChecked(bool(state["transparency_enabled"]))
        self.snap.setChecked(bool(state["snap_enabled"]))

    def apply_changes(self) -> None:
        values = {
            "focus_policy": self.focus_policy.currentData(),
            "border_size": self.border_size.currentData(),
            "titlebar_layout": self.titlebar_layout.currentData(),
            "animation_speed": self.animation_speed.value() / 100,
            "compositor_enabled": self.compositor.isChecked(),
            "blur_enabled": self.blur.isChecked(),
            "transparency_enabled": self.transparency.isChecked(),
            "snap_enabled": self.snap.isChecked(),
        }
        result = self.backend.apply_windows(values)
        self.show_result(result, "Window Behavior")
        self.load_state()

    def on_activated(self) -> None:
        self.load_state()
