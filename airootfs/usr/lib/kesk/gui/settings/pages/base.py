from __future__ import annotations

from PySide6.QtWidgets import QLabel, QScrollArea, QVBoxLayout, QWidget

from ..widgets import SettingsSection, section_heading


class BasePage(QWidget):
    page_key = ""

    def __init__(self, controller, title: str, subtitle: str = "") -> None:
        super().__init__()
        self.controller = controller
        self.sections: list[SettingsSection] = []
        self.search_terms = f"{title} {subtitle}".lower()

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        outer.addWidget(scroll)

        self.content = QWidget()
        scroll.setWidget(self.content)
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(22, 22, 22, 22)
        self.content_layout.setSpacing(16)

        self.content_layout.addWidget(section_heading(title))
        if subtitle:
            label = QLabel(subtitle)
            label.setObjectName("Muted")
            label.setWordWrap(True)
            self.content_layout.addWidget(label)

        self.content_layout.addStretch(1)

    def add_section(self, section: SettingsSection) -> None:
        self.sections.append(section)
        self.content_layout.insertWidget(self.content_layout.count() - 1, section)

    def register_search_terms(self, *values: str) -> None:
        self.search_terms += " " + " ".join(value.lower() for value in values if value)

    def matches_query(self, query: str) -> bool:
        if not query:
            return True
        lowered = query.lower()
        if lowered in self.search_terms:
            return True
        return any(section.matches_query(lowered) for section in self.sections)

    def apply_filter(self, query: str) -> None:
        lowered = query.lower().strip()
        if not lowered:
            for section in self.sections:
                section.apply_filter("")
            return
        for section in self.sections:
            section.apply_filter(lowered)

    def show_result(self, result, title: str) -> None:
        self.controller.present_result(title, result)

    def on_activated(self) -> None:
        pass
