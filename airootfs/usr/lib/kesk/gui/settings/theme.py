from __future__ import annotations

APP_TITLE = "KESK CONTROL CENTER"
APP_SUBTITLE = "SYSTEM TOOLS // DESKTOP STACK // MAINTENANCE CONSOLE"

BACKGROUND = "#050505"
PANEL = "#11100e"
PANEL_DARK = "#0b0a09"
ACCENT = "#ce6a35"
TEXT = "#d8d0c8"
MUTED = "#8f8a84"
WARNING = "#d69a4a"
DANGER = "#d65a4a"
SUCCESS = "#88aa66"


def stylesheet() -> str:
    return f"""
QWidget {{
    background-color: {BACKGROUND};
    color: {TEXT};
    font-family: "JetBrains Mono", "Monospace";
    font-size: 13px;
}}
QMainWindow {{
    background-color: {BACKGROUND};
}}
QFrame#Card {{
    background-color: {PANEL};
    border: 1px solid {ACCENT};
}}
QFrame#Sidebar {{
    background-color: {PANEL_DARK};
    border-right: 1px solid {ACCENT};
}}
QFrame#TopHeader {{
    background-color: {PANEL_DARK};
    border-bottom: 1px solid {ACCENT};
}}
QLabel#Title {{
    color: {ACCENT};
    font-size: 28px;
    font-weight: 700;
    font-family: "VT323", "JetBrains Mono", "Monospace";
    letter-spacing: 2px;
}}
QLabel#Subtitle {{
    color: {MUTED};
    font-size: 12px;
    font-weight: 600;
}}
QLabel#SectionHeading {{
    color: {ACCENT};
    font-size: 18px;
    font-weight: 700;
    font-family: "VT323", "JetBrains Mono", "Monospace";
    text-transform: uppercase;
}}
QLabel#CardTitle {{
    color: {ACCENT};
    font-size: 16px;
    font-weight: 700;
    font-family: "VT323", "JetBrains Mono", "Monospace";
}}
QLabel#CardBody {{
    color: {TEXT};
}}
QLabel#Muted {{
    color: {MUTED};
}}
QPushButton {{
    background-color: {PANEL};
    color: {TEXT};
    border: 1px solid {ACCENT};
    padding: 8px 12px;
    min-height: 16px;
    text-transform: uppercase;
}}
QPushButton:hover {{
    background-color: #191613;
}}
QPushButton:pressed {{
    background-color: #241b16;
}}
QPushButton:disabled {{
    color: {MUTED};
    border-color: #5a3f2b;
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
    background-color: #1a1410;
    border: 1px solid {ACCENT};
    color: {ACCENT};
}}
QTreeWidget, QTableWidget, QTextEdit, QPlainTextEdit, QListView, QComboBox, QLineEdit {{
    background-color: {PANEL};
    border: 1px solid {ACCENT};
    selection-background-color: #251912;
    selection-color: {TEXT};
}}
QHeaderView::section {{
    background-color: {PANEL_DARK};
    color: {ACCENT};
    border: 1px solid {ACCENT};
    padding: 4px;
}}
QTabWidget::pane {{
    border: 1px solid {ACCENT};
    background-color: {PANEL};
}}
QTabBar::tab {{
    background-color: {PANEL_DARK};
    color: {TEXT};
    border: 1px solid {ACCENT};
    padding: 6px 12px;
}}
QTabBar::tab:selected {{
    color: {ACCENT};
    background-color: #1a1410;
}}
QScrollBar:vertical {{
    background: {PANEL_DARK};
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
