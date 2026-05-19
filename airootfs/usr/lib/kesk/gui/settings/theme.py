from __future__ import annotations

APP_TITLE = "KESK SETTINGS"
APP_SUBTITLE = "PLASMA SETTINGS // KESKOS PREFERENCES // USER-SAFE CONFIGURATION"

BACKGROUND = "#050505"
PANEL = "#11100e"
PANEL_ALT = "#0b0a09"
ACCENT = "#ce6a35"
ACCENT_SOFT = "#7b492b"
TEXT = "#ddd6cd"
MUTED = "#9d968f"
SUCCESS = "#88aa66"
WARNING = "#d69a4a"
DANGER = "#d86a54"
FIELD = "#14110e"
HOVER = "#1a1511"


def stylesheet() -> str:
    return f"""
QWidget {{
    background-color: {BACKGROUND};
    color: {TEXT};
    font-family: "Noto Sans", "DejaVu Sans", sans-serif;
    font-size: 13px;
}}
QMainWindow {{
    background-color: {BACKGROUND};
}}
QFrame#Sidebar {{
    background-color: {PANEL_ALT};
    border-right: 1px solid {ACCENT};
}}
QFrame#TopHeader {{
    background-color: {PANEL_ALT};
    border-bottom: 1px solid {ACCENT};
}}
QFrame#Card {{
    background-color: {PANEL};
    border: 1px solid {ACCENT_SOFT};
}}
QFrame#SearchPanel {{
    background-color: {PANEL};
    border: 1px solid {ACCENT_SOFT};
}}
QLabel#Title {{
    color: {ACCENT};
    font-size: 24px;
    font-weight: 700;
    font-family: "JetBrains Mono Nerd Font", "JetBrains Mono", monospace;
    letter-spacing: 1px;
}}
QLabel#Subtitle {{
    color: {MUTED};
    font-size: 12px;
    font-weight: 600;
}}
QLabel#SectionHeading {{
    color: {ACCENT};
    font-size: 22px;
    font-weight: 700;
    font-family: "JetBrains Mono Nerd Font", "JetBrains Mono", monospace;
}}
QLabel#CardTitle {{
    color: {ACCENT};
    font-size: 15px;
    font-weight: 700;
    font-family: "JetBrains Mono Nerd Font", "JetBrains Mono", monospace;
}}
QLabel#Muted {{
    color: {MUTED};
}}
QLabel#RowTitle {{
    color: {TEXT};
    font-size: 13px;
    font-weight: 600;
}}
QLabel#RowBody {{
    color: {MUTED};
    font-size: 12px;
}}
QPushButton {{
    background-color: {FIELD};
    color: {TEXT};
    border: 1px solid {ACCENT_SOFT};
    padding: 8px 12px;
    min-height: 18px;
}}
QPushButton:hover {{
    background-color: {HOVER};
    border-color: {ACCENT};
}}
QPushButton:pressed {{
    background-color: #241c17;
}}
QPushButton:disabled {{
    color: {MUTED};
    border-color: #5d4837;
}}
QPushButton#Primary {{
    border-color: {ACCENT};
}}
QPushButton#Danger {{
    border-color: {DANGER};
}}
QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
    background-color: {FIELD};
    border: 1px solid {ACCENT_SOFT};
    color: {TEXT};
    padding: 6px;
    selection-background-color: {ACCENT};
}}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
    border-color: {ACCENT};
}}
QListWidget {{
    background-color: transparent;
    border: none;
    outline: none;
}}
QListWidget::item {{
    padding: 10px 12px;
    margin: 2px 0;
    border: 1px solid transparent;
}}
QListWidget::item:selected {{
    background-color: #18120f;
    border: 1px solid {ACCENT};
    color: {ACCENT};
}}
QListWidget::item:hover {{
    background-color: {HOVER};
}}
QScrollArea {{
    border: none;
}}
QCheckBox {{
    spacing: 8px;
}}
QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border: 1px solid {ACCENT_SOFT};
    background: {FIELD};
}}
QCheckBox::indicator:checked {{
    background: {ACCENT};
    border-color: {ACCENT};
}}
QSlider::groove:horizontal {{
    height: 6px;
    background: #1a1816;
    border: 1px solid {ACCENT_SOFT};
}}
QSlider::handle:horizontal {{
    width: 16px;
    margin: -6px 0;
    background: {ACCENT};
    border: 1px solid {ACCENT};
}}
QStatusBar {{
    background-color: {PANEL_ALT};
    color: {MUTED};
    border-top: 1px solid {ACCENT_SOFT};
}}
QScrollBar:vertical {{
    background: {PANEL_ALT};
    width: 12px;
}}
QScrollBar::handle:vertical {{
    background: {ACCENT};
    min-height: 24px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
"""


def status_color(kind: str) -> str:
    return {
        "ok": SUCCESS,
        "warn": DANGER,
        "work": WARNING,
        "skip": MUTED,
    }.get(kind, MUTED)
