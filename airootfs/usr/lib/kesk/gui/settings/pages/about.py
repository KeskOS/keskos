from __future__ import annotations

from PySide6.QtWidgets import QFormLayout, QLabel, QPushButton

from .base import BasePage
from ..backend import DOC_LINKS
from ..widgets import CardFrame


class AboutPage(BasePage):
    page_key = "about"

    def __init__(self, controller) -> None:
        super().__init__(controller, "About KeskOS", "VERSION // BUILD // ENVIRONMENT")
        self.fields = {}

        info_card = CardFrame("System Information", "CURRENT KESKOS AND SESSION FIELDS")
        self.form = QFormLayout()
        info_card.layout.addLayout(self.form)
        self.root_layout.insertWidget(2, info_card)

        links_card = CardFrame("Project Links", "OFFICIAL SITE, DOCS, DOWNLOADS, AND GITHUB")
        for label, url in DOC_LINKS:
            button = QPushButton(label.upper())
            button.clicked.connect(lambda _checked=False, target=url: self.controller.open_url(target))
            links_card.layout.addWidget(button)
        self.root_layout.insertWidget(3, links_card)
        self.refresh()

    def refresh(self) -> None:
        while self.form.rowCount():
            self.form.removeRow(0)
        for label, value in self.controller.about_rows():
            field = QLabel(value)
            field.setWordWrap(True)
            self.form.addRow(label, field)

    def on_activated(self) -> None:
        self.refresh()
