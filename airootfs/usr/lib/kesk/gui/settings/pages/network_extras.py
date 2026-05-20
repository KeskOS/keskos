from __future__ import annotations

from PySide6.QtWidgets import QCheckBox, QComboBox, QFileDialog, QLabel, QLineEdit

from ..backend import ApplyResult
from ..backends.common import support_level_for_status
from ..widgets import SupportBadge, SettingsSection, StatusLabel, action_bar, populate_combo, select_combo_value, small_button
from .base import BasePage


class NetworkExtrasPage(BasePage):
    page_key = "network_extras"

    def __init__(self, controller) -> None:
        super().__init__(controller, "Advanced Networking", "Connect cloud accounts, manage VPNs, and configure proxies.")
        self.backend = controller.backend
        self._vpn_connections: list[dict] = []
        self._build_ui()
        self.load_state()

    def _build_ui(self) -> None:
        accounts = SettingsSection("Online Accounts", "Connect cloud accounts for files, calendars and other services.")
        self.accounts_badge = SupportBadge("KDE Handoff", "work")
        self.accounts_status = StatusLabel("Loading backend status", "work")
        self.accounts_note = QLabel()
        self.accounts_note.setWordWrap(True)
        self.connected_accounts = QLabel()
        self.connected_accounts.setWordWrap(True)
        self.sync_calendar = QCheckBox("Sync calendar")
        self.sync_files = QCheckBox("Sync files")
        self.sync_contacts = QCheckBox("Sync contacts")
        accounts.add_row("Support level", "Official support level for online account controls on this system.", self.accounts_badge, keywords="online accounts support level kde handoff")
        accounts.add_row("Backend", "Primary routing for online account management on this system.", self.accounts_status, keywords="backend status online accounts")
        accounts.add_widget(self.accounts_note, keywords="online accounts kde handoff note")
        accounts.add_row("Connected accounts", "Accounts currently visible through KDE or local config discovery.", self.connected_accounts, keywords="connected accounts")
        accounts.add_row("Calendar sync", "Allow connected calendars to sync into desktop apps.", self.sync_calendar, keywords="sync calendar")
        accounts.add_row("File sync", "Allow connected file providers to integrate with the desktop.", self.sync_files, keywords="sync files")
        accounts.add_row("Contact sync", "Allow contact synchronization for connected accounts.", self.sync_contacts, keywords="sync contacts")
        self.accounts_button = small_button("Open KDE Online Accounts")
        self.accounts_button.clicked.connect(lambda: self.controller.open_kcm("kcm_kaccounts"))
        accounts.add_row("Account management", "Use KDE's online-accounts module to add or remove actual providers.", self.accounts_button, keywords="kde online accounts")
        self.add_section(accounts)

        vpn = SettingsSection("VPN", "Add and manage VPN connections.")
        self.vpn_status = StatusLabel("Loading backend status", "work")
        self.vpn_selector = QComboBox()
        self.vpn_selector.currentIndexChanged.connect(self._update_selected_vpn_summary)
        self.vpn_autoconnect = QCheckBox("Enable auto-connect for the selected VPN")
        self.vpn_summary = QLabel()
        self.vpn_summary.setWordWrap(True)
        connect_button = small_button("Connect")
        connect_button.clicked.connect(self.connect_selected_vpn)
        disconnect_button = small_button("Disconnect")
        disconnect_button.clicked.connect(self.disconnect_selected_vpn)
        import_button = small_button("Import VPN Config")
        import_button.clicked.connect(self.import_vpn)
        advanced_vpn = small_button("Open Advanced Network Settings")
        advanced_vpn.clicked.connect(lambda: self.controller.open_kcm("kcm_networkmanagement"))
        vpn.add_row("VPN backend", "Current availability for VPN connections.", self.vpn_status, keywords="backend status vpn")
        vpn.add_row("VPN connections", "Configured VPN profiles from NetworkManager.", self.vpn_selector, keywords="vpn list")
        vpn.add_row("Selected VPN", "Current state for the selected VPN connection.", self.vpn_summary, keywords="vpn summary active autoconnect")
        vpn.add_row("Auto-connect", "Enable or disable automatic connection for the selected VPN.", self.vpn_autoconnect, keywords="vpn autoconnect")
        vpn.add_row("VPN actions", "Connect, disconnect, or import VPN profiles.", action_bar(connect_button, disconnect_button, import_button, advanced_vpn), keywords="vpn connect disconnect import")
        self.add_section(vpn)

        proxy = SettingsSection("Proxy", "Configure proxy servers for network access.")
        self.proxy_badge = SupportBadge("Loading", "work")
        self.proxy_status = StatusLabel("Loading backend status", "work")
        self.proxy_mode = QComboBox()
        populate_combo(self.proxy_mode, [("none", "None"), ("manual", "Manual"), ("automatic", "Automatic")])
        self.http_proxy = QLineEdit()
        self.https_proxy = QLineEdit()
        self.socks_proxy = QLineEdit()
        self.no_proxy = QLineEdit()
        self.pac_url = QLineEdit()
        self.advanced_proxy = small_button("Open KDE Proxy Settings")
        self.advanced_proxy.clicked.connect(lambda: self.controller.open_kcm("proxy"))
        proxy.add_row("Support level", "Official support level for proxy settings on this system.", self.proxy_badge, keywords="proxy support level")
        proxy.add_row("Proxy backend", "Current availability for KDE proxy settings.", self.proxy_status, keywords="backend status proxy")
        proxy.add_row("Proxy mode", "Choose whether the system uses no proxy, manual proxies, or a PAC URL.", self.proxy_mode, keywords="proxy mode")
        proxy.add_row("HTTP proxy", "Proxy used for plain HTTP requests.", self.http_proxy, keywords="http proxy")
        proxy.add_row("HTTPS proxy", "Proxy used for encrypted HTTPS requests.", self.https_proxy, keywords="https proxy")
        proxy.add_row("SOCKS proxy", "SOCKS proxy for apps that support it.", self.socks_proxy, keywords="socks proxy")
        proxy.add_row("No proxy exceptions", "Hosts and domains that should bypass the proxy.", self.no_proxy, keywords="no proxy exceptions")
        proxy.add_row("PAC URL", "URL for an automatic proxy configuration file.", self.pac_url, keywords="pac url")
        proxy.add_row("Advanced proxy settings", "Open KDE's proxy module for deep per-app behavior.", self.advanced_proxy, keywords="kde proxy advanced")
        self.add_section(proxy)

    def _vpn_name(self) -> str:
        return str(self.vpn_selector.currentData() or "").strip()

    def _update_selected_vpn_summary(self) -> None:
        selected = self._vpn_name()
        match = next((item for item in self._vpn_connections if item["name"] == selected), None)
        if match is None:
            self.vpn_summary.setText("No VPN connection is selected.")
            self.vpn_autoconnect.setChecked(False)
            return
        self.vpn_summary.setText(
            f"Type: {match['type']}\nActive: {'yes' if match['active'] else 'no'}\nAuto-connect: {'yes' if match['autoconnect'] else 'no'}"
        )
        self.vpn_autoconnect.setChecked(bool(match["autoconnect"]))

    def load_state(self) -> None:
        self.begin_refresh()
        accounts_state = self.backend.online_accounts_state()
        vpn_state = self.backend.vpn_state()
        proxy_state = self.backend.proxy_state()

        self.accounts_badge.set_support("KDE Handoff")
        self.accounts_status.set_status(accounts_state["status"].display_label, accounts_state["status"].ui_kind)
        self.accounts_note.setText(
            "Online accounts are managed through KDE's account provider system."
        )
        kcm_available = bool(self.backend.tools.get("kcmshell6") or self.backend.tools.get("systemsettings"))
        self.accounts_button.setEnabled(kcm_available)
        self.accounts_button.setToolTip("" if kcm_available else "kcmshell6 or systemsettings is required to open KDE Online Accounts.")
        self.connected_accounts.setText("\n".join(f"- {item}" for item in accounts_state.get("connected_accounts", [])) or "No connected accounts were detected.")
        self.sync_calendar.setChecked(bool(accounts_state["sync_calendar"]))
        self.sync_files.setChecked(bool(accounts_state["sync_files"]))
        self.sync_contacts.setChecked(bool(accounts_state["sync_contacts"]))

        self.vpn_status.set_status(vpn_state["status"].summary, vpn_state["status"].ui_kind)
        self._vpn_connections = list(vpn_state.get("connections", []))
        self.vpn_selector.blockSignals(True)
        self.vpn_selector.clear()
        for connection in self._vpn_connections:
            self.vpn_selector.addItem(connection["name"], connection["name"])
        self.vpn_selector.blockSignals(False)
        self._update_selected_vpn_summary()

        self.proxy_badge.set_support(support_level_for_status(proxy_state["status"]))
        self.proxy_status.set_status(proxy_state["status"].summary, proxy_state["status"].ui_kind)
        self.advanced_proxy.setEnabled(kcm_available)
        self.advanced_proxy.setToolTip("" if kcm_available else "kcmshell6 or systemsettings is required to open KDE Proxy Settings.")
        select_combo_value(self.proxy_mode, str(proxy_state["mode"]))
        self.http_proxy.setText(str(proxy_state["http_proxy"]))
        self.https_proxy.setText(str(proxy_state["https_proxy"]))
        self.socks_proxy.setText(str(proxy_state["socks_proxy"]))
        self.no_proxy.setText(str(proxy_state["no_proxy"]))
        self.pac_url.setText(str(proxy_state["pac_url"]))
        self.finish_refresh()

    def connect_selected_vpn(self) -> None:
        name = self._vpn_name()
        if not name:
            return
        result = self.backend.apply_vpn({"connect": name})
        self.show_result(result, "VPN")
        self.load_state()

    def disconnect_selected_vpn(self) -> None:
        name = self._vpn_name()
        if not name:
            return
        result = self.backend.apply_vpn({"disconnect": name})
        self.show_result(result, "VPN")
        self.load_state()

    def import_vpn(self) -> None:
        path, _selected = QFileDialog.getOpenFileName(
            self,
            "Import VPN Configuration",
            str(self.backend.paths.home),
            "VPN Config (*.ovpn *.conf);;All Files (*)",
        )
        if not path:
            return
        result = self.backend.import_vpn(path)
        self.show_result(result, "VPN")
        self.load_state()

    def apply_changes(self) -> None:
        results = [
            self.backend.apply_online_accounts(
                {
                    "sync_calendar": self.sync_calendar.isChecked(),
                    "sync_files": self.sync_files.isChecked(),
                    "sync_contacts": self.sync_contacts.isChecked(),
                }
            ),
            self.backend.apply_proxy(
                {
                    "mode": self.proxy_mode.currentData(),
                    "http_proxy": self.http_proxy.text().strip(),
                    "https_proxy": self.https_proxy.text().strip(),
                    "socks_proxy": self.socks_proxy.text().strip(),
                    "no_proxy": self.no_proxy.text().strip(),
                    "pac_url": self.pac_url.text().strip(),
                }
            ),
        ]
        if self._vpn_name():
            results.append(self.backend.apply_vpn({"autoconnect": {self._vpn_name(): self.vpn_autoconnect.isChecked()}}))

        summary = "Advanced networking settings updated."
        details: list[str] = []
        warnings: list[str] = []
        requires: list[str] = []
        success = True
        for result in results:
            success = success and result.success
            details.extend(result.details)
            warnings.extend(result.warnings)
            requires.extend(result.requires)
        combined = ApplyResult(success, summary, details=details, warnings=warnings, requires=requires)
        self.show_result(combined, "Advanced Networking")
        self.load_state()

    def on_activated(self) -> None:
        self.load_state()
