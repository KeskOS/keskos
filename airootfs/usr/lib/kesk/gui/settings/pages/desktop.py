from __future__ import annotations

from PySide6.QtWidgets import QCheckBox, QFileDialog, QHBoxLayout, QLineEdit, QSpinBox, QWidget

from ..widgets import SettingsSection, action_bar, small_button
from .base import BasePage


class DesktopPage(BasePage):
    page_key = "desktop"

    def __init__(self, controller) -> None:
        super().__init__(controller, "Desktop", "Adjust wallpaper, virtual desktops, and the high-level KeskOS desktop presentation layer.")
        self.backend = controller.backend
        self._build_ui()
        self.load_state()

    def _build_ui(self) -> None:
        wallpaper_section = SettingsSection("Wallpaper and shell")
        self.wallpaper_path = QLineEdit()
        choose_button = small_button("Choose File")
        choose_button.clicked.connect(self.choose_wallpaper)
        path_host = QWidget()
        path_layout = QHBoxLayout(path_host)
        path_layout.setContentsMargins(0, 0, 0, 0)
        path_layout.setSpacing(8)
        path_layout.addWidget(self.wallpaper_path, 1)
        path_layout.addWidget(choose_button)
        self.desktop_icons = QCheckBox("Show desktop icons")
        self.desktop_toolbox = QCheckBox("Show Plasma desktop toolbox")
        self.show_hidden = QCheckBox("Show hidden files on the desktop when supported")
        self.containment = QLineEdit()
        self.screen_edges = QLineEdit()

        wallpaper_section.add_row("Wallpaper file", "Desktop background path applied through Plasma wallpaper helpers.", path_host, keywords="wallpaper desktop background")
        wallpaper_section.add_row("Desktop containment", "Folder view or plain desktop containment preference stored by KeskOS.", self.containment, keywords="containment folder view desktop mode")
        wallpaper_section.add_row("Screen edge behavior", "High-level preference for the desktop edge action.", self.screen_edges, keywords="screen edge corners behavior")
        wallpaper_section.add_row("Desktop icons", "Store whether icons should remain visible on the desktop.", self.desktop_icons, keywords="icons desktop")
        wallpaper_section.add_row("Desktop toolbox", "Store whether the Plasma desktop toolbox should remain visible.", self.desktop_toolbox, keywords="toolbox plasma desktop")
        wallpaper_section.add_row("Show hidden files", "Store hidden-file visibility for folder-view style desktops.", self.show_hidden, keywords="hidden files")
        self.add_section(wallpaper_section)

        desktop_section = SettingsSection("Virtual desktops")
        self.desktop_count = QSpinBox()
        self.desktop_count.setRange(1, 8)
        desktop_section.add_row("Desktop count", "Choose how many workspaces KDE should keep active.", self.desktop_count, keywords="virtual desktops workspaces count")

        self.workspace_names: list[QLineEdit] = []
        for index in range(1, 9):
            field = QLineEdit()
            self.workspace_names.append(field)
            desktop_section.add_row(
                f"Workspace {index}",
                "Visible workspace name written into kwinrc.",
                field,
                keywords="workspace name virtual desktop",
            )
        self.add_section(desktop_section)

        apply_button = small_button("Apply", primary=True)
        apply_button.clicked.connect(self.apply_changes)
        revert_button = small_button("Revert")
        revert_button.clicked.connect(self.load_state)
        action_section = SettingsSection("Apply changes")
        action_section.add_widget(action_bar(apply_button, revert_button), keywords="apply revert")
        self.add_section(action_section)

    def choose_wallpaper(self) -> None:
        path, _selected_filter = QFileDialog.getOpenFileName(
            self,
            "Choose Wallpaper",
            self.wallpaper_path.text() or str(self.controller.backend.paths.home / "Pictures"),
            "Images (*.png *.jpg *.jpeg *.webp *.bmp *.svg)",
        )
        if path:
            self.wallpaper_path.setText(path)

    def load_state(self) -> None:
        state = self.backend.desktop_state()
        self.wallpaper_path.setText(str(state["wallpaper_path"]))
        self.desktop_icons.setChecked(bool(state["desktop_icons"]))
        self.desktop_toolbox.setChecked(bool(state["desktop_toolbox"]))
        self.show_hidden.setChecked(bool(state["desktop_show_hidden"]))
        self.containment.setText(str(state["desktop_containment"]))
        self.screen_edges.setText(str(state["screen_edge_behavior"]))
        self.desktop_count.setValue(int(state["desktop_count"]))
        names = list(state["workspace_names"])
        for index, field in enumerate(self.workspace_names):
            field.setText(names[index] if index < len(names) else str(index + 1))

    def apply_changes(self) -> None:
        values = {
            "wallpaper_path": self.wallpaper_path.text().strip(),
            "desktop_icons": self.desktop_icons.isChecked(),
            "desktop_toolbox": self.desktop_toolbox.isChecked(),
            "desktop_show_hidden": self.show_hidden.isChecked(),
            "desktop_containment": self.containment.text().strip() or "folder_view",
            "screen_edge_behavior": self.screen_edges.text().strip() or "overview",
            "desktop_count": self.desktop_count.value(),
            "workspace_names": [field.text().strip() for field in self.workspace_names],
        }
        result = self.backend.apply_desktop(values)
        self.show_result(result, "Desktop")
        self.load_state()

    def on_activated(self) -> None:
        self.load_state()
