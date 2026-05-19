from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from .theme import ACCENT, MUTED, PANEL, status_color


class CardFrame(QFrame):
    def __init__(self, title: str, subtitle: str = "") -> None:
        super().__init__()
        self.setObjectName("Card")
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(16, 16, 16, 16)
        self.layout.setSpacing(12)

        title_label = QLabel(title)
        title_label.setObjectName("CardTitle")
        title_label.setWordWrap(True)
        self.layout.addWidget(title_label)

        if subtitle:
            subtitle_label = QLabel(subtitle)
            subtitle_label.setObjectName("Muted")
            subtitle_label.setWordWrap(True)
            self.layout.addWidget(subtitle_label)


class StatusLabel(QLabel):
    def __init__(self, text: str, kind: str = "skip") -> None:
        super().__init__()
        self.setTextFormat(Qt.TextFormat.PlainText)
        self.set_status(text, kind)

    def set_status(self, text: str, kind: str) -> None:
        prefix = {
            "ok": "[ OK ]",
            "warn": "[ !! ]",
            "work": "[ .. ]",
            "skip": "[ -- ]",
        }.get(kind, "[ -- ]")
        self.setText(f"{prefix} {text}")
        self.setStyleSheet(f"color: {status_color(kind)};")


class SettingsSection(CardFrame):
    def __init__(self, title: str, subtitle: str = "") -> None:
        super().__init__(title, subtitle)
        self._search_text = " ".join(part.lower() for part in (title, subtitle) if part)
        self._rows: list[tuple[QWidget, str]] = []
        self._static_widgets: list[QWidget] = []

    def add_row(self, title: str, description: str, *controls: QWidget, keywords: str = "") -> QWidget:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(14)

        text_column = QVBoxLayout()
        text_column.setContentsMargins(0, 0, 0, 0)
        text_column.setSpacing(3)
        title_label = QLabel(title)
        title_label.setObjectName("RowTitle")
        body_label = QLabel(description)
        body_label.setObjectName("RowBody")
        body_label.setWordWrap(True)
        text_column.addWidget(title_label)
        text_column.addWidget(body_label)

        layout.addLayout(text_column, 1)

        control_host = QWidget()
        control_layout = QHBoxLayout(control_host)
        control_layout.setContentsMargins(0, 0, 0, 0)
        control_layout.setSpacing(8)
        for control in controls:
            control_layout.addWidget(control)
        control_layout.addStretch(0)
        control_host.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Preferred)
        layout.addWidget(control_host, 0, Qt.AlignmentFlag.AlignTop)

        self.layout.addWidget(row)
        self._rows.append((row, " ".join([title, description, keywords]).lower()))
        return row

    def add_widget(self, widget: QWidget, *, keywords: str = "") -> None:
        self.layout.addWidget(widget)
        if keywords:
            self._rows.append((widget, keywords.lower()))
        else:
            self._static_widgets.append(widget)

    def add_note(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("Muted")
        label.setWordWrap(True)
        self.layout.addWidget(label)
        self._static_widgets.append(label)
        return label

    def matches_query(self, query: str) -> bool:
        if not query:
            return True
        lowered = query.lower()
        if lowered in self._search_text:
            return True
        return any(lowered in search_text for _widget, search_text in self._rows)

    def apply_filter(self, query: str) -> bool:
        if not query:
            for widget, _search_text in self._rows:
                widget.show()
            self.show()
            return True

        lowered = query.lower()
        section_match = lowered in self._search_text
        visible = False
        for widget, search_text in self._rows:
            row_visible = section_match or lowered in search_text
            widget.setVisible(row_visible)
            visible = visible or row_visible
        self.setVisible(visible or section_match)
        return visible or section_match


def section_heading(text: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName("SectionHeading")
    label.setWordWrap(True)
    return label


def action_bar(*buttons: QPushButton) -> QWidget:
    host = QWidget()
    layout = QHBoxLayout(host)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(8)
    for button in buttons:
        layout.addWidget(button)
    layout.addStretch(1)
    return host


def color_chip(color_value: str) -> QLabel:
    label = QLabel(color_value.upper())
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    label.setFixedHeight(32)
    label.setMinimumWidth(96)
    label.setStyleSheet(
        f"background-color: {QColor(color_value).name()}; color: #111111; border: 1px solid {ACCENT};"
    )
    return label


def image_preview(path: str, size: tuple[int, int] = (220, 124)) -> QLabel:
    label = QLabel()
    label.setFixedSize(*size)
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    label.setStyleSheet(f"background-color: {PANEL}; border: 1px solid {ACCENT}; color: {MUTED};")
    if path:
        pixmap = QPixmap(path)
        if not pixmap.isNull():
            label.setPixmap(pixmap.scaled(*size, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation))
            return label
    label.setText("NO PREVIEW")
    return label


def small_button(text: str, *, primary: bool = False, danger: bool = False) -> QPushButton:
    button = QPushButton(text)
    if primary:
        button.setObjectName("Primary")
    if danger:
        button.setObjectName("Danger")
    return button


def populate_combo(combo: QComboBox, options: list[tuple[str, str]] | list[object]) -> None:
    combo.blockSignals(True)
    combo.clear()
    for option in options:
        if hasattr(option, "value") and hasattr(option, "label"):
            value = getattr(option, "value")
            label = getattr(option, "label")
        else:
            value = option[0]
            label = option[1]
        combo.addItem(label, value)
    combo.blockSignals(False)


def select_combo_value(combo: QComboBox, value: str) -> None:
    for index in range(combo.count()):
        if combo.itemData(index) == value:
            combo.setCurrentIndex(index)
            return
