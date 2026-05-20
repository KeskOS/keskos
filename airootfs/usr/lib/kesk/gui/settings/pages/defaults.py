from __future__ import annotations

from PySide6.QtWidgets import QCheckBox, QComboBox, QLineEdit

from ..backend import (
    BROWSER_OPTIONS,
    EDITOR_OPTIONS,
    FILE_MANAGER_OPTIONS,
    IMAGE_VIEWER_OPTIONS,
    MAIL_OPTIONS,
    MUSIC_PLAYER_OPTIONS,
    VIDEO_PLAYER_OPTIONS,
)
from ..backends.common import support_level_for_status
from ..widgets import SupportBadge, SettingsSection, StatusLabel, action_bar, populate_combo, select_combo_value, small_button
from .base import BasePage


class DefaultsPage(BasePage):
    page_key = "defaults"

    def __init__(self, controller) -> None:
        super().__init__(controller, "Default Applications", "Choose which apps open links, files and common tasks.")
        self.backend = controller.backend
        self._build_ui()
        self.load_options()
        self.load_state()

    def _build_ui(self) -> None:
        status = SettingsSection("Backend status", "Default applications are written directly; MIME handlers also use xdg-mime when available.")
        self.support_badge = SupportBadge("Loading", "work")
        self.status_label = StatusLabel("Loading backend status", "work")
        status.add_row("Support level", "Official support level for default applications and MIME controls on this system.", self.support_badge, keywords="default applications support level")
        status.add_row("Applications backend", "Current availability for default applications and file associations.", self.status_label, keywords="default apps backend status")
        self.add_section(status)

        section = SettingsSection("Preferred applications", "Choose which apps open links, files and common tasks.")
        self.browser = QComboBox()
        self.terminal = QComboBox()
        self.file_manager = QComboBox()
        self.text_editor = QComboBox()
        self.image_viewer = QComboBox()
        self.video_player = QComboBox()
        self.music_player = QComboBox()
        self.mail_app = QComboBox()

        section.add_row("Web browser", "Set the default browser through xdg-settings, xdg-mime, and mimeapps.list.", self.browser, keywords="browser default web")
        section.add_row("Terminal", "Set the default KDE terminal command preference.", self.terminal, keywords="terminal console default")
        section.add_row("File manager", "Set the handler for folders and directories.", self.file_manager, keywords="file manager default folders")
        section.add_row("Text editor", "Set the handler for plain text files.", self.text_editor, keywords="text editor default")
        section.add_row("Image viewer", "Set the default image viewer.", self.image_viewer, keywords="image viewer default")
        section.add_row("Video player", "Set the preferred video player for KeskOS defaults.", self.video_player, keywords="video player default")
        section.add_row("Music player", "Set the preferred music player for KeskOS defaults.", self.music_player, keywords="music player default")
        section.add_row("Mail app", "Set the preferred mail application.", self.mail_app, keywords="mail app default")
        self.add_section(section)

        browser = SettingsSection("Browser defaults", "Choose default browser and KeskOS browser homepage behavior.")
        self.browser_homepage = QCheckBox("Enable the KeskOS homepage")
        self.browser_theme = QCheckBox("Apply the KeskOS browser theme when supported")
        homepage_button = small_button("Open Browser Homepage Settings")
        homepage_button.clicked.connect(lambda: self.controller.open_settings_page("browser_defaults"))
        browser.add_row("KeskOS homepage", "Apply the branded KeskOS start page to supported browsers.", self.browser_homepage, keywords="browser homepage keskos")
        browser.add_row("Browser theme", "Apply the branded browser theme when a supported handler exists.", self.browser_theme, keywords="browser theme")
        browser.add_row(
            "Browser tools",
            "Open browser-default settings or trigger the detailed branded homepage page.",
            action_bar(homepage_button),
            keywords="browser defaults homepage set default browser",
        )
        self.add_section(browser)

        associations = SettingsSection("File Associations", "Choose which applications open different file types.")
        self.mime_search = QLineEdit()
        self.mime_search.setPlaceholderText("Search file type...")
        self.mime_search.textChanged.connect(self._filter_mime_types)
        self.mime_type = QComboBox()
        self.mime_type.currentIndexChanged.connect(self._sync_selected_mime)
        self.mime_default = QComboBox()
        self.mime_default.setEditable(True)
        associations.add_row("Search file type", "Find a MIME type or file extension to edit.", self.mime_search, keywords="search file type mime")
        associations.add_row("Selected file type", "The MIME type currently selected for editing.", self.mime_type, keywords="selected file type")
        associations.add_row("Default app", "The default application for the selected file type.", self.mime_default, keywords="default app mime")
        self.set_association_button = small_button("Set Default")
        self.set_association_button.clicked.connect(self.set_selected_file_association)
        self.reset_association_button = small_button("Reset Association")
        self.reset_association_button.clicked.connect(self.reset_selected_file_association)
        associations.add_row(
            "Association actions",
            "Set or reset file-type associations for the selected MIME type.",
            action_bar(self.set_association_button, self.reset_association_button),
            keywords="add app remove app reset association",
        )
        open_associations = small_button("Open KDE File Associations")
        open_associations.clicked.connect(lambda: self.controller.open_kcm("kcm_filetypes"))
        associations.add_row("Advanced file associations", "Open KDE's file-type editor for MIME routing and advanced associations.", open_associations, keywords="file associations advanced mime")
        self.add_section(associations)

    def load_options(self) -> None:
        populate_combo(self.browser, self.backend.available_desktop_options(BROWSER_OPTIONS, self.backend.default_browser_id()))
        populate_combo(self.terminal, self.backend.available_terminal_options())
        populate_combo(self.file_manager, self.backend.available_desktop_options(FILE_MANAGER_OPTIONS))
        populate_combo(self.text_editor, self.backend.available_desktop_options(EDITOR_OPTIONS))
        populate_combo(self.image_viewer, self.backend.available_desktop_options(IMAGE_VIEWER_OPTIONS))
        populate_combo(self.video_player, self.backend.available_desktop_options(VIDEO_PLAYER_OPTIONS))
        populate_combo(self.music_player, self.backend.available_desktop_options(MUSIC_PLAYER_OPTIONS))
        populate_combo(self.mail_app, self.backend.available_desktop_options(MAIL_OPTIONS))
        known_desktop_ids = sorted(self.backend.installed_desktop_ids())
        populate_combo(self.mime_default, [(desktop_id, desktop_id) for desktop_id in known_desktop_ids])

    def _filter_mime_types(self) -> None:
        current = str(self.mime_type.currentData() or "")
        matches = self.backend.search_mime_types(self.mime_search.text())
        self.mime_type.blockSignals(True)
        self.mime_type.clear()
        for mime in matches:
            self.mime_type.addItem(mime, mime)
        self.mime_type.blockSignals(False)
        if current:
            select_combo_value(self.mime_type, current)
        if self.mime_type.count() > 0 and not current:
            self._sync_selected_mime()

    def _sync_selected_mime(self) -> None:
        mime_type = str(self.mime_type.currentData() or self.mime_type.currentText()).strip()
        if not mime_type:
            self.mime_default.setCurrentText("")
            return
        current_default = self.backend.current_file_association(mime_type)
        select_combo_value(self.mime_default, current_default)
        if current_default and self.mime_default.currentData() != current_default:
            self.mime_default.setCurrentText(current_default)
        elif not current_default:
            self.mime_default.setCurrentText("")

    def load_state(self) -> None:
        self.begin_refresh()
        self.load_options()
        state = self.backend.default_apps_state()
        assoc_state = self.backend.file_associations_state()
        self.support_badge.set_support(support_level_for_status(assoc_state["status"]))
        self.status_label.set_status(assoc_state["status"].summary, assoc_state["status"].ui_kind)
        select_combo_value(self.browser, str(state["browser"]))
        select_combo_value(self.terminal, str(state["terminal"]))
        select_combo_value(self.file_manager, str(state["file_manager"]))
        select_combo_value(self.text_editor, str(state["text_editor"]))
        select_combo_value(self.image_viewer, str(state["image_viewer"]))
        select_combo_value(self.video_player, str(state["video_player"]))
        select_combo_value(self.music_player, str(state["music_player"]))
        select_combo_value(self.mail_app, str(state["mail_app"]))
        self.browser_homepage.setChecked(bool(state["browser_homepage_enabled"]))
        self.browser_theme.setChecked(bool(state["browser_theme_enabled"]))
        self._filter_mime_types()
        select_combo_value(self.mime_type, "text/plain")
        self._sync_selected_mime()
        self.finish_refresh()

    def set_selected_file_association(self) -> None:
        mime_type = str(self.mime_type.currentData() or self.mime_type.currentText()).strip()
        desktop_id = str(self.mime_default.currentData() or self.mime_default.currentText()).strip()
        result = self.backend.apply_file_association(mime_type, desktop_id)
        self.show_result(result, "File Associations")
        self.load_state()

    def reset_selected_file_association(self) -> None:
        mime_type = str(self.mime_type.currentData() or self.mime_type.currentText()).strip()
        result = self.backend.reset_file_association(mime_type)
        self.show_result(result, "File Associations")
        self.load_state()

    def apply_changes(self) -> None:
        values = {
            "browser": self.browser.currentData(),
            "terminal": self.terminal.currentData(),
            "file_manager": self.file_manager.currentData(),
            "text_editor": self.text_editor.currentData(),
            "image_viewer": self.image_viewer.currentData(),
            "video_player": self.video_player.currentData(),
            "music_player": self.music_player.currentData(),
            "mail_app": self.mail_app.currentData(),
            "browser_homepage_enabled": self.browser_homepage.isChecked(),
            "browser_theme_enabled": self.browser_theme.isChecked(),
        }
        result = self.backend.apply_default_apps(values)
        self.show_result(result, "Default Applications")
        self.load_state()

    def on_activated(self) -> None:
        self.load_state()
