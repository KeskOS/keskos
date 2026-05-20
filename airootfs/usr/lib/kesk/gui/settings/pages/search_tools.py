from __future__ import annotations

from PySide6.QtWidgets import QCheckBox, QPlainTextEdit

from ..backends.common import support_level_for_status
from ..widgets import SupportBadge, SettingsSection, StatusLabel, action_bar, control_with_hint, small_button
from .base import BasePage


class SearchToolsPage(BasePage):
    page_key = "search_tools"

    def __init__(self, controller) -> None:
        super().__init__(controller, "Search", "Control launcher search, file indexing and search plugins.")
        self.backend = controller.backend
        self._build_ui()
        self.load_state()

    def _build_ui(self) -> None:
        status = SettingsSection("Backend status", "Search settings use Baloo and KDE search modules where safe.")
        self.support_badge = SupportBadge("Loading", "work")
        self.status_label = StatusLabel("Loading backend status", "work")
        status.add_row("Support level", "Official support level for search and indexing controls on this system.", self.support_badge, keywords="search support level")
        status.add_row("Search backend", "Current availability for search and indexing settings.", self.status_label, keywords="search backend status")
        self.add_section(status)

        section = SettingsSection("Search tools", "Control launcher search, file indexing and search plugins.")
        self.krunner_enabled = QCheckBox("Enable KRunner search")
        self.krunner_enabled_hint = control_with_hint(self.krunner_enabled)
        self.file_indexing = QCheckBox("Enable file indexing")
        self.index_hidden = QCheckBox("Index hidden files")
        self.web_shortcuts = QCheckBox("Enable web shortcuts")
        self.web_shortcuts_hint = control_with_hint(self.web_shortcuts)
        self.indexed_folders = QPlainTextEdit()
        self.indexed_folders.setPlaceholderText("One folder per line")
        self.indexed_folders.setFixedHeight(96)
        self.excluded_folders = QPlainTextEdit()
        self.excluded_folders.setPlaceholderText("One folder per line")
        self.excluded_folders.setFixedHeight(96)
        section.add_row("KRunner search", "Allow the desktop launcher to search applications, windows and commands.", self.krunner_enabled_hint, keywords="krunner search")
        section.add_row("File indexing", "Enable or disable Baloo file indexing.", self.file_indexing, keywords="file indexing baloo")
        section.add_row("Index hidden files", "Include hidden folders and dotfiles in the index.", self.index_hidden, keywords="hidden files baloo")
        section.add_row("Indexed folders", "Folders included in file indexing.", self.indexed_folders, keywords="indexed folders search")
        section.add_row("Excluded folders", "Folders excluded from indexing.", self.excluded_folders, keywords="excluded folders search")
        section.add_row("Web shortcuts", "Allow KRunner to search the web with configured shortcuts.", self.web_shortcuts_hint, keywords="web shortcuts search")
        krunner = small_button("Open KRunner Settings")
        krunner.clicked.connect(lambda: self.controller.open_kcm("kcm_krunnersettings"))
        baloo = small_button("Open File Search")
        baloo.clicked.connect(lambda: self.controller.open_kcm("kcm_baloofile"))
        section.add_row("Advanced search settings", "Open KDE's search modules for plugins and indexing behavior.", action_bar(krunner, baloo), keywords="advanced search krunner baloo")
        self.add_section(section)

    def load_state(self) -> None:
        self.begin_refresh()
        state = self.backend.search_backend_state()
        status = state["status"]
        self.support_badge.set_support(support_level_for_status(status))
        self.status_label.set_status(status.summary, status.ui_kind)
        self.krunner_enabled.setChecked(bool(state["krunner_enabled"]))
        self.file_indexing.setChecked(bool(state["file_indexing"]))
        self.index_hidden.setChecked(bool(state["index_hidden_files"]))
        self.web_shortcuts.setChecked(bool(state["web_shortcuts"]))
        self.krunner_enabled_hint.set_enabled(False, "KRunner plugin control stays in KDE's advanced search modules.")
        self.web_shortcuts_hint.set_enabled(False, "Web shortcuts stay in KDE's advanced search modules.")
        self.indexed_folders.setPlainText("\n".join(state.get("indexed_folders", [])))
        self.excluded_folders.setPlainText("\n".join(state.get("excluded_folders", [])))
        self.finish_refresh()

    def apply_changes(self) -> None:
        values = {
            "file_indexing": self.file_indexing.isChecked(),
            "index_hidden_files": self.index_hidden.isChecked(),
            "indexed_folders": [line.strip() for line in self.indexed_folders.toPlainText().splitlines() if line.strip()],
            "excluded_folders": [line.strip() for line in self.excluded_folders.toPlainText().splitlines() if line.strip()],
        }
        result = self.backend.apply_search_backend(values)
        self.show_result(result, "Search")
        self.load_state()

    def on_activated(self) -> None:
        self.load_state()
