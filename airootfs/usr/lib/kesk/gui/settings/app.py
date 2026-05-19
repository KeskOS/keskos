from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, QSize, Qt
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QStackedWidget,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from common import SessionLogger

from .backend import ApplyResult, SettingsBackend, launch_terminal_command, load_prefs, open_target, resolve_runtime_paths, save_prefs
from .pages.about import AboutPage
from .pages.appearance import AppearancePage
from .pages.boot import BootPage
from .pages.defaults import DefaultsPage
from .pages.desktop import DesktopPage
from .pages.display import DisplayPage
from .pages.input import InputPage
from .pages.kesk import KeskPage
from .pages.network import NetworkPage
from .pages.panels import PanelsPage
from .pages.power import PowerPage
from .pages.sound import SoundPage
from .pages.updates import UpdatesPage
from .pages.users import UsersPage
from .pages.windows import WindowsPage
from .theme import APP_SUBTITLE, APP_TITLE, stylesheet


class GuiController(QObject):
    def __init__(self, root: Path) -> None:
        super().__init__()
        self.paths = resolve_runtime_paths(root)
        self.logger = SessionLogger("settings-gui")
        self.backend = SettingsBackend(self.paths, self.logger)
        self.prefs = load_prefs(self.paths.ui_state_path)
        self.window: KeskSettingsWindow | None = None

    def set_window(self, window: "KeskSettingsWindow") -> None:
        self.window = window

    def close(self) -> None:
        self.logger.close()

    def log(self, message: str) -> None:
        self.logger.log(message)
        if self.window is not None:
            self.window.statusBar().showMessage(message, 4000)

    def surface_error(self, message: str) -> None:
        self.logger.log(f"gui_error={message}")
        if self.window is not None:
            self.window.statusBar().showMessage(message, 6000)
            QMessageBox.warning(self.window, APP_TITLE, message)

    def open_target(self, target: str) -> None:
        ok, detail = open_target(target, self.logger)
        if ok:
            self.log(f"opened {target}")
            return
        self.surface_error(f"Could not open {target} automatically.\n{detail}")

    def open_url(self, url: str) -> None:
        self.open_target(url)

    def open_kcm(self, module: str) -> None:
        ok, detail = self.backend.open_kcm(module)
        if ok:
            self.log(f"opened {module}")
            return
        self.surface_error(f"Could not open KDE settings module.\n{detail}")

    def launch_upgrade(self) -> None:
        command = self.backend.tool_command("upgrade")
        process, description = launch_terminal_command(command, self.logger)
        if process is None:
            self.surface_error(description)
            return
        self.log(f"launched in terminal: {description}")

    def present_result(self, title: str, result: ApplyResult) -> None:
        self.logger.log(f"apply_result={title}:{result.summary}")
        for line in result.details:
            self.logger.log(f"detail {line}")
        for line in result.warnings:
            self.logger.log(f"warning {line}")
        for line in result.requires:
            self.logger.log(f"requires {line}")
        if result.backup_path is not None:
            self.logger.log(f"backup {result.backup_path}")

        if self.window is not None:
            self.window.statusBar().showMessage(result.summary, 6000)

        detail_lines = list(result.details)
        if result.backup_path is not None:
            detail_lines.append(f"Backup: {result.backup_path}")
        detail_lines.extend(result.requires)
        detail_lines.extend(f"Warning: {warning}" for warning in result.warnings)
        if detail_lines:
            box = QMessageBox(self.window)
            box.setWindowTitle(title)
            box.setIcon(QMessageBox.Icon.Information if result.success else QMessageBox.Icon.Warning)
            box.setText(result.summary)
            box.setDetailedText("\n".join(detail_lines))
            box.exec()
        elif not result.success:
            QMessageBox.warning(self.window, title, result.summary)


class KeskSettingsWindow(QMainWindow):
    page_specs = [
        ("appearance", "Appearance", AppearancePage),
        ("desktop", "Desktop", DesktopPage),
        ("panels", "Panel & Launcher", PanelsPage),
        ("windows", "Window Behavior", WindowsPage),
        ("input", "Input", InputPage),
        ("display", "Display", DisplayPage),
        ("sound", "Sound", SoundPage),
        ("network", "Network", NetworkPage),
        ("power", "Power", PowerPage),
        ("users", "Users", UsersPage),
        ("defaults", "Default Apps", DefaultsPage),
        ("updates", "Updates", UpdatesPage),
        ("boot", "Boot & Login", BootPage),
        ("kesk", "KeskOS", KeskPage),
        ("about", "About", AboutPage),
    ]

    def __init__(self, controller: GuiController) -> None:
        super().__init__()
        self.controller = controller
        self.controller.set_window(self)
        self.page_map = {}
        self._ready = False
        self._shown_once = False

        self.setWindowTitle("Kesk Settings")
        self.setMinimumSize(QSize(1040, 720))
        self.resize(self.controller.prefs.width, self.controller.prefs.height)
        self.setStyleSheet(stylesheet())

        status = QStatusBar()
        self.setStatusBar(status)

        central = QWidget()
        self.setCentralWidget(central)
        shell = QHBoxLayout(central)
        shell.setContentsMargins(0, 0, 0, 0)
        shell.setSpacing(0)

        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(248)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(12, 12, 12, 12)
        sidebar_layout.setSpacing(10)

        sidebar_title = QLabel("CATEGORIES")
        sidebar_title.setObjectName("CardTitle")
        sidebar_layout.addWidget(sidebar_title)

        self.sidebar_list = QListWidget()
        for key, label, _page_class in self.page_specs:
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, key)
            self.sidebar_list.addItem(item)
        self.sidebar_list.currentRowChanged.connect(self._page_changed)
        sidebar_layout.addWidget(self.sidebar_list, 1)

        footer = QLabel("KDE PLASMA + KESKOS SETTINGS")
        footer.setObjectName("Muted")
        footer.setWordWrap(True)
        sidebar_layout.addWidget(footer)

        right_host = QWidget()
        right_layout = QVBoxLayout(right_host)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        header = QFrame()
        header.setObjectName("TopHeader")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(18, 16, 18, 16)
        header_layout.setSpacing(10)
        title = QLabel(APP_TITLE)
        title.setObjectName("Title")
        subtitle = QLabel(APP_SUBTITLE)
        subtitle.setObjectName("Subtitle")
        subtitle.setWordWrap(True)
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)

        search_panel = QFrame()
        search_panel.setObjectName("SearchPanel")
        search_layout = QHBoxLayout(search_panel)
        search_layout.setContentsMargins(10, 8, 10, 8)
        search_layout.setSpacing(8)
        search_label = QLabel("SEARCH")
        search_label.setObjectName("CardTitle")
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search settings...")
        self.search_input.textChanged.connect(self._apply_search)
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_input, 1)
        header_layout.addWidget(search_panel)

        self.stack = QStackedWidget()
        for key, _label, page_class in self.page_specs:
            page = page_class(self.controller)
            self.page_map[key] = page
            self.stack.addWidget(page)

        right_layout.addWidget(header)
        right_layout.addWidget(self.stack, 1)

        shell.addWidget(sidebar)
        shell.addWidget(right_host, 1)

        initial_page = self.controller.prefs.last_page
        self.select_page(initial_page if initial_page in self.page_map else "appearance")
        self._ready = True

    def select_page(self, key: str) -> None:
        for row in range(self.sidebar_list.count()):
            item = self.sidebar_list.item(row)
            if item.data(Qt.ItemDataRole.UserRole) == key and not item.isHidden():
                self.sidebar_list.setCurrentRow(row)
                return

    def _page_changed(self, row: int) -> None:
        if row < 0:
            return
        item = self.sidebar_list.item(row)
        if item is None or item.isHidden():
            return
        key = item.data(Qt.ItemDataRole.UserRole)
        self.controller.prefs.last_page = key
        page = self.page_map[key]
        self.stack.setCurrentWidget(page)
        page.apply_filter(self.search_input.text())
        if not self._ready:
            return
        self.controller.log(f"page_opened={key}")
        page.on_activated()

    def _apply_search(self, text: str) -> None:
        query = text.strip().lower()
        first_visible_key: str | None = None
        current_key = self.controller.prefs.last_page

        for row in range(self.sidebar_list.count()):
            item = self.sidebar_list.item(row)
            key = item.data(Qt.ItemDataRole.UserRole)
            page = self.page_map[key]
            visible = not query or query in item.text().lower() or page.matches_query(query)
            item.setHidden(not visible)
            page.apply_filter(query)
            if visible and first_visible_key is None:
                first_visible_key = key

        if current_key in self.page_map:
            current_item = next(
                (self.sidebar_list.item(index) for index in range(self.sidebar_list.count()) if self.sidebar_list.item(index).data(Qt.ItemDataRole.UserRole) == current_key),
                None,
            )
            if current_item is not None and not current_item.isHidden():
                return

        if first_visible_key is not None:
            self.select_page(first_visible_key)

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        if self._shown_once:
            return
        self._shown_once = True
        current = self.stack.currentWidget()
        if current is not None:
            key = self.controller.prefs.last_page
            self.controller.log(f"page_opened={key}")
            current.on_activated()

    def closeEvent(self, event) -> None:  # noqa: N802
        self.controller.prefs.width = self.width()
        self.controller.prefs.height = self.height()
        save_prefs(self.controller.paths.ui_state_path, self.controller.prefs)
        self.controller.close()
        super().closeEvent(event)


def build_application(root: Path) -> tuple[QApplication, KeskSettingsWindow]:
    app = QApplication.instance() or QApplication([])
    app.setApplicationName("Kesk Settings")
    app.setOrganizationName("KeskOS")
    window = KeskSettingsWindow(GuiController(root))
    return app, window
