from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QPushButton, QTreeWidget, QTreeWidgetItem, QWidget

from .base import BasePage
from ..widgets import CardFrame, OutputConsole


class SystemHealthPage(BasePage):
    page_key = "system_health"

    def __init__(self, controller) -> None:
        super().__init__(controller, "System Doctor", "READ-ONLY SYSTEM HEALTH CHECKER")
        self._loaded = False
        self.report_path = Path.home() / "kesk-debug-report.txt"

        actions = QWidget()
        row = QHBoxLayout(actions)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)
        for text, callback in (
            ("RUN SCAN", self.refresh),
            ("EXPORT REPORT", self.export_report),
            ("OPEN LAST REPORT", self.open_last_report),
        ):
            button = QPushButton(text)
            button.clicked.connect(callback)
            row.addWidget(button)
        self.root_layout.insertWidget(2, actions)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Status", "Check"])
        self.tree.header().setStretchLastSection(True)
        self.root_layout.insertWidget(3, self.tree, 1)

        output_card = CardFrame("Doctor Output", "SCAN STATUS AND REPORT EXPORT")
        self.output_console = OutputConsole()
        output_card.layout.addWidget(self.output_console)
        self.root_layout.insertWidget(4, output_card, 1)

    def on_activated(self) -> None:
        if not self._loaded:
            self.refresh()

    def refresh(self) -> None:
        self._loaded = True
        self.output_console.append_line("[ .. ] running doctor scan")
        self.controller.run_json_tool("doctor", ["--json"], self._apply_payload, self.controller.surface_error, timeout=45)

    def _apply_payload(self, payload: dict) -> None:
        self.tree.clear()
        for section in payload.get("section_order", []):
            parent = QTreeWidgetItem([section, ""])
            parent.setFlags(parent.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            self.tree.addTopLevelItem(parent)
            for line in payload.get("sections", {}).get(section, []):
                prefix = {
                    "ok": "[ OK ]",
                    "warn": "[ !! ]",
                    "work": "[ .. ]",
                    "skip": "[ -- ]",
                }.get(line.get("kind"), "[ .. ]")
                child = QTreeWidgetItem([prefix, line.get("message", "")])
                parent.addChild(child)
                for detail in line.get("details", []):
                    child.addChild(QTreeWidgetItem(["", str(detail)]))
            parent.setExpanded(True)
        serious = payload.get("serious_issue", False)
        self.output_console.append_line("[ !! ] serious issues detected" if serious else "[ OK ] doctor scan completed")

    def export_report(self) -> None:
        self.output_console.append_line("[ .. ] exporting debug report")
        self.controller.run_json_tool("doctor", ["--export", "--json"], self._report_exported, self.controller.surface_error, timeout=45)

    def _report_exported(self, payload: dict) -> None:
        report_path = payload.get("report_path")
        if report_path:
            self.report_path = Path(report_path)
            self.output_console.append_line(f"[ OK ] report exported: {report_path}")
        else:
            self.output_console.append_line("[ !! ] report export failed")

    def open_last_report(self) -> None:
        if not self.report_path.exists():
            self.output_console.append_line(f"[ !! ] report not found: {self.report_path}")
            return
        self.controller.open_target(str(self.report_path))
