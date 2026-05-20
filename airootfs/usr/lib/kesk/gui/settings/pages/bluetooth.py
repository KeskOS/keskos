from __future__ import annotations

from PySide6.QtWidgets import QCheckBox, QComboBox, QLabel

from ..backends.common import support_level_for_status
from ..widgets import SupportBadge, SettingsSection, StatusLabel, action_bar, control_with_hint, small_button
from .base import BasePage


class BluetoothPage(BasePage):
    page_key = "bluetooth"

    def __init__(self, controller) -> None:
        super().__init__(controller, "Bluetooth", "Pair and manage Bluetooth devices.")
        self.backend = controller.backend
        self._build_ui()
        self.load_state()

    def _build_ui(self) -> None:
        status_section = SettingsSection("Backend status", "Bluetooth control depends on bluetoothctl, the bluetooth service, and an available adapter.")
        self.support_badge = SupportBadge("Loading", "work")
        self.status_label = StatusLabel("Loading backend status", "work")
        self.note_label = QLabel()
        self.note_label.setWordWrap(True)
        self.adapter_status = QLabel()
        self.service_status = QLabel()
        self.tool_status = QLabel()
        status_section.add_row("Support level", "Official support level for Bluetooth controls on this system.", self.support_badge, keywords="bluetooth support level")
        status_section.add_row("Backend", "Current availability for Bluetooth management.", self.status_label, keywords="bluetooth backend status")
        status_section.add_row("Tool", "Bluetooth device-management tool used by Kesk Settings.", self.tool_status, keywords="bluetoothctl tool state")
        status_section.add_row("Adapter", "Detected Bluetooth adapter.", self.adapter_status, keywords="bluetooth adapter")
        status_section.add_row("Service", "Current bluetooth.service state.", self.service_status, keywords="bluetooth service")
        status_section.add_widget(self.note_label, keywords="bluetooth dependency notes bluez service")
        self.add_section(status_section)

        controls = SettingsSection("Bluetooth adapter", "Pair and manage Bluetooth devices.")
        self.enabled = QCheckBox("Enable Bluetooth")
        self.enabled_hint = control_with_hint(self.enabled)
        self.receive_files = QCheckBox("Allow Bluetooth file reception")
        self.receive_files_hint = control_with_hint(self.receive_files)
        self.start_service_button = small_button("Start Bluetooth Service")
        self.start_service_button.clicked.connect(self.start_service)
        controls.add_row("Bluetooth radio", "Turn the Bluetooth radio on or off.", self.enabled_hint, keywords="bluetooth on off radio")
        controls.add_row("Receive files", "Allow file reception when a Bluetooth backend supports it.", self.receive_files_hint, keywords="receive files bluetooth")
        controls.add_row("Service control", "Start bluetooth.service if Bluetooth tools are installed but the daemon is not active.", self.start_service_button, keywords="start bluetooth service")
        self.add_section(controls)

        paired = SettingsSection("Paired devices", "Trusted or remembered Bluetooth devices.")
        self.paired_selector = QComboBox()
        self.paired_summary = QLabel()
        self.paired_summary.setWordWrap(True)
        connect_button = small_button("Connect")
        self.connect_button = connect_button
        connect_button.clicked.connect(self.connect_selected)
        disconnect_button = small_button("Disconnect")
        self.disconnect_button = disconnect_button
        disconnect_button.clicked.connect(self.disconnect_selected)
        trust_button = small_button("Trust")
        self.trust_button = trust_button
        trust_button.clicked.connect(self.trust_selected)
        remove_button = small_button("Remove")
        self.remove_button = remove_button
        remove_button.clicked.connect(self.remove_selected)
        paired.add_row("Known devices", "Select a paired device to connect, trust, or remove it.", self.paired_selector, keywords="paired devices bluetooth")
        paired.add_row("Device status", "Connection and trust information for the selected device.", self.paired_summary, keywords="paired device status")
        self.paired_actions_hint = control_with_hint(action_bar(connect_button, disconnect_button, trust_button, remove_button))
        paired.add_row("Device actions", "Connect, disconnect, trust, or remove the selected device.", self.paired_actions_hint, keywords="connect disconnect trust remove bluetooth")
        self.add_section(paired)

        nearby = SettingsSection("Nearby devices", "Detect devices nearby and pair them when the adapter is active.")
        self.nearby_selector = QComboBox()
        pair_button = small_button("Pair Selected Device")
        self.pair_button = pair_button
        pair_button.clicked.connect(self.pair_selected)
        self.scan_button = small_button("Scan for Devices")
        self.scan_button.clicked.connect(self.scan_devices)
        advanced_button = small_button("Open Bluetooth Settings")
        advanced_button.clicked.connect(lambda: self.controller.open_kcm("kcm_bluetooth"))
        nearby.add_row("Nearby devices", "Devices currently visible to bluetoothctl.", self.nearby_selector, keywords="nearby bluetooth devices pair")
        self.nearby_actions_hint = control_with_hint(action_bar(self.scan_button, pair_button))
        nearby.add_row("Pair device", "Scan on demand and pair a nearby device when the adapter and Bluetooth service are available.", self.nearby_actions_hint, keywords="pair bluetooth scan nearby")
        nearby.add_row("Advanced Bluetooth", "Open KDE's Bluetooth module for advanced flows.", advanced_button, keywords="bluetooth advanced kde")
        self.add_section(nearby)

    def _current_paired_address(self) -> str:
        return str(self.paired_selector.currentData() or "").strip()

    def _current_nearby_address(self) -> str:
        return str(self.nearby_selector.currentData() or "").strip()

    def load_state(self) -> None:
        self.begin_refresh()
        state = self.backend.bluetooth_state()
        status = state["status"]
        self.support_badge.set_support(support_level_for_status(status))
        self.status_label.set_status(status.display_label, status.ui_kind)
        self.tool_status.setText(str(state.get("tool_state", "missing")))
        self.adapter_status.setText(str(state["adapter_name"]))
        self.service_status.setText(str(state["service_state"]))
        self.enabled.setChecked(bool(state["enabled"]))
        self.receive_files.setChecked(bool(state["receive_files"]))
        notes: list[str] = []
        if status.code == "missing":
            notes.append("Install bluez for Bluetooth device management.")
        if status.code != "missing" and str(state["service_state"]) != "active":
            notes.append("Bluetooth service is not running.")
        if not bool(state.get("adapter_present")):
            notes.append("No Bluetooth adapter was detected on this system.")
        self.note_label.setText("\n\n".join(notes or [status.summary]))

        tool_reason = "Install bluez for Bluetooth device management."
        self.enabled_hint.set_enabled(status.code != "missing", tool_reason)
        self.receive_files_hint.set_enabled(status.code != "missing", tool_reason)

        self.paired_selector.blockSignals(True)
        self.paired_selector.clear()
        for device in state.get("paired_devices", []):
            label = f"{device['name']} ({device['address']})"
            self.paired_selector.addItem(label, str(device["address"]))
        self.paired_selector.blockSignals(False)
        self.nearby_selector.blockSignals(True)
        self.nearby_selector.clear()
        for device in state.get("nearby_devices", []):
            label = f"{device['name']} ({device['address']})"
            self.nearby_selector.addItem(label, str(device["address"]))
        self.nearby_selector.blockSignals(False)

        if state.get("paired_devices"):
            first = state["paired_devices"][0]
            self.paired_summary.setText(
                f"Connected: {'yes' if first.get('connected') else 'no'}\nTrusted: {'yes' if first.get('trusted') else 'no'}"
            )
        else:
            self.paired_summary.setText("No paired Bluetooth devices were found.")
        paired_reason = ""
        nearby_reason = ""
        if status.code == "missing":
            paired_reason = tool_reason
            nearby_reason = tool_reason
        elif str(state["service_state"]) != "active":
            paired_reason = "Bluetooth service is not running."
            nearby_reason = "Bluetooth service is not running."
        elif self.paired_selector.count() == 0:
            paired_reason = "No paired Bluetooth device is available."
        elif self.nearby_selector.count() == 0:
            nearby_reason = "No nearby Bluetooth device is available."
        self.paired_actions_hint.set_enabled(not bool(paired_reason), paired_reason)
        self.nearby_actions_hint.set_enabled(not bool(nearby_reason), nearby_reason)
        self.start_service_button.setEnabled(str(state["service_state"]) != "active" and bool(state.get("service_management_supported")))
        self.start_service_button.setToolTip("" if self.start_service_button.isEnabled() else "pkexec and systemctl are required to start bluetooth.service from Kesk Settings.")
        self.finish_refresh()

    def apply_changes(self) -> None:
        result = self.backend.apply_bluetooth(
            {
                "enabled": self.enabled.isChecked(),
                "receive_files": self.receive_files.isChecked(),
            }
        )
        self.show_result(result, "Bluetooth")
        self.load_state()

    def connect_selected(self) -> None:
        address = self._current_paired_address()
        if not address:
            return
        result = self.backend.bluetooth_connect_device(address)
        self.show_result(result, "Bluetooth")
        self.load_state()

    def disconnect_selected(self) -> None:
        address = self._current_paired_address()
        if not address:
            return
        result = self.backend.bluetooth_disconnect_device(address)
        self.show_result(result, "Bluetooth")
        self.load_state()

    def trust_selected(self) -> None:
        address = self._current_paired_address()
        if not address:
            return
        result = self.backend.bluetooth_trust_device(address)
        self.show_result(result, "Bluetooth")
        self.load_state()

    def remove_selected(self) -> None:
        address = self._current_paired_address()
        if not address:
            return
        if not self.controller.confirm_action("Remove Bluetooth Device", f"Remove {self.paired_selector.currentText()} from paired devices?"):
            return
        result = self.backend.bluetooth_remove_device(address)
        self.show_result(result, "Bluetooth")
        self.load_state()

    def pair_selected(self) -> None:
        address = self._current_nearby_address()
        if not address:
            return
        self.paired_summary.setText("Pairing requested. Follow any prompts from the Bluetooth stack if needed.")
        result = self.backend.bluetooth_pair_device(address)
        self.show_result(result, "Bluetooth")
        self.load_state()

    def start_service(self) -> None:
        result = self.backend.bluetooth_start_service()
        self.show_result(result, "Bluetooth")
        self.load_state()

    def scan_devices(self) -> None:
        result = self.backend.bluetooth_scan_devices()
        self.show_result(result, "Bluetooth")
        self.load_state()

    def on_activated(self) -> None:
        self.load_state()
