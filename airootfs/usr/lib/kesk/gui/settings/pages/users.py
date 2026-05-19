from __future__ import annotations

from PySide6.QtWidgets import QFileDialog, QHBoxLayout, QLabel, QLineEdit, QWidget

from ..widgets import SettingsSection, action_bar, small_button
from .base import BasePage


class UsersPage(BasePage):
    page_key = "users"

    def __init__(self, controller) -> None:
        super().__init__(controller, "Users", "Show the current account context and expose the safe user-level settings that KeskOS can manage directly.")
        self.backend = controller.backend
        self._build_ui()
        self.load_state()

    def _build_ui(self) -> None:
        info = SettingsSection("Current user")
        self.username = QLabel()
        self.autologin = QLabel()
        self.display_name = QLineEdit()
        self.avatar_path = QLineEdit()
        avatar_button = small_button("Choose File")
        avatar_button.clicked.connect(self.choose_avatar)
        avatar_host = QWidget()
        avatar_layout = QHBoxLayout(avatar_host)
        avatar_layout.setContentsMargins(0, 0, 0, 0)
        avatar_layout.setSpacing(8)
        avatar_layout.addWidget(self.avatar_path, 1)
        avatar_layout.addWidget(avatar_button)

        info.add_row("Current user", "The active session user.", self.username, keywords="user account")
        info.add_row("Display name", "KeskOS alias stored for future branded surfaces.", self.display_name, keywords="display name user")
        info.add_row("Avatar", "Copy a file to ~/.face.icon for KDE-compatible avatar usage.", avatar_host, keywords="avatar face icon")
        info.add_row("Autologin", "Read-only detection from SDDM configuration.", self.autologin, keywords="autologin sddm")
        self.add_section(info)

        apply_button = small_button("Apply", primary=True)
        apply_button.clicked.connect(self.apply_changes)
        revert_button = small_button("Revert")
        revert_button.clicked.connect(self.load_state)
        actions = SettingsSection("Apply changes")
        actions.add_widget(action_bar(apply_button, revert_button), keywords="apply revert")
        self.add_section(actions)

    def choose_avatar(self) -> None:
        path, _selected_filter = QFileDialog.getOpenFileName(
            self,
            "Choose Avatar",
            self.avatar_path.text() or str(self.controller.backend.paths.home / "Pictures"),
            "Images (*.png *.jpg *.jpeg *.webp *.bmp *.svg)",
        )
        if path:
            self.avatar_path.setText(path)

    def load_state(self) -> None:
        state = self.backend.user_state()
        self.username.setText(str(state["username"]))
        self.display_name.setText(str(state["display_name"]))
        self.avatar_path.setText(str(state["avatar_path"]))
        self.autologin.setText("Enabled" if state["autologin"] else "Disabled")

    def apply_changes(self) -> None:
        values = {
            "display_name": self.display_name.text().strip(),
            "avatar_path": self.avatar_path.text().strip(),
        }
        result = self.backend.apply_user(values)
        self.show_result(result, "Users")
        self.load_state()

    def on_activated(self) -> None:
        self.load_state()
