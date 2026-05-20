from __future__ import annotations

from PySide6.QtWidgets import QCheckBox, QLabel

from ..backends.common import support_level_for_status
from ..widgets import SupportBadge, SettingsSection, StatusLabel, action_bar, control_with_hint, planned_button, small_button
from .base import BasePage


class PrivacyPage(BasePage):
    page_key = "privacy"

    def __init__(self, controller) -> None:
        super().__init__(controller, "Privacy & Security", "Control privacy, lock-screen and app-permission behavior.")
        self.backend = controller.backend
        self._build_ui()
        self.load_state()

    def _build_ui(self) -> None:
        status = SettingsSection("Backend status", "Privacy controls mix direct cleanup and preference storage with KDE handoff for the deeper security stack.")
        self.support_badge = SupportBadge("Loading", "work")
        self.status_label = StatusLabel("Loading backend status", "work")
        self.screen_lock_timeout = QLabel()
        self.wallet_status = QLabel()
        self.firewall_status = QLabel()
        status.add_row("Support level", "Official support level for privacy and security controls on this system.", self.support_badge, keywords="privacy support level")
        status.add_row("Privacy backend", "Current availability for privacy-related settings.", self.status_label, keywords="privacy backend status")
        status.add_row("Screen lock timeout", "Current lock-screen timeout from KDE user config.", self.screen_lock_timeout, keywords="screen lock timeout")
        status.add_row("KDE Wallet", "Wallet integration state for stored credentials.", self.wallet_status, keywords="wallet status")
        status.add_row("Firewall", "Detected firewall integration state.", self.firewall_status, keywords="firewall status")
        self.add_section(status)

        section = SettingsSection("Session privacy", "Control privacy, lock-screen and app-permission behavior.")
        self.recent_files = QCheckBox("Keep recent files history")
        self.lock_after_sleep = QCheckBox("Lock after sleep")
        self.lock_after_sleep_hint = control_with_hint(self.lock_after_sleep)
        self.file_search_privacy = QCheckBox("Hide private folders from file indexing")
        clear_recent = small_button("Clear Recent Files")
        clear_recent.clicked.connect(self.clear_recent_history)
        screenlocker = small_button("Open Lock Screen Settings")
        screenlocker.clicked.connect(lambda: self.controller.open_kcm("kcm_screenlocker"))
        flatseal = planned_button("Flatpak Permissions")
        section.add_row("Recent files history", "Allow apps and shells to remember recently opened files.", self.recent_files, keywords="recent files history")
        section.add_row("Lock after sleep", "Lock the session after waking from suspend.", self.lock_after_sleep_hint, keywords="lock after sleep")
        section.add_row("File search privacy", "Hide private folders from file indexing and search.", self.file_search_privacy, keywords="file search privacy")
        section.add_row("Privacy tools", "Clear recent history or open KDE's lock-screen module.", action_bar(clear_recent, screenlocker, flatseal), keywords="clear recent history lock screen flatpak permissions")
        self.add_section(section)

    def load_state(self) -> None:
        self.begin_refresh()
        state = self.backend.privacy_state()
        status = state["status"]
        self.support_badge.set_support(support_level_for_status(status))
        self.status_label.set_status(status.summary, status.ui_kind)
        self.screen_lock_timeout.setText(f"{int(state['screen_lock_timeout_seconds'])} s")
        self.wallet_status.setText(str(state["wallet_status"]))
        self.firewall_status.setText(str(state["firewall_status"]))
        self.recent_files.setChecked(bool(state["recent_files_history"]))
        self.lock_after_sleep.setChecked(bool(state["lock_after_sleep"]))
        self.file_search_privacy.setChecked(bool(state["file_search_privacy"]))
        self.lock_after_sleep_hint.set_enabled(False, "Lock-after-sleep policy remains available through KDE's lock-screen settings.")
        self.finish_refresh()

    def clear_recent_history(self) -> None:
        if not self.controller.confirm_action("Clear Recent Files", "Clear recent files and recent-document history for this user?"):
            return
        result = self.backend.clear_recent_history()
        self.show_result(result, "Privacy & Security")
        self.load_state()

    def apply_changes(self) -> None:
        result = self.backend.apply_privacy(
            {
                "recent_files_history": self.recent_files.isChecked(),
                "lock_after_sleep": self.lock_after_sleep.isChecked(),
                "file_search_privacy": self.file_search_privacy.isChecked(),
            }
        )
        self.show_result(result, "Privacy & Security")
        self.load_state()

    def on_activated(self) -> None:
        self.load_state()
