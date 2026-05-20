from __future__ import annotations

APP_TITLE = "Kesk Settings — System Settings"
APP_SUBTITLE = "SYSTEM TOOLS // DESKTOP STACK // MAINTENANCE CONSOLE"

BACKGROUND = "#050505"
MAIN_PANEL = "#070707"
SIDEBAR = "#030303"
PANEL = "#11100e"
PANEL_ALT = "#0b0a09"
ACCENT = "#ce6a35"
ACCENT_SOFT = "rgba(206,106,53,0.35)"
ACCENT_LINE = "rgba(206,106,53,0.25)"
TEXT = "#b8afa6"
MUTED = "#8f8a84"
DISABLED = "#4c4845"
SUCCESS = "#88aa66"
WARNING = "#d69a4a"
DANGER = "#d65a4a"
FIELD = "#10100f"
FIELD_ALT = "#080808"
HOVER = "rgba(206,106,53,0.14)"
ACTIVE_TEXT = "#050505"


def stylesheet() -> str:
    return f"""
QWidget {{
    background-color: {BACKGROUND};
    color: {TEXT};
    font-family: "JetBrains Mono", "Iosevka", "Noto Sans Mono", monospace;
    font-size: 13px;
}}
QMainWindow {{
    background-color: {BACKGROUND};
}}
QWidget#WindowShell {{
    background-color: {MAIN_PANEL};
    border: 1px solid {ACCENT};
}}
QFrame#TitleBar {{
    background-color: {SIDEBAR};
    border-bottom: 1px solid {ACCENT};
}}
QLabel#TitleGlyph {{
    color: {ACCENT};
    font-size: 18px;
    font-weight: 700;
}}
QLabel#TitleText {{
    color: {TEXT};
    font-size: 14px;
    font-weight: 700;
}}
QLabel#TitleSubtext {{
    color: {MUTED};
    font-size: 11px;
}}
QFrame#SidebarHost {{
    background-color: {SIDEBAR};
    border-right: 1px solid {ACCENT_LINE};
}}
QFrame#SidebarSearchRow {{
    background-color: transparent;
}}
QFrame#SidebarSearchRow QLineEdit {{
    min-height: 30px;
}}
QToolButton#SidebarToggle {{
    background-color: {FIELD_ALT};
    border: 1px solid {ACCENT_SOFT};
    color: {TEXT};
    min-width: 32px;
    min-height: 32px;
}}
QToolButton#SidebarToggle:hover {{
    background-color: {HOVER};
    border-color: {ACCENT};
}}
QLineEdit#SearchInput {{
    background-color: {FIELD_ALT};
    border: 1px solid {ACCENT_SOFT};
    color: {TEXT};
    padding: 7px 10px;
}}
QLineEdit#SearchInput:focus {{
    border-color: {ACCENT};
}}
QLabel#SidebarGroup {{
    color: {MUTED};
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 1px;
    text-transform: uppercase;
}}
QFrame#SidebarDivider {{
    background-color: {ACCENT_LINE};
    max-height: 1px;
    min-height: 1px;
}}
QToolButton#SidebarItem {{
    background-color: transparent;
    border: 1px solid transparent;
    color: {TEXT};
    text-align: left;
    padding: 6px 10px;
    min-height: 32px;
}}
QToolButton#SidebarItem:hover {{
    background-color: {HOVER};
    border-color: {ACCENT_LINE};
}}
QToolButton#SidebarItem:checked {{
    background-color: {ACCENT};
    border-color: {ACCENT};
    color: {ACTIVE_TEXT};
}}
QFrame#ContentHost {{
    background-color: {MAIN_PANEL};
}}
QFrame#ContentHeader {{
    background-color: {MAIN_PANEL};
    border-bottom: 1px solid {ACCENT_LINE};
}}
QLabel#ContentTitle {{
    color: {TEXT};
    font-size: 24px;
    font-weight: 700;
}}
QLabel#ContentSubtitle {{
    color: {MUTED};
    font-size: 12px;
}}
QFrame#ContentDivider {{
    background-color: {ACCENT_LINE};
    max-height: 1px;
    min-height: 1px;
}}
QFrame#Card {{
    background-color: {PANEL_ALT};
    border: 1px solid {ACCENT_SOFT};
}}
QLabel#CardTitle {{
    color: {ACCENT};
    font-size: 14px;
    font-weight: 700;
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
QLabel#InlineHint {{
    color: {WARNING};
    font-size: 11px;
}}
QPushButton, QToolButton, QComboBox, QSpinBox, QDoubleSpinBox {{
    background-color: {FIELD};
    color: {TEXT};
    border: 1px solid {ACCENT_SOFT};
    padding: 7px 10px;
}}
QPushButton:hover, QToolButton:hover, QComboBox:hover, QSpinBox:hover, QDoubleSpinBox:hover {{
    background-color: {HOVER};
    border-color: {ACCENT};
}}
QPushButton:disabled, QToolButton:disabled {{
    color: {DISABLED};
    border-color: rgba(76,72,69,0.6);
}}
QPushButton#Primary {{
    border-color: {ACCENT};
}}
QPushButton#Danger {{
    border-color: {DANGER};
}}
QPushButton#ThemeCard {{
    background-color: {FIELD_ALT};
    border: 1px solid {ACCENT_SOFT};
    text-align: left;
    padding: 10px;
    min-width: 136px;
    min-height: 96px;
    color: {TEXT};
}}
QPushButton#ThemeCard:hover {{
    background-color: {HOVER};
    border-color: {ACCENT};
}}
QPushButton#ThemeCard:checked {{
    background-color: rgba(206,106,53,0.22);
    border: 1px solid {ACCENT};
    color: {TEXT};
}}
QLineEdit, QTextEdit, QPlainTextEdit {{
    background-color: {FIELD};
    border: 1px solid {ACCENT_SOFT};
    color: {TEXT};
    padding: 7px 9px;
    selection-background-color: {ACCENT};
}}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
    border-color: {ACCENT};
}}
QComboBox QAbstractItemView {{
    background-color: {PANEL_ALT};
    border: 1px solid {ACCENT_SOFT};
    selection-background-color: {ACCENT};
    selection-color: {ACTIVE_TEXT};
}}
QScrollArea {{
    border: none;
}}
QCheckBox, QRadioButton {{
    spacing: 8px;
}}
QCheckBox::indicator, QRadioButton::indicator {{
    width: 16px;
    height: 16px;
    border: 1px solid {ACCENT_SOFT};
    background: {FIELD};
}}
QRadioButton::indicator {{
    border-radius: 8px;
}}
QCheckBox::indicator:checked, QRadioButton::indicator:checked {{
    background: {ACCENT};
    border-color: {ACCENT};
}}
QSlider::groove:horizontal {{
    height: 6px;
    background: #1a1713;
    border: 1px solid {ACCENT_SOFT};
}}
QSlider::sub-page:horizontal {{
    background: {ACCENT};
}}
QSlider::handle:horizontal {{
    width: 16px;
    margin: -6px 0;
    background: {ACCENT};
    border: 1px solid {ACCENT};
}}
QFrame#BottomBar {{
    background-color: {SIDEBAR};
    border-top: 1px solid {ACCENT_LINE};
}}
QStatusBar {{
    background-color: {SIDEBAR};
    color: {MUTED};
    border-top: 1px solid {ACCENT_LINE};
}}
QScrollBar:vertical {{
    background: {SIDEBAR};
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
