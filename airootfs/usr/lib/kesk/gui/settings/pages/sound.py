from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QLabel, QSlider

from ..widgets import SettingsSection, action_bar, small_button
from .base import BasePage


class SoundPage(BasePage):
    page_key = "sound"

    def __init__(self, controller) -> None:
        super().__init__(controller, "Sound", "Control safe audio defaults here and defer full routing and per-device tuning to KDE’s audio module.")
        self.backend = controller.backend
        self._build_ui()
        self.load_state()

    def _build_ui(self) -> None:
        info = SettingsSection("Detected audio defaults")
        self.default_sink = QLabel()
        self.default_source = QLabel()
        info.add_row("Output device", "Current PipeWire or PulseAudio default output.", self.default_sink, keywords="output sink device")
        info.add_row("Input device", "Current PipeWire or PulseAudio default input.", self.default_source, keywords="input source microphone")
        self.add_section(info)

        control = SettingsSection("Audio controls")
        self.output_volume = QSlider(Qt.Orientation.Horizontal)
        self.output_volume.setRange(0, 150)
        self.output_muted = QCheckBox("Muted")
        self.input_volume = QSlider(Qt.Orientation.Horizontal)
        self.input_volume.setRange(0, 150)
        self.input_muted = QCheckBox("Muted")
        control.add_row("Output volume", "Set default output volume with wpctl.", self.output_volume, self.output_muted, keywords="output volume mute")
        control.add_row("Input volume", "Set default input volume with wpctl.", self.input_volume, self.input_muted, keywords="input volume mute microphone")
        self.add_section(control)

        advanced = SettingsSection("Advanced sound settings")
        open_sound = small_button("Open KDE Audio Settings")
        open_sound.clicked.connect(lambda: self.controller.open_kcm("kcm_pulseaudio"))
        advanced.add_widget(action_bar(open_sound), keywords="advanced audio sound")
        self.add_section(advanced)

        apply_button = small_button("Apply", primary=True)
        apply_button.clicked.connect(self.apply_changes)
        refresh_button = small_button("Refresh")
        refresh_button.clicked.connect(self.load_state)
        actions = SettingsSection("Apply changes")
        actions.add_widget(action_bar(apply_button, refresh_button), keywords="apply refresh")
        self.add_section(actions)

    def load_state(self) -> None:
        state = self.backend.sound_state()
        self.default_sink.setText(str(state["default_sink"]))
        self.default_source.setText(str(state["default_source"]))
        self.output_volume.setValue(int(state["output_volume"]))
        self.output_muted.setChecked(bool(state["output_muted"]))
        self.input_volume.setValue(int(state["input_volume"]))
        self.input_muted.setChecked(bool(state["input_muted"]))

    def apply_changes(self) -> None:
        values = {
            "output_volume": self.output_volume.value(),
            "output_muted": self.output_muted.isChecked(),
            "input_volume": self.input_volume.value(),
            "input_muted": self.input_muted.isChecked(),
        }
        result = self.backend.apply_sound(values)
        self.show_result(result, "Sound")
        self.load_state()

    def on_activated(self) -> None:
        self.load_state()
