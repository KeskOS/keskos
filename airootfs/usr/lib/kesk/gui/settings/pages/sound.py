from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QComboBox, QLabel, QSlider

from ..backends.common import support_level_for_status
from ..widgets import SupportBadge, SettingsSection, StatusLabel, action_bar, info_list, populate_combo, select_combo_value, small_button
from .base import BasePage


class SoundPage(BasePage):
    page_key = "sound"

    def __init__(self, controller) -> None:
        super().__init__(controller, "Sound", "Choose audio devices and adjust volume levels.")
        self.backend = controller.backend
        self._build_ui()
        self.load_state()

    def _build_ui(self) -> None:
        status = SettingsSection("Backend status", "PipeWire or PulseAudio compatibility is used for direct device and volume control.")
        self.support_badge = SupportBadge("Loading", "work")
        self.status_label = StatusLabel("Loading backend status", "work")
        status.add_row("Support level", "Official support level for audio routing controls on this system.", self.support_badge, keywords="sound support level")
        status.add_row("Audio backend", "Current availability for audio routing and volume control.", self.status_label, keywords="audio backend status")
        self.add_section(status)

        devices = SettingsSection("Audio devices", "Choose audio devices and adjust volume levels.")
        self.output_device = QLabel()
        self.input_device = QLabel()
        self.output_selector = QComboBox()
        self.input_selector = QComboBox()
        self.audio_profile = QComboBox()
        populate_combo(self.audio_profile, [("Stereo", "Stereo"), ("Surround", "Surround"), ("Pro Audio", "Pro Audio")])

        devices.add_row("Output device", "Currently active output device reported by PipeWire or PulseAudio.", self.output_device, keywords="output device speakers sink")
        devices.add_row("Preferred output", "Select the default output device when audio routing is fully connected.", self.output_selector, keywords="preferred output device")
        devices.add_row("Input device", "Currently active input device reported by PipeWire or PulseAudio.", self.input_device, keywords="input device microphone source")
        devices.add_row("Preferred input", "Select the default microphone or input device when audio routing is fully connected.", self.input_selector, keywords="preferred input device microphone")
        devices.add_row("Audio profile", "Preferred audio profile stored for KeskOS and future audio backend integration.", self.audio_profile, keywords="audio profile stereo")
        self.add_section(devices)

        volume = SettingsSection("Volume", "Choose audio devices and adjust volume levels.")
        self.output_volume = QSlider(Qt.Orientation.Horizontal)
        self.output_volume.setRange(0, 150)
        self.output_caption = QLabel("50%")
        self.output_caption.setMinimumWidth(56)
        self.output_volume.valueChanged.connect(lambda value: self.output_caption.setText(f"{value}%"))
        self.output_muted = QCheckBox("Muted")
        self.input_volume = QSlider(Qt.Orientation.Horizontal)
        self.input_volume.setRange(0, 150)
        self.input_caption = QLabel("50%")
        self.input_caption.setMinimumWidth(56)
        self.input_volume.valueChanged.connect(lambda value: self.input_caption.setText(f"{value}%"))
        self.input_muted = QCheckBox("Muted")
        self.per_app = QLabel()
        self.per_app.setWordWrap(True)

        volume.add_row("Master volume", "Adjust the default output volume.", self.output_volume, self.output_caption, self.output_muted, keywords="master volume output mute")
        volume.add_row("Microphone volume", "Adjust the default microphone or input volume.", self.input_volume, self.input_caption, self.input_muted, keywords="microphone volume input mute")
        volume.add_row("Per-app volume", "Active application streams and per-app volumes.", self.per_app, keywords="per app volume streams")
        self.add_section(volume)

        advanced = SettingsSection("Advanced sound settings")
        open_sound = small_button("Open Advanced Audio Settings")
        open_sound.clicked.connect(lambda: self.controller.open_kcm("kcm_pulseaudio"))
        advanced.add_widget(action_bar(open_sound), keywords="advanced audio sound")
        self.add_section(advanced)

    def load_state(self) -> None:
        self.begin_refresh()
        state = self.backend.sound_state()
        status = state["status"]
        self.support_badge.set_support(support_level_for_status(status))
        self.status_label.set_status(status.summary, status.ui_kind)
        self.output_device.setText(str(state["default_sink"]))
        self.input_device.setText(str(state["default_source"]))
        self.output_selector.blockSignals(True)
        self.output_selector.clear()
        for device in state.get("output_devices", []):
            self.output_selector.addItem(str(device["name"]), str(device["name"]))
        self.output_selector.blockSignals(False)
        self.input_selector.blockSignals(True)
        self.input_selector.clear()
        for device in state.get("input_devices", []):
            self.input_selector.addItem(str(device["name"]), str(device["name"]))
        self.input_selector.blockSignals(False)
        self.output_selector.setEnabled(status.code != "missing" and self.output_selector.count() > 0)
        self.input_selector.setEnabled(status.code != "missing" and self.input_selector.count() > 0)
        select_combo_value(self.output_selector, str(state["default_sink"]))
        select_combo_value(self.input_selector, str(state["default_source"]))
        self.output_volume.setValue(int(state["output_volume"]))
        self.output_caption.setText(f"{int(state['output_volume'])}%")
        self.output_muted.setChecked(bool(state["output_muted"]))
        self.input_volume.setValue(int(state["input_volume"]))
        self.input_caption.setText(f"{int(state['input_volume'])}%")
        self.input_muted.setChecked(bool(state["input_muted"]))
        self.per_app.setText("\n".join(f"- {item}" for item in state.get("active_streams", [])) or "No active application streams were detected.")
        select_combo_value(self.audio_profile, str(state["audio_profile"]))
        self.finish_refresh()

    def apply_changes(self) -> None:
        values = {
            "output_device": self.output_selector.currentData(),
            "input_device": self.input_selector.currentData(),
            "output_volume": self.output_volume.value(),
            "output_muted": self.output_muted.isChecked(),
            "input_volume": self.input_volume.value(),
            "input_muted": self.input_muted.isChecked(),
            "audio_profile": self.audio_profile.currentData(),
        }
        result = self.backend.apply_sound(values)
        self.show_result(result, "Sound")
        self.load_state()

    def on_activated(self) -> None:
        self.load_state()
