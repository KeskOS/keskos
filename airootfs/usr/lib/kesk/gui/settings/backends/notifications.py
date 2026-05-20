from __future__ import annotations

import configparser
from datetime import datetime
import os
from pathlib import Path
import re
import shutil
import subprocess
from typing import Any

from .common import BackendStatus, connected, limited, missing, result_payload


POSITION_OPTIONS: tuple[tuple[str, str], ...] = (
    ("top-left", "Top left"),
    ("top-center", "Top center"),
    ("top-right", "Top right"),
    ("bottom-left", "Bottom left"),
    ("bottom-center", "Bottom center"),
    ("bottom-right", "Bottom right"),
)

PLASMA_NOTIFICATION_WARNING = "Duplicate notifications may happen if Plasma notifications are also active."
DUPLICATE_RISK_WARNING = (
    "Dunst is active, but Plasma notification integration may also be active. If you see duplicate notifications, open KDE notification settings and disable conflicting notification behavior."
)

KDESK_PRESET: dict[str, Any] = {
    "position": "top-right",
    "offset": "12x42",
    "width": 360,
    "height": 120,
    "show_icons": True,
    "font": "JetBrains Mono 10",
    "transparency": 0,
    "corner_radius": 0,
    "frame_width": 1,
    "frame_color": "#ce6a35",
    "low_timeout": 4,
    "normal_timeout": 6,
    "critical_timeout": 0,
    "low_background": "#050505",
    "low_foreground": "#8f8a84",
    "low_frame_color": "#4c4845",
    "normal_background": "#050505",
    "normal_foreground": "#b8afa6",
    "normal_frame_color": "#ce6a35",
    "critical_background": "#120806",
    "critical_foreground": "#ce6a35",
    "critical_frame_color": "#ce6a35",
}

DEFAULT_DUNSTRC = """[global]
    monitor = 0
    follow = none
    indicate_hidden = yes
    shrink = no
    separator_height = 1
    padding = 12
    horizontal_padding = 12
    frame_width = 1
    frame_color = "#ce6a35"
    separator_color = "#ce6a35"
    sort = yes
    idle_threshold = 120
    font = JetBrains Mono 10
    line_height = 0
    markup = full
    format = "<b>%s</b>\\n%b"
    alignment = left
    vertical_alignment = center
    word_wrap = yes
    ellipsize = middle
    stack_duplicates = yes
    hide_duplicate_count = no
    show_indicators = yes
    icon_position = left
    max_icon_size = 32
    origin = top-right
    offset = 12x42
    width = 360
    height = 120
    transparency = 0
    corner_radius = 0

[urgency_low]
    background = "#050505"
    foreground = "#8f8a84"
    frame_color = "#4c4845"
    timeout = 4

[urgency_normal]
    background = "#050505"
    foreground = "#b8afa6"
    frame_color = "#ce6a35"
    timeout = 6

[urgency_critical]
    background = "#120806"
    foreground = "#ce6a35"
    frame_color = "#ce6a35"
    timeout = 0
"""

AUTOSTART_TEMPLATE = """[Desktop Entry]
Type=Application
Name=Dunst Notification Daemon
Comment=Notification daemon
Exec=dunst
X-GNOME-Autostart-enabled={enabled}
NoDisplay=true
Hidden={hidden}
OnlyShowIn=KDE;Plasma;
X-KDE-autostart-phase=1
X-KDE-autostart-after=panel
"""

SECTION_WRITES: dict[str, dict[str, Any]] = {
    "global": {
        "origin": ("position", str),
        "offset": ("offset", str),
        "width": ("width", int),
        "height": ("height", int),
        "icon_position": ("show_icons", lambda value: "left" if value else "off"),
        "font": ("font", str),
        "transparency": ("transparency", int),
        "corner_radius": ("corner_radius", int),
        "frame_width": ("frame_width", int),
        "frame_color": ("frame_color", str),
    },
    "urgency_low": {
        "background": ("low_background", str),
        "foreground": ("low_foreground", str),
        "frame_color": ("low_frame_color", str),
        "timeout": ("low_timeout", int),
    },
    "urgency_normal": {
        "background": ("normal_background", str),
        "foreground": ("normal_foreground", str),
        "frame_color": ("normal_frame_color", str),
        "timeout": ("normal_timeout", int),
    },
    "urgency_critical": {
        "background": ("critical_background", str),
        "foreground": ("critical_foreground", str),
        "frame_color": ("critical_frame_color", str),
        "timeout": ("critical_timeout", int),
    },
}

SECTION_REMOVE_KEYS: dict[str, set[str]] = {
    "global": {"geometry"},
}

SECTION_HEADER = re.compile(r"^\s*\[(?P<section>[^\]]+)\]\s*$")
KEY_LINE = re.compile(r"^(?P<indent>\s*)(?P<key>[A-Za-z0-9_.-]+)\s*=\s*(?P<value>.*?)(?P<newline>\n?)$")
GEOMETRY = re.compile(r"^\s*\"?(?P<width>\d+)x(?P<height>\d+)(?P<xsign>[+-])(?P<x>\d+)(?P<ysign>[+-])(?P<y>\d+)\"?\s*$")


def _tool(backend, name: str) -> str | None:
    value = backend.tools.get(name)
    return value if value else None


def _repo_root(backend) -> Path | None:
    try:
        return backend.paths.root.parents[3]
    except IndexError:
        return None


def _config_path(backend) -> Path:
    return backend.paths.home / ".config" / "dunst" / "dunstrc"


def _system_config_candidates(backend) -> list[Path]:
    candidates = [Path("/etc/dunst/dunstrc"), backend.paths.staged_root / "etc" / "dunst" / "dunstrc"]
    repo_root = _repo_root(backend)
    if repo_root is not None:
        candidates.append(repo_root / "configs" / "dunst" / "dunstrc")
    return [candidate for candidate in candidates if candidate]


def _autostart_path(backend) -> Path:
    return backend.paths.home / ".config" / "autostart" / "dunst.desktop"


def _system_autostart_candidates(backend) -> list[Path]:
    return [
        Path("/etc/xdg/autostart/dunst.desktop"),
        backend.paths.staged_root / "etc" / "xdg" / "autostart" / "dunst.desktop",
    ]


def _normalise_color(value: str, fallback: str) -> str:
    stripped = value.strip().strip('"').strip("'")
    if re.fullmatch(r"#[0-9A-Fa-f]{6}", stripped):
        return stripped.lower()
    return fallback.lower()


def _normalise_position(value: str) -> str:
    lowered = value.strip().lower()
    options = {item[0] for item in POSITION_OPTIONS}
    return lowered if lowered in options else "top-right"


def _normalise_int(value: Any, fallback: int, *, minimum: int | None = None, maximum: int | None = None) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = fallback
    if minimum is not None:
        number = max(minimum, number)
    if maximum is not None:
        number = min(maximum, number)
    return number


def _config_writable(path: Path) -> bool:
    if path.exists():
        return os.access(path, os.W_OK)
    if path.parent.exists():
        return os.access(path.parent, os.W_OK)
    if path.parent.parent.exists():
        return os.access(path.parent.parent, os.W_OK)
    return False


def _read_file(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _parse(text: str) -> configparser.ConfigParser:
    parser = configparser.ConfigParser(interpolation=None, strict=False)
    parser.optionxform = str
    if text.strip():
        try:
            parser.read_string(text)
        except configparser.Error:
            pass
    return parser


def _geometry_values(raw_value: str) -> dict[str, Any]:
    match = GEOMETRY.match(raw_value)
    if match is None:
        return {"position": "top-right", "offset": KDESK_PRESET["offset"], "width": KDESK_PRESET["width"], "height": KDESK_PRESET["height"]}
    xsign = match.group("xsign")
    ysign = match.group("ysign")
    if xsign == "+" and ysign == "+":
        position = "top-left"
    elif xsign == "-" and ysign == "+":
        position = "top-right"
    elif xsign == "+" and ysign == "-":
        position = "bottom-left"
    else:
        position = "bottom-right"
    return {
        "position": position,
        "offset": f"{match.group('x')}x{match.group('y')}",
        "width": int(match.group("width")),
        "height": int(match.group("height")),
    }


def _read_section_value(parser: configparser.ConfigParser, section: str, key: str, fallback: str) -> str:
    return parser.get(section, key, fallback=fallback).strip()


def _read_enable_notifications(backend) -> bool:
    user_file = _autostart_path(backend)
    if user_file.is_file():
        parser = _parse(_read_file(user_file))
        enabled = parser.get("Desktop Entry", "X-GNOME-Autostart-enabled", fallback="true").strip().lower()
        hidden = parser.get("Desktop Entry", "Hidden", fallback="false").strip().lower()
        return enabled not in {"false", "0", "no"} and hidden not in {"true", "1", "yes"}
    return any(candidate.is_file() for candidate in _system_autostart_candidates(backend))


def _write_autostart(backend, enabled: bool) -> Path:
    path = _autostart_path(backend)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        AUTOSTART_TEMPLATE.format(
            enabled="true" if enabled else "false",
            hidden="false" if enabled else "true",
        ),
        encoding="utf-8",
    )
    backend.logger.log(f"dunst_autostart={path}")
    return path


def _spawn_dunst(backend) -> bool:
    dunst = _tool(backend, "dunst")
    if not dunst:
        return False
    try:
        subprocess.Popen(
            [dunst],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
        )
    except OSError as exc:
        backend.logger.log(f"dunst_spawn_failed={exc!r}")
        return False
    return True


def is_available(backend) -> bool:
    return bool(_tool(backend, "dunst") or _config_path(backend).exists())


def is_running(backend) -> bool:
    pgrep = _tool(backend, "pgrep") or shutil.which("pgrep")
    if pgrep:
        result = backend._run([pgrep, "-x", "dunst"], capture=True, timeout=5)
        if result is not None:
            return result.returncode == 0
    dunstctl = _tool(backend, "dunstctl")
    if dunstctl:
        result = backend._run([dunstctl, "is-paused"], capture=True, timeout=5)
        if result is not None and result.returncode == 0:
            return True
    return False


def _process_running(backend, name: str) -> bool:
    pgrep = _tool(backend, "pgrep") or shutil.which("pgrep")
    if not pgrep:
        return False
    result = backend._run([pgrep, "-x", name], capture=True, timeout=5)
    return result is not None and result.returncode == 0


def _qdbus_service_names(backend) -> set[str]:
    qdbus = _tool(backend, "qdbus6")
    if not qdbus:
        return set()

    commands = (
        [qdbus],
        [qdbus, "org.freedesktop.DBus", "/org/freedesktop/DBus", "org.freedesktop.DBus.ListNames"],
    )
    for command in commands:
        result = backend._run(command, capture=True, timeout=8)
        if result is None or result.returncode != 0:
            continue
        names: set[str] = set()
        for line in result.stdout.splitlines():
            stripped = line.strip().strip('"').strip("'")
            if stripped.startswith("org.") or stripped.startswith(":"):
                names.add(stripped)
        if names:
            return names
    return set()


def _plasma_notification_state(backend) -> dict[str, Any]:
    dbus_names = _qdbus_service_names(backend)
    config_candidates = (
        backend.paths.home / ".config" / "plasmanotifyrc",
        backend.paths.home / ".config" / "knotifications5rc",
        backend.paths.home / ".config" / "knotifications6rc",
    )
    config_matches = [str(path) for path in config_candidates if path.exists()]
    plasmashell_running = _process_running(backend, "plasmashell")
    plasmashell_dbus = "org.kde.plasmashell" in dbus_names
    plasma_notification_active = plasmashell_running or plasmashell_dbus
    return {
        "plasmashell_running": plasmashell_running,
        "plasmashell_dbus": plasmashell_dbus,
        "notification_config_present": bool(config_matches),
        "notification_config_paths": config_matches,
        "plasma_notification_active": plasma_notification_active,
    }


def get_config_path(backend) -> Path:
    return _config_path(backend)


def ensure_user_config(backend) -> Path:
    path = _config_path(backend)
    if path.is_file():
        return path

    path.parent.mkdir(parents=True, exist_ok=True)
    for candidate in _system_config_candidates(backend):
        if candidate.is_file():
            shutil.copy2(candidate, path)
            backend.logger.log(f"dunst_config_seed={candidate}")
            return path

    path.write_text(DEFAULT_DUNSTRC, encoding="utf-8")
    backend.logger.log("dunst_config_seed=generated-default")
    return path


def _backup_path(backend, stem: str) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return backend.paths.backups_dir / f"{stem}.{timestamp}.bak"


def backup_config(backend) -> Path | None:
    config_path = ensure_user_config(backend)
    backup_path = _backup_path(backend, "dunstrc")
    backup_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        shutil.copy2(config_path, backup_path)
    except OSError as exc:
        backend.logger.log(f"dunst_backup_failed={exc!r}")
        return None
    backend.logger.log(f"dunst_backup={backup_path}")
    return backup_path


def _backup_autostart(backend) -> Path | None:
    autostart = _autostart_path(backend)
    if not autostart.exists():
        return None
    backup_path = _backup_path(backend, "dunst.desktop")
    backup_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        shutil.copy2(autostart, backup_path)
    except OSError as exc:
        backend.logger.log(f"dunst_autostart_backup_failed={exc!r}")
        return None
    backend.logger.log(f"dunst_autostart_backup={backup_path}")
    return backup_path


def _settings_from_parser(parser: configparser.ConfigParser) -> dict[str, Any]:
    geometry = _geometry_values(_read_section_value(parser, "global", "geometry", ""))
    position = _normalise_position(_read_section_value(parser, "global", "origin", geometry["position"]))
    offset = _read_section_value(parser, "global", "offset", geometry["offset"]) or KDESK_PRESET["offset"]
    font = _read_section_value(parser, "global", "font", KDESK_PRESET["font"]) or KDESK_PRESET["font"]
    icon_position = _read_section_value(parser, "global", "icon_position", "left").lower()
    return {
        "position": position,
        "offset": offset,
        "width": _normalise_int(_read_section_value(parser, "global", "width", str(geometry["width"])), KDESK_PRESET["width"], minimum=240, maximum=600),
        "height": _normalise_int(_read_section_value(parser, "global", "height", str(geometry["height"])), KDESK_PRESET["height"], minimum=40, maximum=300),
        "show_icons": icon_position not in {"off", "none", "false"},
        "font": font,
        "transparency": _normalise_int(_read_section_value(parser, "global", "transparency", str(KDESK_PRESET["transparency"])), KDESK_PRESET["transparency"], minimum=0, maximum=30),
        "corner_radius": _normalise_int(_read_section_value(parser, "global", "corner_radius", str(KDESK_PRESET["corner_radius"])), KDESK_PRESET["corner_radius"], minimum=0, maximum=12),
        "frame_width": _normalise_int(_read_section_value(parser, "global", "frame_width", str(KDESK_PRESET["frame_width"])), KDESK_PRESET["frame_width"], minimum=0, maximum=4),
        "frame_color": _normalise_color(_read_section_value(parser, "global", "frame_color", KDESK_PRESET["frame_color"]), KDESK_PRESET["frame_color"]),
        "low_timeout": _normalise_int(_read_section_value(parser, "urgency_low", "timeout", str(KDESK_PRESET["low_timeout"])), KDESK_PRESET["low_timeout"], minimum=0, maximum=20),
        "normal_timeout": _normalise_int(_read_section_value(parser, "urgency_normal", "timeout", str(KDESK_PRESET["normal_timeout"])), KDESK_PRESET["normal_timeout"], minimum=0, maximum=20),
        "critical_timeout": _normalise_int(_read_section_value(parser, "urgency_critical", "timeout", str(KDESK_PRESET["critical_timeout"])), KDESK_PRESET["critical_timeout"], minimum=0, maximum=20),
        "low_background": _normalise_color(_read_section_value(parser, "urgency_low", "background", KDESK_PRESET["low_background"]), KDESK_PRESET["low_background"]),
        "low_foreground": _normalise_color(_read_section_value(parser, "urgency_low", "foreground", KDESK_PRESET["low_foreground"]), KDESK_PRESET["low_foreground"]),
        "low_frame_color": _normalise_color(_read_section_value(parser, "urgency_low", "frame_color", KDESK_PRESET["low_frame_color"]), KDESK_PRESET["low_frame_color"]),
        "normal_background": _normalise_color(_read_section_value(parser, "urgency_normal", "background", KDESK_PRESET["normal_background"]), KDESK_PRESET["normal_background"]),
        "normal_foreground": _normalise_color(_read_section_value(parser, "urgency_normal", "foreground", KDESK_PRESET["normal_foreground"]), KDESK_PRESET["normal_foreground"]),
        "normal_frame_color": _normalise_color(_read_section_value(parser, "urgency_normal", "frame_color", KDESK_PRESET["normal_frame_color"]), KDESK_PRESET["normal_frame_color"]),
        "critical_background": _normalise_color(_read_section_value(parser, "urgency_critical", "background", KDESK_PRESET["critical_background"]), KDESK_PRESET["critical_background"]),
        "critical_foreground": _normalise_color(_read_section_value(parser, "urgency_critical", "foreground", KDESK_PRESET["critical_foreground"]), KDESK_PRESET["critical_foreground"]),
        "critical_frame_color": _normalise_color(_read_section_value(parser, "urgency_critical", "frame_color", KDESK_PRESET["critical_frame_color"]), KDESK_PRESET["critical_frame_color"]),
    }


def read_settings(backend, *, ensure_config: bool = True) -> dict[str, Any]:
    config_path = ensure_user_config(backend) if ensure_config else get_config_path(backend)
    if not config_path.exists():
        values = dict(KDESK_PRESET)
    else:
        values = _settings_from_parser(_parse(_read_file(config_path)))
    values["config_path"] = str(config_path)
    values["config_writable"] = _config_writable(config_path)
    return values


def _update_section_lines(lines: list[str], section: str, mapping: dict[str, str], remove_keys: set[str] | None = None) -> list[str]:
    header_indexes: list[tuple[int, str]] = []
    for index, raw_line in enumerate(lines):
        match = SECTION_HEADER.match(raw_line.strip())
        if match:
            header_indexes.append((index, match.group("section").strip()))

    start = None
    end = len(lines)
    for offset, (index, name) in enumerate(header_indexes):
        if name == section:
            start = index
            if offset + 1 < len(header_indexes):
                end = header_indexes[offset + 1][0]
            break

    if start is None:
        if lines and lines[-1] and not lines[-1].endswith("\n"):
            lines[-1] += "\n"
        if lines and lines[-1].strip():
            lines.append("\n")
        lines.append(f"[{section}]\n")
        for key, value in mapping.items():
            lines.append(f'    {key} = {value}\n')
        return lines

    body = lines[start + 1 : end]
    pending = dict(mapping)
    remove_keys = remove_keys or set()
    updated_body: list[str] = []
    seen_keys: set[str] = set()

    for raw_line in body:
        match = KEY_LINE.match(raw_line)
        if match is None or raw_line.lstrip().startswith(("#", ";")):
            updated_body.append(raw_line)
            continue
        key = match.group("key")
        if key in remove_keys:
            continue
        if key in pending:
            if key in seen_keys:
                continue
            newline = match.group("newline") or "\n"
            updated_body.append(f'{match.group("indent")}{key} = {pending.pop(key)}{newline}')
            seen_keys.add(key)
            continue
        updated_body.append(raw_line)

    if updated_body and updated_body[-1].strip():
        updated_body.append("\n")
    for key, value in pending.items():
        updated_body.append(f"    {key} = {value}\n")

    return lines[: start + 1] + updated_body + lines[end:]


def _serialise_value(key: str, value: Any) -> str:
    if key.endswith("color"):
        return f'"{_normalise_color(str(value), "#ce6a35")}"'
    return str(value)


def _values_to_sections(values: dict[str, Any]) -> dict[str, dict[str, str]]:
    sections: dict[str, dict[str, str]] = {}
    for section, config in SECTION_WRITES.items():
        section_values: dict[str, str] = {}
        for key, (source_key, transform) in config.items():
            section_values[key] = _serialise_value(key, transform(values[source_key]))
        if section == "global" and "frame_color" in section_values:
            section_values["separator_color"] = section_values["frame_color"]
        sections[section] = section_values
    return sections


def write_settings(backend, values: dict[str, Any]) -> dict[str, Any]:
    config_path = ensure_user_config(backend)
    current_state = read_settings(backend, ensure_config=True)
    merged = dict(current_state)
    merged.update(values)
    sections = _values_to_sections(merged)

    lines = _read_file(config_path).splitlines(keepends=True)
    if not lines:
        lines = DEFAULT_DUNSTRC.splitlines(keepends=True)

    for section, mapping in sections.items():
        lines = _update_section_lines(lines, section, mapping, SECTION_REMOVE_KEYS.get(section))

    config_path.write_text("".join(lines), encoding="utf-8")
    return result_payload(
        True,
        "Dunst notification settings were updated.",
        details=[f"Config written to {config_path}."],
    )


def get_do_not_disturb(backend) -> bool | None:
    dunstctl = _tool(backend, "dunstctl")
    if not dunstctl:
        return None
    result = backend._run([dunstctl, "is-paused"], capture=True, timeout=5)
    if result is None or result.returncode != 0:
        return None
    output = (result.stdout or "").strip().lower()
    return output in {"true", "1", "yes"}


def set_do_not_disturb(backend, enabled: bool) -> dict[str, Any]:
    dunstctl = _tool(backend, "dunstctl")
    if not dunstctl:
        return result_payload(False, "dunstctl is not available.", warnings=["Do Not Disturb live control requires dunstctl."])
    result = backend._run([dunstctl, "set-paused", "true" if enabled else "false"], capture=True, timeout=5)
    if result is None or result.returncode != 0:
        return result_payload(False, "Do Not Disturb could not be changed.", warnings=["Dunst did not accept the pause request."])
    return result_payload(True, f"Do Not Disturb {'enabled' if enabled else 'disabled'}.")


def reload_dunst(backend) -> dict[str, Any]:
    dunstctl = _tool(backend, "dunstctl")
    if dunstctl:
        result = backend._run([dunstctl, "reload"], capture=True, timeout=8)
        if result is not None and result.returncode == 0:
            return result_payload(True, "Dunst was reloaded.")

    dunst = _tool(backend, "dunst")
    pkill = _tool(backend, "pkill") or shutil.which("pkill")
    if dunst and pkill:
        backend._run([pkill, "dunst"], capture=True, timeout=5)
        if _spawn_dunst(backend):
            return result_payload(True, "Dunst was restarted.")
    elif dunst and not is_running(backend):
        if _spawn_dunst(backend):
            return result_payload(True, "Dunst was started.")

    return result_payload(False, "Dunst could not be reloaded.", warnings=["Install dunstctl or ensure dunst is available in the current session."])


def send_test_notification(backend, *, critical: bool = False) -> dict[str, Any]:
    notify_send = _tool(backend, "notify-send")
    if not notify_send:
        return result_payload(False, "notify-send is not available.", warnings=["Install libnotify or another notify-send provider to send test notifications."])
    command = [notify_send]
    if critical:
        command.extend(["-u", "critical", "KESKOS WARNING", "Critical notification test."])
    else:
        command.extend(["KESKOS", "Notification backend online."])
    result = backend._run(command, capture=True, timeout=5)
    if result is None or result.returncode != 0:
        return result_payload(False, "The test notification could not be sent.")
    return result_payload(True, "A test notification was sent.")


def open_config(backend) -> dict[str, Any]:
    config_path = ensure_user_config(backend)
    xdg_open = shutil.which("xdg-open")
    if xdg_open is None:
        return result_payload(
            False,
            "xdg-open is not available.",
            warnings=[f"Open the Dunst config manually at {config_path}."],
        )
    try:
        subprocess.Popen(
            [xdg_open, str(config_path)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
        )
    except OSError as exc:
        backend.logger.log(f"dunst_open_config_failed={exc!r}")
        return result_payload(False, "The Dunst config could not be opened.", warnings=[str(exc)])
    return result_payload(True, "Opened the Dunst config.", details=[str(config_path)])


def open_advanced_kde_settings(backend):
    return backend.open_kcm("kcm_notifications")


def apply_kesk_preset(backend) -> dict[str, Any]:
    current_state = read_current(backend, ensure_config=True)
    values = dict(KDESK_PRESET)
    values["enable_notifications"] = current_state["enable_notifications"]
    values["do_not_disturb"] = current_state["do_not_disturb"]
    payload = write_settings(backend, values)
    if payload["success"]:
        reload_payload = reload_dunst(backend)
        payload["details"].extend(reload_payload["details"])
        payload["warnings"].extend(reload_payload["warnings"])
    payload["summary"] = "The KeskOS Dunst preset was applied."
    return payload


def _apply_enable_notifications(backend, enabled: bool) -> list[str]:
    details: list[str] = []
    _backup_autostart(backend)
    autostart = _write_autostart(backend, enabled)
    details.append(f"Autostart updated at {autostart}.")

    dunstctl = _tool(backend, "dunstctl")
    if enabled:
        if dunstctl:
            backend._run([dunstctl, "set-paused", "false"], capture=True, timeout=5)
        if not is_running(backend) and _tool(backend, "dunst"):
            if _spawn_dunst(backend):
                details.append("Dunst was started for the current session.")
    else:
        if dunstctl:
            backend._run([dunstctl, "set-paused", "true"], capture=True, timeout=5)
            details.append("Dunst was paused for the current session.")
        else:
            pkill = _tool(backend, "pkill") or shutil.which("pkill")
            if pkill and is_running(backend):
                backend._run([pkill, "dunst"], capture=True, timeout=5)
                details.append("Dunst was stopped for the current session.")
    return details


def _backend_status(backend, settings: dict[str, Any]) -> BackendStatus:
    dunst = _tool(backend, "dunst")
    dunstctl = _tool(backend, "dunstctl")
    running = is_running(backend)
    writable = bool(settings.get("config_writable"))
    details = [
        "KeskOS uses Dunst as its runtime notification daemon.",
    ]
    if running:
        details.append("Dunst is running in the current session.")
    else:
        details.append("Dunst is not currently running in this session.")

    if dunst and dunstctl and writable:
        return connected("Dunst runtime and live controls are available.", details=details, advanced_module="kcm_notifications")
    if dunst and writable:
        return limited(
            "Dunst config editing is available, but live pause/reload control is limited.",
            details=details,
            missing_tools=["dunstctl"],
            advanced_module="kcm_notifications",
        )
    if writable or Path(str(settings["config_path"])).exists():
        missing_tools = ["dunst"] + ([] if dunstctl else ["dunstctl"])
        return limited(
            "Dunst is not fully available, but the user config can still be edited.",
            details=details,
            missing_tools=missing_tools,
            advanced_module="kcm_notifications",
        )
    return missing(
        "Dunst is not installed and the notification config is not writable.",
        missing_tools=["dunst"],
        advanced_module="kcm_notifications",
    )


def read_current(backend, *, ensure_config: bool = True) -> dict[str, Any]:
    settings = read_settings(backend, ensure_config=ensure_config)
    dunst_available = bool(_tool(backend, "dunst"))
    dunstctl_available = bool(_tool(backend, "dunstctl"))
    notify_send_available = bool(_tool(backend, "notify-send"))
    dnd_state = get_do_not_disturb(backend)
    running = is_running(backend)
    plasma_state = _plasma_notification_state(backend)
    duplicate_risk = running and bool(plasma_state["plasma_notification_active"])
    status = _backend_status(backend, settings)
    notes = [
        "KeskOS uses Dunst for runtime notifications. KDE notification settings are available as an advanced fallback.",
    ]
    hints: list[str] = []
    if not dunstctl_available:
        notes.append("Live Do Not Disturb and clean reload require dunstctl.")
        hints.append("Install dunst or ensure dunstctl is available for live Do Not Disturb and reload.")
    if not notify_send_available:
        notes.append("Test notifications require notify-send.")
        hints.append("Install libnotify for test notifications.")
    if duplicate_risk:
        notes.append(DUPLICATE_RISK_WARNING)
    elif plasma_state["plasma_notification_active"]:
        notes.append(PLASMA_NOTIFICATION_WARNING)
    settings.update(
        {
            "runtime_notifier": "Dunst",
            "dunst_available": dunst_available,
            "dunstctl_available": dunstctl_available,
            "notify_send_available": notify_send_available,
            "dunst_running": running,
            "plasma_notification_active": bool(plasma_state["plasma_notification_active"]),
            "plasma_notification_config_present": bool(plasma_state["notification_config_present"]),
            "plasma_notification_config_paths": list(plasma_state["notification_config_paths"]),
            "duplicate_notification_risk": duplicate_risk,
            "enable_notifications": _read_enable_notifications(backend),
            "do_not_disturb": bool(dnd_state) if dnd_state is not None else False,
            "dnd_supported": dnd_state is not None,
            "reload_supported": bool(dunstctl_available or (dunst_available and (not running or _tool(backend, "pkill") or shutil.which("pkill")))),
            "clean_reload_supported": dunstctl_available,
            "test_supported": notify_send_available,
            "open_config_supported": True,
            "config_editable": bool(settings.get("config_writable")),
            "autostart_path": str(_autostart_path(backend)),
            "status": status,
            "status_note": "\n\n".join(notes + hints),
            "status_notes": notes,
            "dependency_hints": hints,
            "backend_label": status.display_label,
            "enable_reason": "" if dunst_available else "Install dunst to manage runtime notifications.",
            "dnd_reason": (
                ""
                if dnd_state is not None
                else ("Live Do Not Disturb and clean reload require dunstctl." if not dunstctl_available else "Start Dunst to change Do Not Disturb live.")
            ),
            "reload_reason": (
                ""
                if bool(dunstctl_available or (dunst_available and (not running or _tool(backend, "pkill") or shutil.which("pkill"))))
                else "Install dunst or ensure dunstctl is available for live Do Not Disturb and reload."
            ),
            "test_reason": "" if notify_send_available else "Install libnotify for test notifications.",
        }
    )
    return settings


def apply_changes(backend, values: dict[str, Any]) -> dict[str, Any]:
    details: list[str] = []
    warnings: list[str] = []

    config_path = ensure_user_config(backend)
    if not _config_writable(config_path):
        return result_payload(False, "The Dunst config is not writable.", warnings=[f"Check permissions for {config_path}."])

    payload = write_settings(backend, values)
    details.extend(payload["details"])
    warnings.extend(payload["warnings"])

    if "enable_notifications" in values:
        details.extend(_apply_enable_notifications(backend, bool(values["enable_notifications"])))

    if "do_not_disturb" in values:
        dnd_payload = set_do_not_disturb(backend, bool(values["do_not_disturb"]))
        if not dnd_payload["success"]:
            warnings.extend(dnd_payload["warnings"])
        else:
            details.extend(dnd_payload["details"])

    reload_payload = reload_dunst(backend)
    if not reload_payload["success"]:
        warnings.extend(reload_payload["warnings"])
    else:
        details.extend(reload_payload["details"])

    return result_payload(
        True,
        "Dunst notification preferences were updated.",
        details=details,
        warnings=warnings,
    )
