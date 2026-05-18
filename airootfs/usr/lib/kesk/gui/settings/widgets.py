from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPlainTextEdit, QVBoxLayout, QWidget

from .theme import ACCENT, MUTED, status_color


class CardFrame(QFrame):
    def __init__(self, title: str, subtitle: str = "") -> None:
        super().__init__()
        self.setObjectName("Card")
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(14, 14, 14, 14)
        self.layout.setSpacing(8)

        title_label = QLabel(title.upper())
        title_label.setObjectName("CardTitle")
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


class OutputConsole(QPlainTextEdit):
    def __init__(self) -> None:
        super().__init__()
        self.setReadOnly(True)
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        font = QFont("JetBrains Mono")
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.setFont(font)

    def append_text(self, text: str) -> None:
        if not text:
            return
        cursor = self.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        cursor.insertText(text)
        self.setTextCursor(cursor)
        self.ensureCursorVisible()

    def append_line(self, text: str) -> None:
        self.append_text(text.rstrip("\n") + "\n")


def section_heading(text: str) -> QLabel:
    label = QLabel(text.upper())
    label.setObjectName("SectionHeading")
    return label


def value_row(label_text: str, value_text: str) -> QWidget:
    widget = QWidget()
    layout = QHBoxLayout(widget)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(12)

    label = QLabel(label_text)
    label.setStyleSheet(f"color: {MUTED};")
    value = QLabel(value_text)
    value.setWordWrap(True)
    value.setStyleSheet(f"color: {ACCENT if label_text.endswith(':') else '#d8d0c8'};")
    layout.addWidget(label, 0)
    layout.addWidget(value, 1)
    return widget
