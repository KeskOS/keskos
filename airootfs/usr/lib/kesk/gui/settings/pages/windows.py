from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QComboBox, QLabel, QSlider

from ..backend import FOCUS_POLICIES, TITLEBAR_LAYOUTS, WINDOW_BORDER_SIZES
from ..widgets import SettingsSection, StatusLabel, control_with_hint, planned_combo, planned_field, populate_combo, select_combo_value, small_button
from .base import BasePage


class WindowsPage(BasePage):
    page_key = "windows"

    def __init__(self, controller) -> None:
        super().__init__(controller, "Window Behavior", "Control how windows focus, move, snap and react to clicks.")
        self.backend = controller.backend
        self._build_ui()
        self.load_state()

    def _build_ui(self) -> None:
        status = SettingsSection("Backend status", "Core KWin window behavior is writable directly. Task-switcher details still use KDE's advanced KWin module.")
        self.task_switcher_status = StatusLabel("Loading backend status", "work")
        self.task_switcher_note = QLabel()
        self.task_switcher_note.setWordWrap(True)
        status.add_row("Backend", "Primary routing for Alt+Tab and task-switcher settings on this system.", self.task_switcher_status, keywords="task switcher backend status")
        status.add_widget(self.task_switcher_note, keywords="task switcher kde handoff note")
        self.add_section(status)

        behavior = SettingsSection("Window behavior", "Control how windows focus, move, snap and react to clicks.")
        self.focus_policy = QComboBox()
        populate_combo(self.focus_policy, FOCUS_POLICIES)
        self.border_size = QComboBox()
        populate_combo(self.border_size, [(value, value) for value in WINDOW_BORDER_SIZES])
        self.titlebar_layout = QComboBox()
        populate_combo(self.titlebar_layout, [(name, name) for name in TITLEBAR_LAYOUTS])
        self.animation_speed = QSlider(Qt.Orientation.Horizontal)
        self.animation_speed.setRange(0, 200)
        self.animation_label = QLabel("1.00x")
        self.animation_label.setMinimumWidth(56)
        self.animation_speed.valueChanged.connect(self._sync_animation_label)
        self.compositor = QCheckBox("Enabled")
        self.blur = QCheckBox("Enabled")
        self.transparency = QCheckBox("Enabled")
        self.snap = QCheckBox("Enabled")
        self.raise_hover = QCheckBox("Raise window on hover")
        self.active_screen_mouse = QCheckBox("Active screen follows mouse")
        self.snap_distance = QSlider(Qt.Orientation.Horizontal)
        self.snap_distance.setRange(0, 40)
        self.snap_distance_label = QLabel("10 px")
        self.snap_distance_label.setMinimumWidth(56)
        self.snap_distance.valueChanged.connect(lambda value: self.snap_distance_label.setText(f"{value} px"))
        self.double_click_action = QComboBox()
        populate_combo(
            self.double_click_action,
            [("maximize", "Maximize"), ("shade", "Shade"), ("none", "Do nothing")],
        )
        self.middle_click_action = QComboBox()
        populate_combo(
            self.middle_click_action,
            [("lower", "Lower"), ("close", "Close"), ("none", "Do nothing")],
        )

        behavior.add_row("Focus policy", "Choose click-to-focus or focus-follows-mouse.", self.focus_policy, keywords="focus policy click focus follows mouse")
        behavior.add_row("Window border size", "Adjust KWin decoration border size.", self.border_size, keywords="window border size")
        behavior.add_row("Titlebar layout", "Choose a supported titlebar button arrangement.", self.titlebar_layout, keywords="titlebar buttons layout")
        behavior.add_row("Animation speed", "Controls the speed of Plasma desktop animations.", self.animation_speed, self.animation_label, keywords="animation speed")
        behavior.add_row("Compositor", "Toggle KWin compositing where supported.", self.compositor, keywords="compositor")
        behavior.add_row("Blur", "Toggle the blur effect flag in KWin config.", self.blur, keywords="blur effect")
        behavior.add_row("Transparency", "Toggle translucency flags in KWin config.", self.transparency, keywords="transparency translucency")
        behavior.add_row("Window snapping", "Toggle screen-edge tiling behavior.", self.snap, keywords="window snapping")
        behavior.add_row("Snap distance", "Preferred snapping distance for future KWin integration.", self.snap_distance, self.snap_distance_label, keywords="snap distance")
        behavior.add_row("Raise window on hover", "Raise the focused window when using focus-follows-mouse workflows.", self.raise_hover, keywords="raise window hover")
        behavior.add_row("Double-click titlebar", "Choose the titlebar double-click action.", self.double_click_action, keywords="double click titlebar action")
        behavior.add_row("Middle-click titlebar", "Choose the titlebar middle-click action.", self.middle_click_action, keywords="middle click titlebar action")
        behavior.add_row("Active screen follows mouse", "Move keyboard focus with the pointer across screens.", self.active_screen_mouse, keywords="active screen follows mouse")
        self.add_section(behavior)

        task_switcher = SettingsSection("Task Switcher", "Change how Alt+Tab and task switching works.")
        self.task_switcher_style = planned_combo(["Thumbnail Grid", "Compact List", "Present Windows"])
        self.task_switcher_style_hint = control_with_hint(self.task_switcher_style)
        self.show_selected_window = QCheckBox("Enabled")
        self.show_selected_window_hint = control_with_hint(self.show_selected_window)
        self.include_minimized = QCheckBox("Enabled")
        self.include_minimized_hint = control_with_hint(self.include_minimized)
        self.all_desktops = QCheckBox("Enabled")
        self.all_desktops_hint = control_with_hint(self.all_desktops)
        self.sort_order = planned_combo(["Recently used", "Stacking order", "Alphabetical"])
        self.sort_order_hint = control_with_hint(self.sort_order)
        self.task_shortcut = planned_field("Alt+Tab")
        self.task_shortcut_hint = control_with_hint(self.task_shortcut)
        task_switcher.add_row("Task switcher style", "Choose the preferred Alt+Tab presentation.", self.task_switcher_style_hint, keywords="task switcher style alt tab")
        task_switcher.add_row("Show selected window", "Preview the selected window while switching.", self.show_selected_window_hint, keywords="show selected window alt tab")
        task_switcher.add_row("Include minimized windows", "Include minimized windows in Alt+Tab results.", self.include_minimized_hint, keywords="include minimized windows")
        task_switcher.add_row("All desktops", "Include windows from all virtual desktops.", self.all_desktops_hint, keywords="all desktops task switcher")
        task_switcher.add_row("Sort order", "Choose how the switcher sorts windows.", self.sort_order_hint, keywords="task switcher sort order")
        task_switcher.add_row("Shortcut", "Current shortcut used to open the task switcher.", self.task_shortcut_hint, keywords="task switcher shortcut")
        advanced_task_switcher = small_button("Open KDE Task Switcher Settings")
        advanced_task_switcher.clicked.connect(lambda: self.controller.open_kcm("kwintabbox"))
        task_switcher.add_row("Advanced task switcher", "Use KDE's advanced task-switcher module for live KWin tab-box changes.", advanced_task_switcher, keywords="advanced task switcher kwintabbox")
        self.add_section(task_switcher)

    def _sync_animation_label(self) -> None:
        factor = self.animation_speed.value() / 100
        self.animation_label.setText("INSTANT" if factor <= 0 else f"{factor:.2f}x")

    def load_state(self) -> None:
        self.begin_refresh()
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
        self.raise_hover.setChecked(False)
        self.active_screen_mouse.setChecked(False)
        self.snap_distance.setValue(10)
        self.snap_distance_label.setText("10 px")
        select_combo_value(self.double_click_action, "maximize")
        select_combo_value(self.middle_click_action, "lower")
        task_state = self.backend.task_switcher_state()
        self.task_switcher_status.set_status(task_state["status"].display_label, task_state["status"].ui_kind)
        self.task_switcher_note.setText(
            "Task switcher settings are handled by KDE/KWin. Kesk Settings opens the advanced KDE task switcher module."
        )
        self.include_minimized.setChecked(bool(task_state["include_minimized"]))
        self.all_desktops.setChecked(bool(task_state["all_desktops"]))
        self.show_selected_window.setChecked(True)
        handoff_reason = "Use KDE Task Switcher Settings for live Alt+Tab changes."
        self.task_switcher_style_hint.set_enabled(False, handoff_reason)
        self.show_selected_window_hint.set_enabled(False, handoff_reason)
        self.include_minimized_hint.set_enabled(False, handoff_reason)
        self.all_desktops_hint.set_enabled(False, handoff_reason)
        self.sort_order_hint.set_enabled(False, handoff_reason)
        self.task_shortcut_hint.set_enabled(False, handoff_reason)
        self.finish_refresh()

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
