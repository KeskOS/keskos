from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFontDatabase, QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSlider,
    QWidget,
)

from ..widgets import SettingsSection, action_bar, populate_combo, select_combo_value, small_button
from .base import BasePage


class AppearancePage(BasePage):
    page_key = "appearance"

    def __init__(self, controller) -> None:
        super().__init__(controller, "Appearance", "Manage the Plasma theme stack and the KeskOS visual layer from one place.")
        self.backend = controller.backend
        self._build_ui()
        self.load_state()

    def _build_ui(self) -> None:
        theme_section = SettingsSection("Theme stack", "These controls write to KDE user config and use Plasma theme tools when available.")
        self.look_and_feel = QComboBox()
        self.plasma_theme = QComboBox()
        self.color_scheme = QComboBox()
        self.icon_theme = QComboBox()
        self.cursor_theme = QComboBox()
        self.font_family = QComboBox()
        self.font_family.setEditable(True)

        fonts = sorted(QFontDatabase().families())
        self.font_family.addItems(fonts)

        theme_section.add_row("Global theme", "Apply a Plasma look-and-feel package.", self.look_and_feel, keywords="theme look and feel kde plasma")
        theme_section.add_row("Plasma style", "Choose the active desktop theme for panels and shells.", self.plasma_theme, keywords="plasma style desktop theme panels")
        theme_section.add_row("Color scheme", "Switch the active color scheme.", self.color_scheme, keywords="color scheme accent palette")
        theme_section.add_row("Icon theme", "Set the icon pack used by KDE applications.", self.icon_theme, keywords="icons")
        theme_section.add_row("Cursor theme", "Set the system pointer theme.", self.cursor_theme, keywords="cursor pointer mouse")
        theme_section.add_row("Font", "Set the primary UI font for KDE user settings.", self.font_family, keywords="font text ui")
        self.add_section(theme_section)

        accent_section = SettingsSection("KeskOS effects", "KeskOS-specific presentation controls are stored in ~/.config/kesk/settings.json.")
        self.accent_value = QLabel()
        self.accent_value.setMinimumWidth(96)
        self.accent_value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.accent_button = small_button("Choose Accent")
        self.accent_button.clicked.connect(self.choose_accent)
        accent_control = QWidget()
        accent_layout = QHBoxLayout(accent_control)
        accent_layout.setContentsMargins(0, 0, 0, 0)
        accent_layout.setSpacing(8)
        accent_layout.addWidget(self.accent_value)
        accent_layout.addWidget(self.accent_button)

        self.decoration = QComboBox()
        self.crt_effects = QCheckBox("Enabled")
        self.scanlines = QCheckBox("Enabled")
        self.glow = QSlider(Qt.Orientation.Horizontal)
        self.glow.setRange(0, 100)

        accent_section.add_row("Accent color", "Primary KeskOS accent used by supported assets and settings.", accent_control, keywords="accent orange color glow")
        accent_section.add_row("Window decoration", "Choose the active KWin decoration theme.", self.decoration, keywords="window decoration titlebar borders")
        accent_section.add_row("CRT effects", "Store the main CRT overlay preference for KeskOS components.", self.crt_effects, keywords="crt retro terminal")
        accent_section.add_row("Scanlines", "Store the scanline overlay preference for compatible components.", self.scanlines, keywords="scanlines overlay")
        accent_section.add_row("Glow intensity", "Tune the orange glow level for KeskOS surfaces.", self.glow, keywords="glow intensity orange")
        self.add_section(accent_section)

        wallpaper_section = SettingsSection("Wallpaper", "Pick a wallpaper file and apply it through Plasma if the wallpaper helper is available.")
        self.wallpaper_preview = QLabel("NO PREVIEW")
        self.wallpaper_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.wallpaper_preview.setFixedSize(240, 136)
        self.wallpaper_preview.setStyleSheet("border: 1px solid #ce6a35; background-color: #11100e; color: #9d968f;")
        self.wallpaper_path = QLineEdit()
        self.wallpaper_button = small_button("Choose File")
        self.wallpaper_button.clicked.connect(self.choose_wallpaper)
        path_control = QWidget()
        path_layout = QHBoxLayout(path_control)
        path_layout.setContentsMargins(0, 0, 0, 0)
        path_layout.setSpacing(8)
        path_layout.addWidget(self.wallpaper_path, 1)
        path_layout.addWidget(self.wallpaper_button)
        wallpaper_section.add_widget(self.wallpaper_preview, keywords="wallpaper background preview")
        wallpaper_section.add_row("Wallpaper file", "Absolute file path for the desktop background.", path_control, keywords="wallpaper background image")
        self.add_section(wallpaper_section)

        self.apply_button = small_button("Apply", primary=True)
        self.apply_button.clicked.connect(self.apply_changes)
        self.revert_button = small_button("Revert")
        self.revert_button.clicked.connect(self.load_state)
        self.kesk_defaults_button = small_button("Apply KeskOS Default")
        self.kesk_defaults_button.clicked.connect(self.apply_kesk_defaults)
        self.kde_defaults_button = small_button("Reset To KDE Default")
        self.kde_defaults_button.clicked.connect(self.apply_kde_defaults)
        self.restore_backup_button = small_button("Restore Appearance Backup")
        self.restore_backup_button.clicked.connect(self.restore_backup)
        actions = action_bar(
            self.apply_button,
            self.revert_button,
            self.kesk_defaults_button,
            self.kde_defaults_button,
            self.restore_backup_button,
        )
        action_section = SettingsSection("Apply changes")
        action_section.add_widget(actions, keywords="apply revert restore reset defaults")
        self.add_section(action_section)

    def _set_accent_chip(self, value: str) -> None:
        color = QColor(value)
        if not color.isValid():
            color = QColor("#ce6a35")
        text_color = "#111111" if color.lightness() > 140 else "#f4efe8"
        self.accent_value.setText(color.name().upper())
        self.accent_value.setStyleSheet(f"background-color: {color.name()}; color: {text_color}; border: 1px solid #ce6a35; padding: 6px;")

    def _set_wallpaper_preview(self, value: str) -> None:
        self.wallpaper_preview.setPixmap(QPixmap())
        self.wallpaper_preview.setText("NO PREVIEW")
        path = value.strip()
        if not path:
            return
        pixmap = QPixmap(path)
        if pixmap.isNull():
            self.wallpaper_preview.setText("PREVIEW UNAVAILABLE")
            return
        self.wallpaper_preview.setPixmap(
            pixmap.scaled(
                self.wallpaper_preview.size(),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
        )

    def reload_options(self) -> None:
        populate_combo(self.look_and_feel, self.backend.look_and_feel_options())
        populate_combo(self.plasma_theme, self.backend.plasma_theme_options())
        populate_combo(self.color_scheme, self.backend.color_scheme_options())
        populate_combo(self.icon_theme, self.backend.icon_theme_options())
        populate_combo(self.cursor_theme, self.backend.cursor_theme_options())
        populate_combo(self.decoration, self.backend.window_decoration_options())

    def load_state(self) -> None:
        self.reload_options()
        state = self.backend.appearance_state()
        select_combo_value(self.look_and_feel, state["look_and_feel"])
        select_combo_value(self.plasma_theme, state["plasma_theme"])
        select_combo_value(self.color_scheme, state["color_scheme"])
        select_combo_value(self.icon_theme, state["icon_theme"])
        select_combo_value(self.cursor_theme, state["cursor_theme"])
        select_combo_value(self.decoration, state["window_decoration"])
        index = self.font_family.findText(state["font_family"])
        if index >= 0:
            self.font_family.setCurrentIndex(index)
        else:
            self.font_family.setEditText(state["font_family"])
        self._set_accent_chip(state["accent_color"])
        self.wallpaper_path.setText(state["wallpaper_path"])
        self._set_wallpaper_preview(state["wallpaper_path"])
        self.crt_effects.setChecked(bool(state["crt_effects"]))
        self.scanlines.setChecked(bool(state["scanlines"]))
        self.glow.setValue(int(state["glow_intensity"]))

    def choose_accent(self) -> None:
        color = QColorDialog.getColor(QColor(self.accent_value.text() or "#ce6a35"), self, "Choose KeskOS Accent")
        if color.isValid():
            self._set_accent_chip(color.name())

    def choose_wallpaper(self) -> None:
        path, _selected_filter = QFileDialog.getOpenFileName(
            self,
            "Choose Wallpaper",
            self.wallpaper_path.text() or str(self.controller.backend.paths.home / "Pictures"),
            "Images (*.png *.jpg *.jpeg *.webp *.bmp *.svg)",
        )
        if path:
            self.wallpaper_path.setText(path)
            self._set_wallpaper_preview(path)

    def values(self) -> dict[str, object]:
        return {
            "look_and_feel": self.look_and_feel.currentData(),
            "plasma_theme": self.plasma_theme.currentData(),
            "color_scheme": self.color_scheme.currentData(),
            "icon_theme": self.icon_theme.currentData(),
            "cursor_theme": self.cursor_theme.currentData(),
            "font_family": self.font_family.currentText().strip(),
            "accent_color": self.accent_value.text().strip(),
            "window_decoration": self.decoration.currentData(),
            "wallpaper_path": self.wallpaper_path.text().strip(),
            "crt_effects": self.crt_effects.isChecked(),
            "scanlines": self.scanlines.isChecked(),
            "glow_intensity": self.glow.value(),
        }

    def apply_changes(self) -> None:
        result = self.backend.apply_appearance(self.values())
        self.show_result(result, "Appearance")
        self.load_state()

    def apply_kesk_defaults(self) -> None:
        result = self.backend.apply_kesk_appearance_defaults()
        self.show_result(result, "Appearance")
        self.load_state()

    def apply_kde_defaults(self) -> None:
        result = self.backend.apply_kde_appearance_defaults()
        self.show_result(result, "Appearance")
        self.load_state()

    def restore_backup(self) -> None:
        result = self.backend.restore_latest_backup("appearance")
        self.show_result(result, "Appearance Backup")
        self.load_state()

    def on_activated(self) -> None:
        self.load_state()
