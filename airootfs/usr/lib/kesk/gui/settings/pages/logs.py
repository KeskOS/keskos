from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QListWidget, QListWidgetItem, QMessageBox, QPushButton, QSplitter, QVBoxLayout, QWidget

from .base import BasePage
from ..widgets import CardFrame, OutputConsole


class LogsPage(BasePage):
    page_key = "logs"

    def __init__(self, controller) -> None:
        super().__init__(controller, "Logs", "LOG FILES // BACKUPS // MANUAL RESTORE PATHS")

        controls = QWidget()
        row = QHBoxLayout(controls)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["all", "upgrade", "doctor", "repair", "settings", "gui"])
        self.filter_combo.currentTextChanged.connect(self.refresh)
        row.addWidget(self.filter_combo)
        for text, callback in (
            ("REFRESH", self.refresh),
            ("OPEN LOGS FOLDER", lambda: self.controller.open_target(str(self.controller.paths.logs_dir))),
            ("CLEAR LOGS", self.clear_logs),
            ("OPEN BACKUPS FOLDER", lambda: self.controller.open_target(str(self.controller.paths.backups_dir))),
        ):
            button = QPushButton(text)
            button.clicked.connect(callback)
            row.addWidget(button)
        self.root_layout.insertWidget(2, controls)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(8)
        logs_card = CardFrame("Log Files", "SELECT A LOG TO PREVIEW OR OPEN")
        self.log_list = QListWidget()
        self.log_list.currentItemChanged.connect(self._load_log_preview)
        logs_card.layout.addWidget(self.log_list)
        left_layout.addWidget(logs_card)

        backups_card = CardFrame("Backups", "TARGETED KESK BACKUPS CREATED BY REPAIR")
        self.backup_list = QListWidget()
        self.backup_list.currentItemChanged.connect(self._load_backup_preview)
        backups_card.layout.addWidget(self.backup_list)
        left_layout.addWidget(backups_card)
        splitter.addWidget(left)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(8)

        preview_card = CardFrame("Preview", "SELECTED LOG OR BACKUP DETAILS")
        self.preview = OutputConsole()
        preview_card.layout.addWidget(self.preview)
        right_layout.addWidget(preview_card)

        actions = QWidget()
        action_row = QHBoxLayout(actions)
        action_row.setContentsMargins(0, 0, 0, 0)
        action_row.setSpacing(8)
        for text, callback in (
            ("OPEN SELECTED LOG", self.open_selected_log),
            ("COPY SELECTED PATH", self.copy_selected_path),
        ):
            button = QPushButton(text)
            button.clicked.connect(callback)
            action_row.addWidget(button)
        right_layout.addWidget(actions)
        splitter.addWidget(right)
        splitter.setSizes([360, 620])

        self.root_layout.insertWidget(3, splitter, 1)
        self.refresh()

    def refresh(self) -> None:
        prefix = self.filter_combo.currentText()
        self.log_list.clear()
        for path in self.controller.list_logs(None if prefix == "all" else prefix):
            item = QListWidgetItem(path.name)
            item.setData(Qt.ItemDataRole.UserRole, str(path))
            self.log_list.addItem(item)

        self.backup_list.clear()
        for path in self.controller.list_backups():
            item = QListWidgetItem(path.name)
            item.setData(Qt.ItemDataRole.UserRole, str(path))
            self.backup_list.addItem(item)

    def _load_log_preview(self, current, _previous) -> None:
        if current is None:
            return
        path = Path(current.data(Qt.ItemDataRole.UserRole))
        self.preview.setPlainText(self.controller.read_preview(path))

    def _load_backup_preview(self, current, _previous) -> None:
        if current is None:
            return
        path = Path(current.data(Qt.ItemDataRole.UserRole))
        self.preview.setPlainText(
            f"Backup directory: {path}\n\nManual restore reminder:\n- inspect the dated folder first\n- copy individual config files back only when needed\n- avoid restoring unrelated files blindly"
        )

    def selected_path(self) -> Path | None:
        item = self.log_list.currentItem() or self.backup_list.currentItem()
        if item is None:
            return None
        return Path(item.data(Qt.ItemDataRole.UserRole))

    def open_selected_log(self) -> None:
        path = self.selected_path()
        if path is None:
            self.preview.append_line("No item selected.")
            return
        self.controller.open_target(str(path))

    def copy_selected_path(self) -> None:
        path = self.selected_path()
        if path is None:
            self.preview.append_line("No item selected.")
            return
        QGuiApplication.clipboard().setText(str(path))
        self.preview.append_line(f"Copied path: {path}")

    def clear_logs(self) -> None:
        items = [self.log_list.item(index) for index in range(self.log_list.count())]
        if not items:
            self.preview.append_line("No logs to clear for this filter.")
            return
        if QMessageBox.question(self, "CLEAR LOGS", "Delete the currently listed log files?") != QMessageBox.StandardButton.Yes:
            return
        removed = 0
        for item in items:
            path = Path(item.data(Qt.ItemDataRole.UserRole))
            try:
                path.unlink()
            except OSError:
                continue
            removed += 1
        self.preview.append_line(f"Removed {removed} log file(s).")
        self.refresh()
