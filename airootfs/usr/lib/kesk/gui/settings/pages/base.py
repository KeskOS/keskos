from __future__ import annotations

from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from ..widgets import section_heading


class BasePage(QWidget):
    page_key = ""

    def __init__(self, controller, title: str, subtitle: str = "") -> None:
        super().__init__()
        self.controller = controller
        self.root_layout = QVBoxLayout(self)
        self.root_layout.setContentsMargins(18, 18, 18, 18)
        self.root_layout.setSpacing(16)
        self.root_layout.addWidget(section_heading(title))

        if subtitle:
            label = QLabel(subtitle)
            label.setObjectName("Muted")
            label.setWordWrap(True)
            self.root_layout.addWidget(label)

        self.root_layout.addStretch(0)

    def on_activated(self) -> None:
        pass
