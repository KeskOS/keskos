from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QComboBox, QLabel, QSlider

from ..widgets import SettingsSection, action_bar, populate_combo, select_combo_value, small_button
from .base import BasePage


class PanelsPage(BasePage):
    page_key = "panels"

    def __init__(self, controller) -> None:
        super().__init__(controller, "Panel & Launcher", "Configure the launcher path, panel mode, and branded shell preferences without turning settings into a dashboard.")
        self.backend = controller.backend
        self._build_ui()
        self.load_state()

    def _build_ui(self) -> None:
        launcher_section = SettingsSection("Launcher")
        self.launcher_enabled = QCheckBox("Enabled")
        self.launcher_style = QComboBox()
        self.launcher_keybind = QComboBox()
        populate_combo(self.launcher_style, [("keskos", "KeskOS Launcher"), ("kde", "KDE Fallback")])
        populate_combo(self.launcher_keybind, [("Meta", "Meta"), ("Meta+Q", "Meta+Q"), ("Meta+Space", "Meta+Space")])
        launcher_section.add_row("Enable launcher", "Keep the application launcher path enabled.", self.launcher_enabled, keywords="launcher enable")
        launcher_section.add_row("Launcher style", "Choose between the branded KeskOS launcher mode and the KDE fallback.", self.launcher_style, keywords="launcher style")
        launcher_section.add_row("Launcher keybind", "Bind the launcher to Meta, Meta+Q, or Meta+Space.", self.launcher_keybind, keywords="shortcut keybind meta launcher")
        self.add_section(launcher_section)

        panel_section = SettingsSection("Panel mode")
        self.panel_mode = QComboBox()
        populate_combo(
            self.panel_mode,
            [
                ("kde_default", "KDE Default Fallback"),
                ("kesk_panel", "KeskOS Branded KDE Panel"),
                ("quickshell_hud", "Quickshell HUD Mode"),
            ],
        )
        self.top_panel = QCheckBox("Enabled")
        self.bottom_panel = QCheckBox("Enabled")
        self.auto_hide = QCheckBox("Auto-hide bottom panel")
        self.workspace_switcher = QCheckBox("Show workspace switcher")
        self.opacity = QSlider(Qt.Orientation.Horizontal)
        self.opacity.setRange(0, 100)
        self.glow = QSlider(Qt.Orientation.Horizontal)
        self.glow.setRange(0, 100)

        panel_section.add_row("Panel mode", "Apply a Plasma panel strategy from inside settings.", self.panel_mode, keywords="panel mode quickshell kde")
        panel_section.add_row("Top panel", "Store whether the top panel should remain active.", self.top_panel, keywords="top panel")
        panel_section.add_row("Bottom panel", "Store whether the bottom panel should remain active.", self.bottom_panel, keywords="bottom panel")
        panel_section.add_row("Auto-hide", "Store whether the bottom panel should auto-hide.", self.auto_hide, keywords="auto hide")
        panel_section.add_row("Workspace switcher", "Store whether the workspace switcher should be shown.", self.workspace_switcher, keywords="workspace switcher")
        panel_section.add_row("Panel opacity", "Brand preference used by compatible KeskOS panels.", self.opacity, keywords="opacity transparency panel")
        panel_section.add_row("Glow intensity", "Glow amount used by compatible branded panels.", self.glow, keywords="glow intensity orange panel")
        self.add_section(panel_section)

        note_section = SettingsSection("Notes")
        note_section.add_note("Panel layout actions may need a Plasma shell refresh. The settings app stores branded preferences and only uses helper scripts where they map cleanly to settings behavior.")
        self.add_section(note_section)

        apply_button = small_button("Apply", primary=True)
        apply_button.clicked.connect(self.apply_changes)
        revert_button = small_button("Revert")
        revert_button.clicked.connect(self.load_state)
        reset_launcher = small_button("Reset Launcher Style")
        reset_launcher.clicked.connect(lambda: select_combo_value(self.launcher_style, "keskos"))
        actions = SettingsSection("Apply changes")
        actions.add_widget(action_bar(apply_button, revert_button, reset_launcher), keywords="apply revert reset launcher")
        self.add_section(actions)

    def load_state(self) -> None:
        state = self.backend.panel_state()
        self.launcher_enabled.setChecked(bool(state["launcher_enabled"]))
        select_combo_value(self.launcher_style, str(state["launcher_style"]))
        select_combo_value(self.launcher_keybind, str(state["launcher_keybind"]))
        select_combo_value(self.panel_mode, str(state["panel_mode"]))
        self.top_panel.setChecked(bool(state["top_panel_enabled"]))
        self.bottom_panel.setChecked(bool(state["bottom_panel_enabled"]))
        self.auto_hide.setChecked(bool(state["bottom_panel_autohide"]))
        self.workspace_switcher.setChecked(bool(state["workspace_switcher"]))
        self.opacity.setValue(int(state["panel_opacity"]))
        self.glow.setValue(int(state["panel_glow_intensity"]))

    def apply_changes(self) -> None:
        values = {
            "launcher_enabled": self.launcher_enabled.isChecked(),
            "launcher_style": self.launcher_style.currentData(),
            "launcher_keybind": self.launcher_keybind.currentData(),
            "panel_mode": self.panel_mode.currentData(),
            "top_panel_enabled": self.top_panel.isChecked(),
            "bottom_panel_enabled": self.bottom_panel.isChecked(),
            "bottom_panel_autohide": self.auto_hide.isChecked(),
            "workspace_switcher": self.workspace_switcher.isChecked(),
            "panel_opacity": self.opacity.value(),
            "panel_glow_intensity": self.glow.value(),
        }
        result = self.backend.apply_panels(values)
        self.show_result(result, "Panel & Launcher")
        self.load_state()

    def on_activated(self) -> None:
        self.load_state()
