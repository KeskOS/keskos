from __future__ import annotations

from PySide6.QtWidgets import QComboBox

from ..backend import BROWSER_OPTIONS, EDITOR_OPTIONS, FILE_MANAGER_OPTIONS, IMAGE_VIEWER_OPTIONS
from ..widgets import SettingsSection, action_bar, populate_combo, select_combo_value, small_button
from .base import BasePage


class DefaultsPage(BasePage):
    page_key = "defaults"

    def __init__(self, controller) -> None:
        super().__init__(controller, "Default Apps", "Adjust browser, terminal, file manager, editor, and image defaults without turning settings into an app launcher.")
        self.backend = controller.backend
        self._build_ui()
        self.load_options()
        self.load_state()

    def _build_ui(self) -> None:
        section = SettingsSection("Preferred applications")
        self.browser = QComboBox()
        self.terminal = QComboBox()
        self.file_manager = QComboBox()
        self.text_editor = QComboBox()
        self.image_viewer = QComboBox()
        section.add_row("Web browser", "Set the default browser through xdg-settings, xdg-mime, and mimeapps.list.", self.browser, keywords="browser default web")
        section.add_row("Terminal", "Set the default KDE terminal command preference.", self.terminal, keywords="terminal console")
        section.add_row("File manager", "Set the handler for folders and directories.", self.file_manager, keywords="file manager folders")
        section.add_row("Text editor", "Set the handler for text/plain.", self.text_editor, keywords="text editor")
        section.add_row("Image viewer", "Set the handler for image/png and image/jpeg.", self.image_viewer, keywords="image viewer")
        self.add_section(section)

        advanced = SettingsSection("Advanced file associations")
        open_associations = small_button("Open KDE File Associations")
        open_associations.clicked.connect(lambda: self.controller.open_kcm("kcm_filetypes"))
        advanced.add_widget(action_bar(open_associations), keywords="file associations advanced")
        self.add_section(advanced)

        apply_button = small_button("Apply", primary=True)
        apply_button.clicked.connect(self.apply_changes)
        revert_button = small_button("Refresh")
        revert_button.clicked.connect(self.load_state)
        actions = SettingsSection("Apply changes")
        actions.add_widget(action_bar(apply_button, revert_button), keywords="apply refresh")
        self.add_section(actions)

    def load_options(self) -> None:
        populate_combo(self.browser, self.backend.available_desktop_options(BROWSER_OPTIONS, self.backend.default_browser_id()))
        populate_combo(self.terminal, self.backend.available_terminal_options())
        populate_combo(self.file_manager, self.backend.available_desktop_options(FILE_MANAGER_OPTIONS))
        populate_combo(self.text_editor, self.backend.available_desktop_options(EDITOR_OPTIONS))
        populate_combo(self.image_viewer, self.backend.available_desktop_options(IMAGE_VIEWER_OPTIONS))

    def load_state(self) -> None:
        self.load_options()
        state = self.backend.default_apps_state()
        select_combo_value(self.browser, str(state["browser"]))
        select_combo_value(self.terminal, str(state["terminal"]))
        select_combo_value(self.file_manager, str(state["file_manager"]))
        select_combo_value(self.text_editor, str(state["text_editor"]))
        select_combo_value(self.image_viewer, str(state["image_viewer"]))

    def apply_changes(self) -> None:
        values = {
            "browser": self.browser.currentData(),
            "terminal": self.terminal.currentData(),
            "file_manager": self.file_manager.currentData(),
            "text_editor": self.text_editor.currentData(),
            "image_viewer": self.image_viewer.currentData(),
        }
        result = self.backend.apply_default_apps(values)
        self.show_result(result, "Default Apps")
        self.load_state()

    def on_activated(self) -> None:
        self.load_state()
