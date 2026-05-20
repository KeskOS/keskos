from __future__ import annotations

from PySide6.QtWidgets import QCheckBox, QComboBox, QFileDialog, QHBoxLayout, QLabel, QLineEdit, QSpinBox, QWidget

from ..widgets import SupportBadge, SettingsSection, StatusLabel, action_bar, control_with_hint, populate_combo, select_combo_value, small_button
from .base import BasePage


class BootPage(BasePage):
    page_key = "boot"

    def __init__(self, controller) -> None:
        super().__init__(controller, "Boot & Login", "Change boot splash, quiet boot and login screen behavior.")
        self.backend = controller.backend
        self._build_ui()
        self.load_state()

    def _build_ui(self) -> None:
        status = SettingsSection("Backend status", "System-level boot and login changes are isolated behind a pkexec helper so the settings app itself stays unprivileged.")
        self.support_badge = SupportBadge("Loading", "work")
        self.reboot_badge = SupportBadge("Reboot may be required", "warn")
        self.status_label = StatusLabel("Loading backend status", "work")
        self.status_note = QLabel()
        self.status_note.setWordWrap(True)
        status.add_row("Support level", "Official support level for boot and login controls on this system.", self.support_badge, keywords="boot login support level requires admin limited unsupported")
        status.add_row("Reboot impact", "Boot splash, quiet boot, and Plymouth changes can require a reboot before they are visible.", self.reboot_badge, keywords="boot login reboot required")
        status.add_row("Backend", "Primary routing for boot and login changes on this system.", self.status_label, keywords="boot login backend status")
        status.add_widget(self.status_note, keywords="boot login admin note")
        self.add_section(status)

        info = SettingsSection("Detected system values", "Requires administrator permission for SDDM and Plymouth theme changes.")
        self.sddm_theme = QLabel()
        self.plymouth_theme = QLabel()
        self.bootloader_label = QLabel()
        self.reboot_status = QLabel()
        self.sddm_assets_label = QLabel()
        self.plymouth_tooling_label = QLabel()
        self.plymouth_assets_label = QLabel()
        info.add_row("Current login theme", "Detected SDDM login theme from current system configuration.", self.sddm_theme, keywords="sddm login theme")
        info.add_row("Current boot splash", "Detected Plymouth boot theme from current system configuration.", self.plymouth_theme, keywords="plymouth boot splash")
        info.add_row("SDDM assets", "Whether the required SDDM theme assets are installed for Kesk Settings to apply a login theme.", self.sddm_assets_label, keywords="sddm assets status")
        info.add_row("Plymouth tooling", "Whether the Plymouth theme command-line tooling is installed.", self.plymouth_tooling_label, keywords="plymouth tooling status")
        info.add_row("Plymouth themes", "Whether Plymouth themes are installed, including the KeskOS boot splash theme.", self.plymouth_assets_label, keywords="plymouth theme assets status")
        info.add_row("Bootloader", "Detected bootloader used for quiet-boot changes.", self.bootloader_label, keywords="bootloader grub systemd-boot")
        info.add_row("Reboot status", "Whether the system currently indicates a reboot is recommended.", self.reboot_status, keywords="reboot required")
        self.add_section(info)

        boot = SettingsSection("Boot splash", "Change boot splash, quiet boot and login screen behavior.")
        self.plymouth_selector = QComboBox()
        self.plymouth_selector_hint = control_with_hint(self.plymouth_selector)
        self.boot_splash_duration = QSpinBox()
        self.boot_splash_duration.setRange(0, 20)
        self.boot_splash_duration.setSuffix(" s")
        self.boot_splash_duration_hint = control_with_hint(self.boot_splash_duration)
        self.quiet_boot = QCheckBox("Enable quiet boot")
        self.quiet_boot_hint = control_with_hint(self.quiet_boot)
        self.show_logs = QCheckBox("Show boot logs")
        self.show_logs_hint = control_with_hint(self.show_logs)
        self.terminal_boot_text = QCheckBox("Show terminal-style boot text")
        self.terminal_boot_text_hint = control_with_hint(self.terminal_boot_text)
        boot.add_row("Plymouth theme", "Choose the KeskOS boot animation or another installed Plymouth theme.", self.plymouth_selector_hint, keywords="plymouth theme boot splash")
        boot.add_row("Minimum splash duration", "Minimum time the splash remains visible before the session appears.", self.boot_splash_duration_hint, keywords="minimum splash duration")
        boot.add_row("Quiet boot", "Hides most boot messages and shows the KeskOS splash instead.", self.quiet_boot_hint, keywords="quiet boot")
        boot.add_row("Show boot logs", "Keep kernel and service messages visible during boot.", self.show_logs_hint, keywords="boot logs")
        boot.add_row("Terminal-style boot text", "Prefer a terminal-like boot text presentation when supported.", self.terminal_boot_text_hint, keywords="terminal style boot text")
        boot_docs = small_button("Open Boot Docs")
        boot_docs.clicked.connect(lambda: self.controller.open_url("https://docs.keskos.org"))
        repair_theme = small_button("Open Repair Theme Options")
        repair_theme.clicked.connect(lambda: self.controller.open_settings_page("kesk_theme"))
        boot.add_row(
            "Boot tools",
            "Plymouth changes may require initramfs rebuilds and a reboot.",
            action_bar(boot_docs, repair_theme),
            keywords="boot docs repair initramfs",
        )
        boot.add_note("System Plymouth changes go through the dedicated Kesk Settings helper and may rebuild initramfs.")
        self.add_section(boot)

        login = SettingsSection("Login screen", "Change the login screen theme and background.")
        self.sddm_selector = QComboBox()
        self.sddm_selector_hint = control_with_hint(self.sddm_selector)
        self.show_user_list = QCheckBox("Show user list on the login screen")
        self.show_user_list_hint = control_with_hint(self.show_user_list)
        self.login_background = QLineEdit()
        background_button = small_button("Choose File")
        background_button.clicked.connect(self.choose_background)
        background_host = QWidget()
        background_layout = QHBoxLayout(background_host)
        background_layout.setContentsMargins(0, 0, 0, 0)
        background_layout.setSpacing(8)
        background_layout.addWidget(self.login_background, 1)
        background_layout.addWidget(background_button)
        self.login_background_hint = control_with_hint(background_host)
        login.add_row("SDDM theme", "Choose the login theme shown before the desktop session starts.", self.sddm_selector_hint, keywords="sddm theme login")
        login.add_row("Login background", "Pick a preferred background for future SDDM theme integration.", self.login_background_hint, keywords="login background sddm")
        login.add_row("Show user list", "Show local users on the login screen.", self.show_user_list_hint, keywords="show user list login")
        login_docs = small_button("Open Boot Docs")
        login_docs.clicked.connect(lambda: self.controller.open_url("https://docs.keskos.org"))
        login_theme = small_button("Open Repair Theme Options")
        login_theme.clicked.connect(lambda: self.controller.open_settings_page("kesk_theme"))
        login.add_row(
            "Login tools",
            "Login-screen theme changes affect the whole system and may require administrator permission.",
            action_bar(login_docs, login_theme),
            keywords="login tools sddm theme repair",
        )
        login.add_note("This affects the login screen and may require administrator permission.")
        self.add_section(login)

    def choose_background(self) -> None:
        path, _selected_filter = QFileDialog.getOpenFileName(
            self,
            "Choose Login Background",
            self.login_background.text() or str(self.controller.backend.paths.home / "Pictures"),
            "Images (*.png *.jpg *.jpeg *.webp *.bmp *.svg)",
        )
        if path:
            self.login_background.setText(path)

    def load_state(self) -> None:
        self.begin_refresh()
        state = self.backend.boot_state()
        support_level = str(state.get("support_level", "Requires Admin"))
        self.support_badge.set_support(support_level)
        self.reboot_badge.set_support("Requires Admin" if state.get("requires_reboot_for_boot_changes", True) else "Limited")
        self.status_label.set_status(support_level, {"Requires Admin": "warn", "Limited": "work", "Unsupported": "skip"}.get(support_level, "warn"))
        populate_combo(self.sddm_selector, self.backend.ensure_choice(str(state["sddm_theme"]), self.backend.sddm_theme_options()))
        populate_combo(self.plymouth_selector, self.backend.ensure_choice(str(state["plymouth_theme"]), self.backend.plymouth_theme_options()))
        select_combo_value(self.sddm_selector, str(state["sddm_theme"]))
        select_combo_value(self.plymouth_selector, str(state["plymouth_theme"]))
        self.sddm_theme.setText(str(state["sddm_theme"]))
        self.plymouth_theme.setText(str(state["plymouth_theme"]))
        self.sddm_assets_label.setText("found" if state.get("sddm_assets_found") else "missing")
        self.plymouth_tooling_label.setText("found" if state.get("plymouth_tooling_available") else "missing")
        if state.get("plymouth_theme_present"):
            self.plymouth_assets_label.setText("KeskOS theme found")
        elif state.get("plymouth_current_theme_present"):
            self.plymouth_assets_label.setText("Current theme found, KeskOS theme missing")
        else:
            self.plymouth_assets_label.setText("missing")
        self.bootloader_label.setText(str(state.get("bootloader_detected", "unknown")))
        self.reboot_status.setText("Reboot recommended" if state.get("reboot_required") else "No reboot required")
        self.boot_splash_duration.setValue(int(state["boot_splash_min_duration"]))
        self.show_logs.setChecked(bool(state["show_boot_logs"]))
        self.quiet_boot.setChecked(bool(state["quiet_boot"]))
        self.show_user_list.setChecked(bool(state.get("show_user_list", True)))
        self.terminal_boot_text.setChecked(bool(state.get("terminal_boot_text", False)))
        self.login_background.setText(str(state["login_background"]))

        notes = [
            "Boot and login settings need privileged access and installed SDDM/Plymouth assets. Bootloader editing is only enabled when a supported bootloader is detected.",
        ]
        if not bool(state.get("pkexec_found")):
            notes.append("Install polkit for privileged settings.")
        if not bool(state.get("helper_found")):
            notes.append("The Kesk Settings helper is missing on this system.")
        if not bool(state.get("sddm_assets_found")):
            notes.append("SDDM theme assets are missing on this system.")
        if not bool(state.get("plymouth_tooling_available")):
            notes.append("Plymouth tooling is missing on this system.")
        if not bool(state.get("plymouth_theme_present")):
            notes.append("The KeskOS Plymouth theme is missing on this system.")
        if not bool(state.get("quiet_boot_supported")):
            notes.append("Bootloader not recognized. Manual configuration required.")
        self.status_note.setText("\n\n".join(notes))

        sddm_reason = "Boot and login settings need privileged access and installed SDDM/Plymouth assets."
        if not bool(state.get("pkexec_found")):
            sddm_reason = "Install polkit for privileged settings."
        elif not bool(state.get("helper_found")):
            sddm_reason = "The Kesk Settings helper is missing on this system."

        plymouth_reason = "Plymouth tooling/theme missing on this system."
        if not bool(state.get("pkexec_found")):
            plymouth_reason = "Install polkit for privileged settings."
        elif not bool(state.get("helper_found")):
            plymouth_reason = "The Kesk Settings helper is missing on this system."
        elif not bool(state.get("plymouth_tooling_available")):
            plymouth_reason = "plymouth-set-default-theme is not available on this system."
        elif not bool(state.get("plymouth_theme_present")):
            plymouth_reason = "The KeskOS Plymouth theme is not installed on this system."

        duration_reason = "Boot splash timing changes need privileged access through the Kesk Settings helper."
        if not bool(state.get("pkexec_found")):
            duration_reason = "Install polkit for privileged settings."
        elif not bool(state.get("helper_found")):
            duration_reason = "The Kesk Settings helper is missing on this system."

        quiet_reason = "Bootloader not recognized. Manual configuration required."
        if not bool(state.get("pkexec_found")):
            quiet_reason = "Install polkit for privileged settings."
        elif not bool(state.get("helper_found")):
            quiet_reason = "The Kesk Settings helper is missing on this system."

        self.sddm_selector_hint.set_enabled(bool(state.get("sddm_apply_supported")) and self.sddm_selector.count() > 0, sddm_reason)
        self.login_background_hint.set_enabled(bool(state.get("sddm_apply_supported")) and self.sddm_selector.count() > 0, sddm_reason)
        self.plymouth_selector_hint.set_enabled(bool(state.get("plymouth_apply_supported")) and self.plymouth_selector.count() > 0, plymouth_reason)
        self.boot_splash_duration_hint.set_enabled(bool(state.get("helper_found")) and bool(state.get("pkexec_found")), duration_reason)
        self.quiet_boot_hint.set_enabled(bool(state.get("quiet_boot_supported")), quiet_reason)
        self.show_logs_hint.set_enabled(False, "Boot log presentation is not written directly on this backend.")
        self.terminal_boot_text_hint.set_enabled(False, "Terminal-style boot text is not written directly on this backend.")
        self.show_user_list_hint.set_enabled(False, "Login user-list behavior is not written directly by the current SDDM backend.")
        self.finish_refresh()

    def apply_changes(self) -> None:
        values = {
            "sddm_theme": self.sddm_selector.currentData(),
            "plymouth_theme": self.plymouth_selector.currentData(),
            "boot_splash_min_duration": self.boot_splash_duration.value(),
            "show_boot_logs": self.show_logs.isChecked(),
            "quiet_boot": self.quiet_boot.isChecked(),
            "show_user_list": self.show_user_list.isChecked(),
            "terminal_boot_text": self.terminal_boot_text.isChecked(),
            "login_background": self.login_background.text().strip(),
        }
        result = self.backend.apply_boot(values)
        self.show_result(result, "Boot & Login")
        self.load_state()

    def on_activated(self) -> None:
        self.load_state()
