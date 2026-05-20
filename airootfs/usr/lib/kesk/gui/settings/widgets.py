from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QRadioButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from .backends.common import support_ui_kind
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


class SupportBadge(QLabel):
    def __init__(self, text: str, kind: str = "skip") -> None:
        super().__init__()
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumHeight(28)
        self.setTextFormat(Qt.TextFormat.PlainText)
        self.set_support(text, kind)

    def set_support(self, text: str, kind: str | None = None) -> None:
        badge_kind = kind or support_ui_kind(text)
        color = status_color(badge_kind)
        self.setText(text)
        self.setStyleSheet(
            f"background-color: {PANEL}; border: 1px solid {color}; color: {color}; padding: 4px 10px; font-weight: 700;"
        )


class ControlHint(QWidget):
    def __init__(self, control: QWidget) -> None:
        super().__init__()
        self.control = control
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        layout.addWidget(control)
        self.hint_label = QLabel()
        self.hint_label.setObjectName("InlineHint")
        self.hint_label.setWordWrap(True)
        self.hint_label.hide()
        layout.addWidget(self.hint_label)

    def set_reason(self, text: str = "") -> None:
        message = text.strip()
        self.hint_label.setText(message)
        self.hint_label.setVisible(bool(message))

    def set_enabled(self, enabled: bool, reason: str = "") -> None:
        self.control.setEnabled(enabled)
        self.set_reason("" if enabled else reason)


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


def control_with_hint(control: QWidget) -> ControlHint:
    return ControlHint(control)


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


def planned_toggle(text: str = "Enabled", *, checked: bool = False, radio: bool = False) -> QWidget:
    widget = QRadioButton(text) if radio else QCheckBox(text)
    widget.setChecked(checked)
    widget.setEnabled(False)
    widget.setToolTip("Backend not connected yet.")
    return widget


def planned_combo(options: list[tuple[str, str]] | list[str], current: int = 0) -> QComboBox:
    combo = QComboBox()
    normalized = []
    for option in options:
        if isinstance(option, str):
            normalized.append((option, option))
        else:
            normalized.append(option)
    populate_combo(combo, normalized)
    if 0 <= current < combo.count():
        combo.setCurrentIndex(current)
    combo.setEnabled(False)
    combo.setToolTip("Backend not connected yet.")
    return combo


def planned_button(text: str) -> QPushButton:
    button = QPushButton(text)
    button.setEnabled(False)
    button.setToolTip("Backend not connected yet.")
    return button


def planned_field(text: str = "", placeholder: str = "") -> QLineEdit:
    field = QLineEdit(text)
    field.setPlaceholderText(placeholder)
    field.setEnabled(False)
    field.setToolTip("Backend not connected yet.")
    return field


def info_list(items: list[str], empty_text: str) -> QLabel:
    label = QLabel()
    label.setWordWrap(True)
    if items:
        label.setText("\n".join(f"- {item}" for item in items))
    else:
        label.setText(empty_text)
    return label
