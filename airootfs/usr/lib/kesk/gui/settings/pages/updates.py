from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QPushButton, QTreeWidget, QTreeWidgetItem, QWidget

from .base import BasePage
from ..widgets import CardFrame, OutputConsole, StatusLabel


class UpdatesPage(BasePage):
    page_key = "updates"

    def __init__(self, controller) -> None:
        super().__init__(controller, "Updates", "OFFICIAL REPOS // AUR // FLATPAK // FWUPD")
        self._loaded = False

        status_card = CardFrame("Update Sources", "PACKAGE SOURCES AND QUICK ACTIONS")
        self.source_labels = {}
        for key, label in (
            ("official", "official repos"),
            ("aur", "AUR"),
            ("flatpak", "Flatpak"),
            ("firmware", "firmware"),
        ):
            status = StatusLabel(f"{label}: waiting", "work")
            self.source_labels[key] = status
            status_card.layout.addWidget(status)

        button_row = QWidget()
        button_layout = QHBoxLayout(button_row)
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setSpacing(8)
        for text, callback in (
            ("REFRESH", self.refresh),
            ("UPGRADE ALL", lambda: self.launch_action("--all", "upgrade all sources")),
            ("UPGRADE OFFICIAL", lambda: self.launch_action("--official", "upgrade official packages")),
            ("UPGRADE AUR", lambda: self.launch_action("--aur", "upgrade AUR packages")),
            ("UPGRADE FLATPAK", lambda: self.launch_action("--flatpak", "upgrade Flatpak packages")),
            ("UPGRADE FIRMWARE", lambda: self.launch_action("--firmware", "upgrade firmware")),
        ):
            button = QPushButton(text)
            button.clicked.connect(callback)
            button_layout.addWidget(button)
        status_card.layout.addWidget(button_row)
        self.root_layout.insertWidget(2, status_card)

        self.package_tree = QTreeWidget()
        self.package_tree.setHeaderLabels(["Detected updates"])
        self.package_tree.header().setStretchLastSection(True)
        self.root_layout.insertWidget(3, self.package_tree, 1)

        output_card = CardFrame("Output Console", "LOG STREAM AND TERMINAL HANDOFFS")
        self.output_console = OutputConsole()
        output_card.layout.addWidget(self.output_console)
        self.root_layout.insertWidget(4, output_card, 1)

    def on_activated(self) -> None:
        if not self._loaded:
            self.refresh()

    def refresh(self) -> None:
        self._loaded = True
        self.output_console.append_line("[ .. ] refreshing update inventory")
        self.controller.run_json_tool("upgrade", ["--list", "--json"], self._apply_payload, self.controller.surface_error)

    def _apply_payload(self, payload: dict) -> None:
        self.package_tree.clear()
        sources = payload.get("sources", {})
        if payload.get("pacman_lock_detected"):
            self.output_console.append_line("[ !! ] pacman lock detected; official and AUR actions may be blocked")

        for key, label in (
            ("official", "OFFICIAL REPOS"),
            ("aur", "AUR"),
            ("flatpak", "FLATPAK"),
            ("firmware", "FIRMWARE"),
        ):
            source = sources.get(key, {})
            if not source.get("available"):
                self.source_labels[key].set_status(source.get("unavailable_reason", f"{label.lower()} unavailable"), "skip")
            elif source.get("blocked_reason"):
                self.source_labels[key].set_status(source["blocked_reason"], "warn")
            elif source.get("error"):
                self.source_labels[key].set_status(source["error"], "warn")
            else:
                self.source_labels[key].set_status(f"{label.lower()}: {source.get('count', 0)} update(s)", "ok")

            top = QTreeWidgetItem([label])
            top.setFlags(top.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            self.package_tree.addTopLevelItem(top)

            items = source.get("items", [])
            if not source.get("available"):
                top.addChild(QTreeWidgetItem([source.get("unavailable_reason", "unavailable")]))
            elif source.get("blocked_reason"):
                top.addChild(QTreeWidgetItem([source["blocked_reason"]]))
            elif source.get("error"):
                top.addChild(QTreeWidgetItem([source["error"]]))
            elif items:
                for item in items:
                    top.addChild(QTreeWidgetItem([str(item)]))
            else:
                top.addChild(QTreeWidgetItem(["No updates detected"]))
            top.setExpanded(True)

        self.output_console.append_line("[ OK ] update inventory refreshed")

    def launch_action(self, flag: str, description: str) -> None:
        if not self.controller.confirm(f"Continue and {description}?"):
            self.output_console.append_line("[ -- ] upgrade action cancelled")
            return
        self.output_console.append_line(f"[ .. ] launching terminal updater for {description}")
        self.controller.launch_tool_in_terminal("upgrade", [flag, "--yes"], "upgrade", self.output_console)
