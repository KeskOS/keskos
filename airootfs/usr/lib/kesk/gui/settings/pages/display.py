from __future__ import annotations

from PySide6.QtWidgets import QCheckBox, QComboBox, QHBoxLayout, QLabel, QPlainTextEdit, QSlider, QWidget

from ..widgets import SettingsSection, StatusLabel, action_bar, control_with_hint, populate_combo, select_combo_value, small_button
from .base import BasePage


class DisplayPage(BasePage):
    page_key = "display"

    def __init__(self, controller) -> None:
        super().__init__(controller, "Display & Monitor", "Change resolution, scaling, refresh rate and monitor behavior.")
        self.backend = controller.backend
        self._build_ui()
        self.load_state()

    def _build_ui(self) -> None:
        status = SettingsSection("Backend status", "Live monitor layout changes stay in KDE's advanced display module to avoid unsafe black-screen situations.")
        self.status_label = StatusLabel("Loading backend status", "work")
        self.note_label = QLabel()
        self.note_label.setWordWrap(True)
        status.add_row("Backend", "Primary routing for display layout and scaling on this system.", self.status_label, keywords="display backend status")
        status.add_widget(self.note_label, keywords="display intentional kde handoff note")
        self.add_section(status)

        monitors = SettingsSection("Detected monitors", "Some display changes may require confirmation or logout.")
        self.monitor_list = QLabel()
        self.monitor_list.setWordWrap(True)
        self.output_summary = QPlainTextEdit()
        self.output_summary.setReadOnly(True)
        self.output_summary.setMinimumHeight(140)
        monitors.add_row(
            "Monitor list",
            "Connected outputs reported by the current display stack.",
            self.monitor_list,
            keywords="monitor list outputs displays",
        )
        monitors.add_widget(self.output_summary, keywords="display outputs summary resolution refresh scale")
        self.add_section(monitors)

        controls = SettingsSection("Display controls", "Resolution, scaling, refresh rate and monitor behavior.")
        self.resolution = QComboBox()
        populate_combo(
            self.resolution,
            [
                ("Automatic", "Automatic"),
                ("1920x1080", "1920x1080"),
                ("2560x1440", "2560x1440"),
                ("3840x2160", "3840x2160"),
            ],
        )
        self.refresh_rate = QComboBox()
        populate_combo(self.refresh_rate, [("60", "60 Hz"), ("75", "75 Hz"), ("120", "120 Hz"), ("144", "144 Hz")])
        self.scale = QComboBox()
        populate_combo(self.scale, [("100", "100%"), ("125", "125%"), ("150", "150%"), ("175", "175%"), ("200", "200%")])
        self.orientation = QComboBox()
        populate_combo(
            self.orientation,
            [("Normal", "Normal"), ("Left", "Left"), ("Right", "Right"), ("Inverted", "Inverted")],
        )
        self.night_color = QCheckBox("Enabled")
        self.night_color_hint = control_with_hint(self.night_color)
        self.brightness = QSlider()
        self.brightness.setRange(0, 100)
        self.brightness_caption = QLabel("100%")
        self.brightness_caption.setMinimumWidth(56)
        self.brightness.valueChanged.connect(lambda value: self.brightness_caption.setText(f"{value}%"))
        self.resolution_hint = control_with_hint(self.resolution)
        self.refresh_rate_hint = control_with_hint(self.refresh_rate)
        self.scale_hint = control_with_hint(self.scale)
        self.orientation_hint = control_with_hint(self.orientation)
        brightness_host = QWidget()
        brightness_layout = QHBoxLayout(brightness_host)
        brightness_layout.setContentsMargins(0, 0, 0, 0)
        brightness_layout.setSpacing(8)
        brightness_layout.addWidget(self.brightness)
        brightness_layout.addWidget(self.brightness_caption)
        self.brightness_hint = control_with_hint(brightness_host)

        controls.add_row("Resolution", "Preferred resolution for the active monitor.", self.resolution_hint, keywords="resolution display monitor")
        controls.add_row("Refresh rate", "Preferred refresh rate for the active monitor.", self.refresh_rate_hint, keywords="refresh rate display monitor")
        controls.add_row("Scale", "Desktop scaling percentage for readable UI sizing.", self.scale_hint, keywords="display scale dpi")
        controls.add_row("Orientation", "Rotate the active display.", self.orientation_hint, keywords="orientation rotate display")
        controls.add_row("Night color", "Reduce blue light in the evening.", self.night_color_hint, keywords="night color blue light")
        controls.add_row("Brightness", "Preferred brightness level when supported by the display backend.", self.brightness_hint, keywords="brightness monitor")
        self.add_section(controls)

        advanced = SettingsSection("Advanced display settings")
        open_display = small_button("Open KDE Display Settings")
        open_display.clicked.connect(lambda: self.controller.open_kcm("kcm_kscreen"))
        advanced.add_widget(action_bar(open_display), keywords="advanced display kscreen resolution layout monitors")
        advanced.add_note("Use the advanced KDE display module for live monitor layout changes, scaling confirmation, and multi-screen placement.")
        self.add_section(advanced)

    def load_state(self) -> None:
        self.begin_refresh()
        state = self.backend.display_state()
        self.status_label.set_status(state["status"].display_label, state["status"].ui_kind)
        self.note_label.setText(
            "Display layout and scaling are opened in KDE Display Settings to avoid unsafe display changes or black-screen risk."
        )
        monitors = state.get("monitor_list") or []
        self.monitor_list.setText("\n".join(f"- {item}" for item in monitors) if monitors else "No monitor data reported.")
        self.output_summary.setPlainText(str(state["output_summary"]))
        select_combo_value(self.resolution, str(state["resolution"]))
        select_combo_value(self.refresh_rate, str(int(state["refresh_rate"])))
        select_combo_value(self.scale, str(int(state["scale_percent"])))
        select_combo_value(self.orientation, str(state["orientation"]))
        self.night_color.setChecked(bool(state["night_color"]))
        self.brightness.setValue(int(state["brightness"]))
        self.brightness_caption.setText(f"{int(state['brightness'])}%")
        reason = str(state.get("handoff_reason") or "Open KDE Display Settings for safe display changes.")
        self.resolution_hint.set_enabled(False, reason)
        self.refresh_rate_hint.set_enabled(False, reason)
        self.scale_hint.set_enabled(False, reason)
        self.orientation_hint.set_enabled(False, reason)
        self.night_color_hint.set_enabled(False, reason)
        self.brightness_hint.set_enabled(False, reason)
        self.finish_refresh()

    def apply_changes(self) -> None:
        result = self.backend.apply_display(
            {
                "night_color": self.night_color.isChecked(),
                "scale_percent": int(self.scale.currentData() or 100),
                "refresh_rate": int(self.refresh_rate.currentData() or 60),
                "orientation": self.orientation.currentData() or "Normal",
                "brightness": self.brightness.value(),
                "resolution": self.resolution.currentData() or "Automatic",
            }
        )
        self.show_result(result, "Display & Monitor")
        self.load_state()

    def can_apply(self) -> bool:
        return False

    def on_activated(self) -> None:
        self.load_state()
