from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, QSize, Qt, QThreadPool, QTimer
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from common import SessionLogger

from .backend import (
    DOC_LINKS,
    GuiPrefs,
    RuntimePaths,
    about_info,
    launch_terminal_command,
    latest_log,
    list_backup_dirs,
    list_log_files,
    load_prefs,
    open_target,
    read_text_preview,
    resolve_runtime_paths,
    save_prefs,
    tool_command,
)
from .pages.about import AboutPage
from .pages.appearance import AppearancePage
from .pages.boot_login import BootLoginPage
from .pages.dashboard import DashboardPage
from .pages.desktop import DesktopPage
from .pages.logs import LogsPage
from .pages.repair import RepairPage
from .pages.system_health import SystemHealthPage
from .pages.updates import UpdatesPage
from .runner import CommandWorker, StreamProcess
from .theme import APP_SUBTITLE, APP_TITLE, stylesheet


class LogTailWatcher(QObject):
    def __init__(self, paths: RuntimePaths, prefix: str, console, logger: SessionLogger) -> None:
        super().__init__()
        self.paths = paths
        self.prefix = prefix
        self.console = console
        self.logger = logger
        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.poll)
        self.current_path: Path | None = None
        self.offset = 0
        self.idle_ticks = 0

    def start(self) -> None:
        self.poll()
        self.timer.start()

    def stop(self) -> None:
        self.timer.stop()

    def poll(self) -> None:
        path = latest_log(self.paths, self.prefix)
        if path is None:
            self.idle_ticks += 1
            if self.idle_ticks > 30:
                self.stop()
            return

        if path != self.current_path:
            self.current_path = path
            self.offset = 0
            self.idle_ticks = 0
            self.console.append_line(f"[ .. ] monitoring log: {path}")

        try:
            with path.open("r", encoding="utf-8", errors="replace") as handle:
                handle.seek(self.offset)
                chunk = handle.read()
                self.offset = handle.tell()
        except OSError as exc:
            self.console.append_line(f"[ !! ] log tail failed: {exc}")
            self.stop()
            return

        if chunk:
            self.console.append_text(chunk)
            self.idle_ticks = 0
        else:
            self.idle_ticks += 1
            if self.idle_ticks > 60:
                self.stop()


class GuiController(QObject):
    def __init__(self, root: Path) -> None:
        super().__init__()
        self.paths = resolve_runtime_paths(root)
        self.logger = SessionLogger("gui")
        self.thread_pool = QThreadPool.globalInstance()
        self.prefs = load_prefs(self.paths.config_path)
        self.window: KeskSettingsWindow | None = None
        self._streams: list[StreamProcess] = []
        self._watchers: list[LogTailWatcher] = []
        self._workers: list[CommandWorker] = []
        self._closing = False

    def set_window(self, window: "KeskSettingsWindow") -> None:
        self.window = window

    def close(self) -> None:
        self._closing = True
        for watcher in self._watchers:
            watcher.stop()
        for stream in self._streams:
            stream.kill()
        self.thread_pool.waitForDone(3000)
        self.logger.close()

    def log(self, message: str) -> None:
        self.logger.log(message)
        if self.window is not None:
            self.window.statusBar().showMessage(message, 4000)

    def confirm(self, message: str) -> bool:
        if self.window is None:
            return False
        result = QMessageBox.question(self.window, APP_TITLE, message)
        return result == QMessageBox.StandardButton.Yes

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
        self.surface_error(f"Could not open target automatically.\n{detail}")

    def open_url(self, url: str) -> None:
        self.open_target(url)

    def about_rows(self) -> list[tuple[str, str]]:
        return about_info(self.paths)

    def queue_worker(self, worker: CommandWorker, on_success, on_error=None) -> None:
        self._workers.append(worker)

        def cleanup() -> None:
            if worker in self._workers:
                self._workers.remove(worker)

        def handle_success(payload) -> None:
            cleanup()
            if self._closing:
                return
            on_success(payload)

        def handle_error(message: str) -> None:
            cleanup()
            if self._closing:
                return
            (on_error or self.surface_error)(message)

        worker.signals.finished.connect(handle_success)
        worker.signals.failed.connect(handle_error)
        self.thread_pool.start(worker)

    def run_json_tool(self, tool_name: str, args: list[str], on_success, on_error=None, *, timeout: int = 30) -> None:
        command = tool_command(self.paths, tool_name, *args)
        self.logger.log(f"gui_json_command={' '.join(command)}")
        worker = CommandWorker(command, timeout=timeout, parse_json=True)
        self.queue_worker(worker, on_success, on_error)

    def run_stream_tool(self, tool_name: str, args: list[str], console, on_finished=None) -> None:
        command = tool_command(self.paths, tool_name, *args)
        self.run_stream_command(command, console, on_finished)

    def run_stream_command(self, command: list[str], console, on_finished=None) -> None:
        self.logger.log(f"gui_stream_command={' '.join(command)}")
        stream = StreamProcess(command)
        self._streams.append(stream)
        stream.output.connect(console.append_text)
        stream.failed.connect(self.surface_error)

        def handle_finished(exit_code: int) -> None:
            if on_finished is not None:
                on_finished(exit_code)
            if stream in self._streams:
                self._streams.remove(stream)

        stream.finished.connect(handle_finished)
        stream.start()

    def launch_tool_in_terminal(self, tool_name: str, args: list[str], log_prefix: str, console) -> None:
        command = tool_command(self.paths, tool_name, *args)
        process, description = launch_terminal_command(command, self.logger)
        if process is None:
            self.surface_error(description)
            return
        console.append_line(f"[ .. ] launched in terminal: {description}")
        watcher = LogTailWatcher(self.paths, log_prefix, console, self.logger)
        self._watchers.append(watcher)
        watcher.start()

    def list_logs(self, prefix: str | None) -> list[Path]:
        return list_log_files(self.paths, prefix)

    def list_backups(self) -> list[Path]:
        return list_backup_dirs(self.paths)

    def read_preview(self, path: Path) -> str:
        return read_text_preview(path)

    def show_page(self, key: str) -> None:
        if self.window is not None:
            self.window.select_page(key)

    def page(self, key: str):
        if self.window is None:
            return None
        return self.window.page_map[key]


class KeskSettingsWindow(QMainWindow):
    page_specs = [
        ("dashboard", "Dashboard", DashboardPage),
        ("updates", "Updates", UpdatesPage),
        ("system_health", "System Doctor", SystemHealthPage),
        ("repair", "Repair", RepairPage),
        ("appearance", "Appearance", AppearancePage),
        ("desktop", "Desktop", DesktopPage),
        ("boot_login", "Boot & Login", BootLoginPage),
        ("logs", "Logs", LogsPage),
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
        self.setMinimumSize(QSize(900, 600))
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
        sidebar.setFixedWidth(230)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(12, 12, 12, 12)
        sidebar_layout.setSpacing(10)

        header = QFrame()
        header.setObjectName("TopHeader")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(18, 14, 18, 14)
        title = QLabel(APP_TITLE)
        title.setObjectName("Title")
        subtitle = QLabel(APP_SUBTITLE)
        subtitle.setObjectName("Subtitle")
        subtitle.setWordWrap(True)
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)

        right_host = QWidget()
        right_layout = QVBoxLayout(right_host)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)
        right_layout.addWidget(header)

        self.sidebar_list = QListWidget()
        for key, label, _page_class in self.page_specs:
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, key)
            self.sidebar_list.addItem(item)
        self.sidebar_list.currentRowChanged.connect(self._page_changed)
        sidebar_layout.addWidget(self.sidebar_list, 1)

        sidebar_layout.addStretch(1)
        for label, url in (("Open Docs", DOC_LINKS[0][1]), ("GitHub", DOC_LINKS[3][1]), ("Downloads", DOC_LINKS[2][1])):
            button = QPushButton(label.upper())
            button.clicked.connect(lambda _checked=False, target=url: self.controller.open_url(target))
            sidebar_layout.addWidget(button)

        self.stack = QStackedWidget()
        for key, _label, page_class in self.page_specs:
            page = page_class(self.controller)
            self.page_map[key] = page
            self.stack.addWidget(page)
        right_layout.addWidget(self.stack, 1)

        shell.addWidget(sidebar)
        shell.addWidget(right_host, 1)

        initial_page = self.controller.prefs.last_page
        self.select_page(initial_page if initial_page in self.page_map else "dashboard")
        self._ready = True

    def select_page(self, key: str) -> None:
        for row in range(self.sidebar_list.count()):
            item = self.sidebar_list.item(row)
            if item.data(Qt.ItemDataRole.UserRole) == key:
                self.sidebar_list.setCurrentRow(row)
                return

    def _page_changed(self, row: int) -> None:
        if row < 0:
            return
        item = self.sidebar_list.item(row)
        key = item.data(Qt.ItemDataRole.UserRole)
        self.controller.prefs.last_page = key
        page = self.page_map[key]
        self.stack.setCurrentWidget(page)
        if not self._ready:
            return
        self.controller.log(f"page_opened={key}")
        page.on_activated()

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
        save_prefs(self.controller.paths.config_path, self.controller.prefs)
        self.controller.close()
        super().closeEvent(event)


def build_application(root: Path) -> tuple[QApplication, KeskSettingsWindow]:
    app = QApplication.instance() or QApplication([])
    app.setApplicationName("Kesk Settings")
    app.setOrganizationName("KeskOS")
    window = KeskSettingsWindow(GuiController(root))
    return app, window
