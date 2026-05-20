from __future__ import annotations

from PySide6.QtGui import QColor, QFontDatabase
from PySide6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QSpinBox,
    QWidget,
)

from ..backends.common import support_level_for_status
from ..widgets import SupportBadge, SettingsSection, StatusLabel, action_bar, control_with_hint, populate_combo, select_combo_value, small_button
from .base import BasePage


class NotificationsPage(BasePage):
    page_key = "notifications"

    def __init__(self, controller) -> None:
        super().__init__(
            controller,
            "Notifications",
            "Change how KeskOS notifications appear, sound and behave. KeskOS uses Dunst as its runtime notification daemon.",
        )
        self.backend = controller.backend
        self._build_ui()
        self.load_state()

    def _build_ui(self) -> None:
        status = SettingsSection(
            "Backend status",
            "Control KeskOS desktop notifications powered by Dunst.",
        )
        self.support_badge = SupportBadge("Loading", "work")
        self.status_label = StatusLabel("Loading backend status", "work")
        self.runtime_label = QLabel()
        self.running_label = QLabel()
        self.config_path_label = QLabel()
        self.config_path_label.setWordWrap(True)
        self.per_app_rules_label = QLabel("KDE handoff")
        self.note_label = QLabel()
        self.note_label.setWordWrap(True)
        status.add_row("Support level", "Official support level for notification controls on this system.", self.support_badge, keywords="notifications support level native limited dunst")
        status.add_row("Runtime notifier", "The desktop notification daemon used by KeskOS.", self.runtime_label, keywords="runtime notifier dunst")
        status.add_row("Dunst running", "Whether the Dunst daemon is active in the current session.", self.running_label, keywords="dunst running status")
        status.add_row("Config path", "User-level Dunst configuration file used by Kesk Settings.", self.config_path_label, keywords="dunst config path dunstrc")
        status.add_row("Per-app rules", "Application-specific notification rules remain available through KDE's advanced notifications module.", self.per_app_rules_label, keywords="per app rules kde handoff notifications")
        status.add_row("Backend", "Current availability for Dunst notification control.", self.status_label, keywords="notifications backend status dunst")
        status.add_widget(self.note_label, keywords="dunst kde duplicate notifications note")
        self.add_section(status)

        behavior = SettingsSection(
            "Notification behavior",
            "Enable notifications, quiet mode, and screen placement for the Dunst runtime.",
        )
        self.enable_notifications = QCheckBox("Enable notifications")
        self.enable_notifications_hint = control_with_hint(self.enable_notifications)
        self.do_not_disturb = QCheckBox("Enable Do Not Disturb")
        self.do_not_disturb_hint = control_with_hint(self.do_not_disturb)
        self.position = QComboBox()
        populate_combo(
            self.position,
            [
                ("top-left", "Top left"),
                ("top-center", "Top center"),
                ("top-right", "Top right"),
                ("bottom-left", "Bottom left"),
                ("bottom-center", "Bottom center"),
                ("bottom-right", "Bottom right"),
            ],
        )
        self.width = QSpinBox()
        self.width.setRange(240, 600)
        self.height = QSpinBox()
        self.height.setRange(40, 300)
        self.show_icons = QCheckBox("Show icons")
        self.font = QComboBox()
        self.font.setEditable(True)
        self.font.addItems(sorted(f"{family} 10" for family in QFontDatabase().families()))

        behavior.add_row("Enable notifications", "Keep Dunst available in the user session and on login.", self.enable_notifications_hint, keywords="enable notifications dunst autostart")
        behavior.add_row("Do Not Disturb", "Pause popup delivery without changing the saved Dunst style.", self.do_not_disturb_hint, keywords="do not disturb dunstctl")
        behavior.add_row("Notification position", "Choose where notification popups appear on screen.", self.position, keywords="notification position top right bottom left")
        behavior.add_row("Notification width", "Maximum Dunst popup width in pixels.", self.width, keywords="notification width")
        behavior.add_row("Notification height", "Maximum Dunst popup height in pixels.", self.height, keywords="notification height")
        behavior.add_row("Notification icons", "Show icons beside notification text when an app provides one.", self.show_icons, keywords="notification icons")
        behavior.add_row("Notification font", "Font used by Dunst for popup titles and body text.", self.font, keywords="notification font jetbrains mono")
        self.add_section(behavior)

        style = SettingsSection(
            "Frame and surface style",
            "Match Dunst notifications to the black-and-orange KeskOS desktop style.",
        )
        self.transparency = QSpinBox()
        self.transparency.setRange(0, 30)
        self.corner_radius = QSpinBox()
        self.corner_radius.setRange(0, 12)
        self.frame_width = QSpinBox()
        self.frame_width.setRange(0, 4)
        self.frame_color_value, self.frame_color_button = self._color_control("Choose Frame Color", "#ce6a35")
        style.add_row("Transparency", "Lower values are more opaque. Higher values let more desktop background show through.", self.transparency, keywords="notification transparency")
        style.add_row("Corner radius", "KeskOS defaults to sharp corners. Increase only if you want rounded notifications.", self.corner_radius, keywords="notification corner radius")
        style.add_row("Frame width", "Border thickness around each notification popup.", self.frame_width, keywords="notification frame border size")
        style.add_row("Frame color", "Primary border color around Dunst notifications.", self._color_host(self.frame_color_value, self.frame_color_button), keywords="notification frame color border color orange")
        self.add_section(style)

        urgency = SettingsSection(
            "Urgency profiles",
            "Tune timeout and colors for low, normal, and critical notifications.",
        )
        self.low_timeout = QSpinBox()
        self.low_timeout.setRange(0, 20)
        self.normal_timeout = QSpinBox()
        self.normal_timeout.setRange(0, 20)
        self.critical_timeout = QSpinBox()
        self.critical_timeout.setRange(0, 20)

        self.low_background, self.low_background_button = self._color_control("Choose Low Background", "#050505")
        self.low_foreground, self.low_foreground_button = self._color_control("Choose Low Foreground", "#8f8a84")
        self.low_frame, self.low_frame_button = self._color_control("Choose Low Border", "#4c4845")
        self.normal_background, self.normal_background_button = self._color_control("Choose Normal Background", "#050505")
        self.normal_foreground, self.normal_foreground_button = self._color_control("Choose Normal Foreground", "#b8afa6")
        self.normal_frame, self.normal_frame_button = self._color_control("Choose Normal Border", "#ce6a35")
        self.critical_background, self.critical_background_button = self._color_control("Choose Critical Background", "#120806")
        self.critical_foreground, self.critical_foreground_button = self._color_control("Choose Critical Foreground", "#ce6a35")
        self.critical_frame, self.critical_frame_button = self._color_control("Choose Critical Border", "#ce6a35")

        urgency.add_row("Low urgency timeout", "Seconds to keep low-priority notifications visible.", self.low_timeout, keywords="low urgency timeout")
        urgency.add_row("Low urgency colors", "Background, text, and border for low-priority notifications.", self._triple_color_host(self.low_background, self.low_background_button, self.low_foreground, self.low_foreground_button, self.low_frame, self.low_frame_button), keywords="low urgency notification colors background foreground frame")
        urgency.add_row("Normal timeout", "Seconds to keep standard notifications visible.", self.normal_timeout, keywords="normal urgency timeout")
        urgency.add_row("Normal colors", "Background, text, and border for standard notifications.", self._triple_color_host(self.normal_background, self.normal_background_button, self.normal_foreground, self.normal_foreground_button, self.normal_frame, self.normal_frame_button), keywords="normal urgency notification colors background foreground frame")
        urgency.add_row("Critical timeout", "Seconds to keep critical alerts visible. Use 0 to keep them until dismissed.", self.critical_timeout, keywords="critical urgency timeout")
        urgency.add_row("Critical colors", "Background, text, and border for critical alerts.", self._triple_color_host(self.critical_background, self.critical_background_button, self.critical_foreground, self.critical_foreground_button, self.critical_frame, self.critical_frame_button), keywords="critical urgency notification colors background foreground frame")
        self.add_section(urgency)

        actions = SettingsSection(
            "Notification actions",
            "Apply the branded preset, send test notifications, reload Dunst, or hand off to KDE's advanced module when needed.",
        )
        self.apply_preset_button = small_button("Apply KeskOS Notification Style", primary=True)
        self.apply_preset_hint = control_with_hint(self.apply_preset_button)
        self.apply_preset_button.clicked.connect(self.apply_kesk_preset)
        self.test_button = small_button("Send Test Notification")
        self.test_button.clicked.connect(self.send_test_notification)
        self.critical_test_button = small_button("Send Critical Test")
        self.critical_test_button.clicked.connect(self.send_critical_notification)
        self.test_actions_hint = control_with_hint(action_bar(self.test_button, self.critical_test_button))
        self.open_config_button = small_button("Open Dunst Config")
        self.open_config_button.clicked.connect(self.open_config)
        self.reload_button = small_button("Reload Notification Daemon")
        self.reload_button.clicked.connect(self.reload_dunst)
        self.reload_hint = control_with_hint(self.reload_button)
        self.advanced_button = small_button("Open Advanced KDE Notification Settings")
        self.advanced_button.clicked.connect(lambda: self.controller.open_kcm("kcm_notifications"))
        actions.add_row(
            "Dunst preset",
            "Apply the branded KeskOS notification style to the Dunst runtime config.",
            self.apply_preset_hint,
            keywords="apply keskos notification style dunst preset",
        )
        actions.add_row(
            "Test notifications",
            "Send a normal or critical test notification through notify-send.",
            self.test_actions_hint,
            keywords="send test notification notify send",
        )
        actions.add_row(
            "Reload daemon",
            "Reload the runtime notification daemon after changing the Dunst config.",
            self.reload_hint,
            keywords="reload notification daemon dunstctl",
        )
        actions.add_row(
            "Config and advanced settings",
            "Open the Dunst config file directly or use KDE's notification module for app-specific rules.",
            action_bar(self.open_config_button, self.advanced_button),
            keywords="open dunst config kde notifications advanced",
        )
        self.add_section(actions)

    def _color_control(self, title: str, default: str) -> tuple[QLineEdit, QWidget]:
        field = QLineEdit(default)
        field.setMinimumWidth(96)
        button = small_button("Color")
        button.clicked.connect(lambda: self.choose_color(field, title))
        self._set_color_field(field, default)
        return field, button

    def _color_host(self, field: QLineEdit, button: QWidget) -> QWidget:
        host = QWidget()
        layout = QHBoxLayout(host)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addWidget(field)
        layout.addWidget(button)
        return host

    def _triple_color_host(
        self,
        first_field: QLineEdit,
        first_button: QWidget,
        second_field: QLineEdit,
        second_button: QWidget,
        third_field: QLineEdit,
        third_button: QWidget,
    ) -> QWidget:
        host = QWidget()
        layout = QHBoxLayout(host)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        layout.addWidget(self._color_host(first_field, first_button))
        layout.addWidget(self._color_host(second_field, second_button))
        layout.addWidget(self._color_host(third_field, third_button))
        return host

    def _set_color_field(self, field: QLineEdit, value: str) -> None:
        color = QColor(value)
        if not color.isValid():
            color = QColor("#ce6a35")
        text_color = "#111111" if color.lightness() > 140 else "#f4efe8"
        field.setText(color.name())
        field.setStyleSheet(f"background-color: {color.name()}; color: {text_color}; border: 1px solid #ce6a35;")

    def choose_color(self, field: QLineEdit, title: str) -> None:
        color = QColorDialog.getColor(QColor(field.text() or "#ce6a35"), self, title)
        if color.isValid():
            self._set_color_field(field, color.name())

    def _set_control_enabled(self, enabled: bool, reason: str = "") -> None:
        widgets = (
            self.position,
            self.width,
            self.height,
            self.show_icons,
            self.font,
            self.transparency,
            self.corner_radius,
            self.frame_width,
            self.frame_color_value,
            self.frame_color_button,
            self.low_timeout,
            self.normal_timeout,
            self.critical_timeout,
            self.low_background,
            self.low_background_button,
            self.low_foreground,
            self.low_foreground_button,
            self.low_frame,
            self.low_frame_button,
            self.normal_background,
            self.normal_background_button,
            self.normal_foreground,
            self.normal_foreground_button,
            self.normal_frame,
            self.normal_frame_button,
            self.critical_background,
            self.critical_background_button,
            self.critical_foreground,
            self.critical_foreground_button,
            self.critical_frame,
            self.critical_frame_button,
            self.apply_preset_button,
        )
        for widget in widgets:
            widget.setEnabled(enabled)
            widget.setToolTip("" if enabled else reason)

    def load_state(self) -> None:
        self.begin_refresh()
        state = self.backend.notifications_state()
        status = state["status"]
        self.support_badge.set_support(support_level_for_status(status))
        self.status_label.set_status(str(state["backend_label"]), status.ui_kind)
        self.runtime_label.setText(str(state["runtime_notifier"]))
        self.running_label.setText("yes" if state["dunst_running"] else "no")
        self.config_path_label.setText(str(state["config_path"]))
        self.per_app_rules_label.setText("KDE Handoff")
        note_parts = [
            "KeskOS uses Dunst as the primary runtime notification daemon. Per-app notification rules remain available through KDE notification settings.",
        ]
        note_parts.extend(str(item) for item in state.get("status_notes", []) if item)
        self.note_label.setText("\n\n".join(dict.fromkeys(note_parts)))

        self.enable_notifications.setChecked(bool(state["enable_notifications"]))
        self.do_not_disturb.setChecked(bool(state["do_not_disturb"]))
        select_combo_value(self.position, str(state["position"]))
        self.width.setValue(int(state["width"]))
        self.height.setValue(int(state["height"]))
        self.show_icons.setChecked(bool(state["show_icons"]))
        index = self.font.findText(str(state["font"]))
        if index >= 0:
            self.font.setCurrentIndex(index)
        else:
            self.font.setEditText(str(state["font"]))
        self.transparency.setValue(int(state["transparency"]))
        self.corner_radius.setValue(int(state["corner_radius"]))
        self.frame_width.setValue(int(state["frame_width"]))
        self._set_color_field(self.frame_color_value, str(state["frame_color"]))

        self.low_timeout.setValue(int(state["low_timeout"]))
        self.normal_timeout.setValue(int(state["normal_timeout"]))
        self.critical_timeout.setValue(int(state["critical_timeout"]))
        self._set_color_field(self.low_background, str(state["low_background"]))
        self._set_color_field(self.low_foreground, str(state["low_foreground"]))
        self._set_color_field(self.low_frame, str(state["low_frame_color"]))
        self._set_color_field(self.normal_background, str(state["normal_background"]))
        self._set_color_field(self.normal_foreground, str(state["normal_foreground"]))
        self._set_color_field(self.normal_frame, str(state["normal_frame_color"]))
        self._set_color_field(self.critical_background, str(state["critical_background"]))
        self._set_color_field(self.critical_foreground, str(state["critical_foreground"]))
        self._set_color_field(self.critical_frame, str(state["critical_frame_color"]))

        config_editable = bool(state["config_editable"])
        config_reason = "" if config_editable else f"Dunst config is not writable at {state['config_path']}."
        self._set_control_enabled(config_editable, config_reason)
        self.enable_notifications_hint.set_enabled(bool(state["dunst_available"]), str(state["enable_reason"]))
        dnd_reason = str(state["dnd_reason"])
        if bool(state["dnd_supported"]) and not bool(state["enable_notifications"]):
            dnd_reason = "Enable notifications to use live Do Not Disturb."
        self.do_not_disturb_hint.set_enabled(bool(state["dnd_supported"] and state["enable_notifications"]), dnd_reason)
        self.test_actions_hint.set_enabled(bool(state["test_supported"]), str(state["test_reason"]))
        self.reload_hint.set_enabled(bool(state["reload_supported"]), str(state["reload_reason"]))
        self.open_config_button.setEnabled(bool(state["open_config_supported"]))
        kcm_available = bool(self.backend.tools.get("kcmshell6") or self.backend.tools.get("systemsettings"))
        self.advanced_button.setEnabled(kcm_available)
        self.advanced_button.setToolTip("" if kcm_available else "kcmshell6 or systemsettings is required to open KDE notification settings.")
        self.apply_preset_hint.set_reason(config_reason)

        if not state["dnd_supported"]:
            self.do_not_disturb.setToolTip("Live Do Not Disturb control requires dunstctl and a running Dunst session.")
        else:
            self.do_not_disturb.setToolTip("")
        if not state["test_supported"]:
            self.test_button.setToolTip("notify-send is not installed.")
            self.critical_test_button.setToolTip("notify-send is not installed.")
        else:
            self.test_button.setToolTip("")
            self.critical_test_button.setToolTip("")

        self.finish_refresh()

    def values(self) -> dict[str, object]:
        return {
            "enable_notifications": self.enable_notifications.isChecked(),
            "do_not_disturb": self.do_not_disturb.isChecked(),
            "position": self.position.currentData(),
            "width": self.width.value(),
            "height": self.height.value(),
            "show_icons": self.show_icons.isChecked(),
            "font": self.font.currentText().strip() or "JetBrains Mono 10",
            "transparency": self.transparency.value(),
            "corner_radius": self.corner_radius.value(),
            "frame_width": self.frame_width.value(),
            "frame_color": self.frame_color_value.text().strip(),
            "low_timeout": self.low_timeout.value(),
            "normal_timeout": self.normal_timeout.value(),
            "critical_timeout": self.critical_timeout.value(),
            "low_background": self.low_background.text().strip(),
            "low_foreground": self.low_foreground.text().strip(),
            "low_frame_color": self.low_frame.text().strip(),
            "normal_background": self.normal_background.text().strip(),
            "normal_foreground": self.normal_foreground.text().strip(),
            "normal_frame_color": self.normal_frame.text().strip(),
            "critical_background": self.critical_background.text().strip(),
            "critical_foreground": self.critical_foreground.text().strip(),
            "critical_frame_color": self.critical_frame.text().strip(),
        }

    def apply_changes(self) -> None:
        result = self.backend.apply_notifications(self.values())
        self.show_result(result, "Notifications")
        self.load_state()

    def apply_kesk_preset(self) -> None:
        result = self.backend.apply_notifications_preset()
        self.show_result(result, "Notifications")
        self.load_state()

    def send_test_notification(self) -> None:
        result = self.backend.test_notification()
        self.show_result(result, "Notifications")

    def send_critical_notification(self) -> None:
        result = self.backend.test_notification(critical=True)
        self.show_result(result, "Notifications")

    def open_config(self) -> None:
        result = self.backend.open_notifications_config()
        self.show_result(result, "Notifications")

    def reload_dunst(self) -> None:
        result = self.backend.reload_notifications()
        self.show_result(result, "Notifications")
        self.load_state()

    def on_activated(self) -> None:
        self.load_state()
