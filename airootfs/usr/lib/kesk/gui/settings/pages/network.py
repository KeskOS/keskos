from __future__ import annotations

from PySide6.QtWidgets import QCheckBox, QLabel, QLineEdit

from ..widgets import SettingsSection, action_bar, small_button
from .base import BasePage


class NetworkPage(BasePage):
    page_key = "network"

    def __init__(self, controller) -> None:
        super().__init__(controller, "Network", "Expose safe network preferences here without trying to replace NetworkManager’s full management UI.")
        self.backend = controller.backend
        self._build_ui()
        self.load_state()

    def _build_ui(self) -> None:
        info = SettingsSection("Network overview")
        self.wifi_enabled = QCheckBox("Enable Wi-Fi radio")
        self.current_network = QLabel()
        self.hostname = QLineEdit()
        info.add_row("Wi-Fi", "Enable or disable the NetworkManager Wi-Fi radio.", self.wifi_enabled, keywords="wifi wireless radio")
        info.add_row("Current network", "Current active wireless network if one is connected.", self.current_network, keywords="network ssid current")
        info.add_row("Hostname", "System hostname. Changing this requires pkexec.", self.hostname, keywords="hostname computer name")
        self.add_section(info)

        advanced = SettingsSection("Advanced network settings")
        open_network = small_button("Open KDE Network Settings")
        open_network.clicked.connect(lambda: self.controller.open_kcm("kcm_networkmanagement"))
        advanced.add_widget(action_bar(open_network), keywords="advanced network manager")
        self.add_section(advanced)

        apply_button = small_button("Apply", primary=True)
        apply_button.clicked.connect(self.apply_changes)
        refresh_button = small_button("Refresh")
        refresh_button.clicked.connect(self.load_state)
        actions = SettingsSection("Apply changes")
        actions.add_widget(action_bar(apply_button, refresh_button), keywords="apply refresh")
        self.add_section(actions)

    def load_state(self) -> None:
        state = self.backend.network_state()
        if state["wifi_enabled"] is None:
            self.wifi_enabled.setCheckState(self.wifi_enabled.checkState())
            self.wifi_enabled.setEnabled(False)
        else:
            self.wifi_enabled.setEnabled(True)
            self.wifi_enabled.setChecked(bool(state["wifi_enabled"]))
        self.current_network.setText(str(state["current_network"]))
        self.hostname.setText(str(state["hostname"]))

    def apply_changes(self) -> None:
        values = {
            "wifi_enabled": self.wifi_enabled.isChecked() if self.wifi_enabled.isEnabled() else None,
            "hostname": self.hostname.text().strip(),
        }
        result = self.backend.apply_network(values)
        self.show_result(result, "Network")
        self.load_state()

    def on_activated(self) -> None:
        self.load_state()
