from __future__ import annotations

import configparser
from dataclasses import dataclass, field
from datetime import datetime
import getpass
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import sys
import tempfile
from typing import Any, Iterable, Sequence

try:
    import pwd
except ImportError:  # pragma: no cover - non-POSIX fallback for smoke tests
    pwd = None

from common import APP_VERSION, SessionLogger, shell_join
from .backends import accounts as accounts_backend
from .backends import accessibility as accessibility_backend
from .backends import audio as audio_backend
from .backends import bluetooth as bluetooth_backend
from .backends import boot_login as boot_login_backend
from .backends import display as display_backend
from .backends import file_associations as file_associations_backend
from .backends import notifications as notifications_backend
from .backends import privacy as privacy_backend
from .backends import privileged as privileged_backend
from .backends import proxy as proxy_backend
from .backends import search as search_backend
from .backends import task_switcher as task_switcher_backend
from .backends import vpn as vpn_backend


DOC_LINKS: tuple[tuple[str, str], ...] = (
    ("Docs", "https://docs.keskos.org"),
    ("Website", "https://keskos.org"),
    ("Downloads", "https://downloads.keskos.org"),
    ("GitHub", "https://github.com/memegeko/keskos"),
)

ACCENT_ORANGE = "#ce6a35"
DEFAULT_LOOK_AND_FEEL = "com.keskos.desktop"
DEFAULT_COLOR_SCHEME = "KESKOS"
DEFAULT_PLASMA_THEME = "keskos-shell"
DEFAULT_WINDOW_DECORATION = "kwin4_decoration_qml_keskos_split"
DEFAULT_WALLPAPER_CANDIDATES = (
    Path("/usr/share/backgrounds/keskos/wallpaper.jpg"),
    Path("/usr/share/backgrounds/keskos/wallpaper-2560x1440.png"),
    Path("/usr/share/backgrounds/keskos/wallpaper-1920x1080.png"),
)
FIRST_RUN_STATE_FILE = Path.home() / ".config" / "keskos" / "first-run-complete"
TERMINAL_PROMPT_STYLES = ("keskos", "minimal")

DEFAULT_KESK_SETTINGS: dict[str, Any] = {
    "accent_color": ACCENT_ORANGE,
    "kesk_theme_mode": "full",
    "crt_effects": True,
    "scanlines": True,
    "glow_intensity": 70,
    "terminal_font": "JetBrains Mono",
    "wallpaper_path": "",
    "wallpaper_fit": "Fill",
    "random_wallpaper": False,
    "wallpaper_folder": "",
    "apply_wallpaper_to_lock": False,
    "desktop_icons": True,
    "desktop_toolbox": True,
    "desktop_containment": "folder_view",
    "desktop_show_hidden": False,
    "screen_edge_behavior": "overview",
    "panel_mode": "kesk_panel",
    "launcher_enabled": True,
    "launcher_style": "keskos",
    "launcher_keybind": "Meta",
    "top_panel_enabled": True,
    "bottom_panel_enabled": True,
    "panel_opacity": 100,
    "panel_glow_intensity": 60,
    "bottom_panel_autohide": False,
    "workspace_switcher": True,
    "hud_widgets_enabled": True,
    "hud_cpu_widget": True,
    "hud_memory_widget": True,
    "hud_network_widget": True,
    "hud_media_widget": True,
    "hud_clock_widget": True,
    "hud_widget_position": "top-right",
    "quickshell_experimental_mode": False,
    "new_launcher_backend": False,
    "new_settings_backend": False,
    "debug_ui_overlays": False,
    "input_tap_to_click": True,
    "input_natural_scroll": False,
    "input_two_finger_scroll": True,
    "input_disable_touchpad_while_typing": True,
    "input_acceleration_profile": "adaptive",
    "input_right_click_method": "two_finger",
    "input_repeat_enabled": True,
    "input_numlock_startup": "unchanged",
    "input_compose_key": "Disabled",
    "mouse_speed": 50,
    "display_night_color": False,
    "display_scale_percent": 100,
    "display_refresh_rate": 60,
    "display_orientation": "Normal",
    "display_brightness": 100,
    "display_resolution": "Automatic",
    "sound_audio_profile": "Stereo",
    "network_metered": False,
    "power_blank_timeout": 10,
    "power_sleep_timeout": 30,
    "power_show_battery_percent": True,
    "power_lid_action": "sleep",
    "power_dim_screen": True,
    "power_low_battery_action": "suspend",
    "user_display_name": "",
    "update_notifications": True,
    "update_auto_check": True,
    "update_check_interval": 24,
    "update_include_aur": True,
    "update_include_flatpak": True,
    "update_include_firmware": True,
    "boot_splash_min_duration": 2,
    "boot_show_logs": False,
    "boot_quiet_boot": True,
    "boot_terminal_text": False,
    "show_user_list": True,
    "login_background": "",
    "default_browser_preference": "librewolf.desktop",
    "default_video_player_preference": "",
    "default_music_player_preference": "",
    "default_mail_preference": "",
    "browser_homepage_enabled": True,
    "browser_theme_enabled": False,
    "telemetry_enabled": False,
    "local_analytics_dashboard": False,
    "experimental_features": False,
    "prompt_style": "keskos",
    "bluetooth_receive_files": False,
    "accounts_sync_calendar": True,
    "accounts_sync_files": True,
    "accounts_sync_contacts": True,
    "privacy_recent_files_history": True,
    "privacy_file_search": False,
}

FOCUS_POLICIES = (
    ("ClickToFocus", "Click to focus"),
    ("FocusFollowsMouse", "Focus follows mouse"),
)
WINDOW_BORDER_SIZES = ("None", "Tiny", "Normal", "Large", "VeryLarge", "Huge", "VeryHuge", "Oversized")
TITLEBAR_LAYOUTS = {
    "Breeze": ("MS", "HIAX"),
    "Compact": ("", "HIA"),
    "Mac": ("HI", "AX"),
}
POWER_PROFILES = ("performance", "balanced", "power-saver")

BROWSER_OPTIONS: tuple[tuple[str, str], ...] = (
    ("librewolf.desktop", "LibreWolf"),
    ("brave-browser.desktop", "Brave"),
    ("zen-browser.desktop", "Zen"),
    ("firefox.desktop", "Firefox"),
)
TERMINAL_OPTIONS: tuple[tuple[str, str, str], ...] = (
    ("keskos-terminal.desktop", "KeskOS Terminal", "konsole"),
    ("org.kde.konsole.desktop", "Konsole", "konsole"),
    ("konsole.desktop", "Konsole", "konsole"),
    ("kitty.desktop", "Kitty", "kitty"),
)
FILE_MANAGER_OPTIONS: tuple[tuple[str, str], ...] = (
    ("org.kde.dolphin.desktop", "Dolphin"),
    ("dolphin.desktop", "Dolphin"),
    ("thunar.desktop", "Thunar"),
    ("nautilus.desktop", "Files"),
)
EDITOR_OPTIONS: tuple[tuple[str, str], ...] = (
    ("org.kde.kate.desktop", "Kate"),
    ("kate.desktop", "Kate"),
    ("org.gnome.gedit.desktop", "Gedit"),
    ("codium.desktop", "VSCodium"),
)
IMAGE_VIEWER_OPTIONS: tuple[tuple[str, str], ...] = (
    ("org.kde.gwenview.desktop", "Gwenview"),
    ("gwenview.desktop", "Gwenview"),
    ("org.kde.okular.desktop", "Okular"),
    ("eog.desktop", "Image Viewer"),
)
VIDEO_PLAYER_OPTIONS: tuple[tuple[str, str], ...] = (
    ("org.kde.haruna.desktop", "Haruna"),
    ("vlc.desktop", "VLC"),
    ("mpv.desktop", "MPV"),
)
MUSIC_PLAYER_OPTIONS: tuple[tuple[str, str], ...] = (
    ("elisa.desktop", "Elisa"),
    ("org.kde.elisa.desktop", "Elisa"),
    ("spotify.desktop", "Spotify"),
    ("rhythmbox.desktop", "Rhythmbox"),
)
MAIL_OPTIONS: tuple[tuple[str, str], ...] = (
    ("thunderbird.desktop", "Thunderbird"),
    ("org.kde.kmail2.desktop", "KMail"),
    ("evolution.desktop", "Evolution"),
)


@dataclass(frozen=True)
class SelectOption:
    value: str
    label: str


@dataclass
class RuntimePaths:
    root: Path
    usr_root: Path
    staged_root: Path
    home: Path
    router_path: Path
    gui_path: Path
    logs_dir: Path
    backups_dir: Path
    settings_path: Path
    ui_state_path: Path
    docs_local_path: Path | None


@dataclass
class GuiPrefs:
    width: int = 1240
    height: int = 820
    last_page: str = "appearance"


@dataclass
class ApplyResult:
    success: bool
    summary: str
    details: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    requires: list[str] = field(default_factory=list)
    backup_path: Path | None = None


def command_exists(name: str) -> bool:
    return shutil.which(name) is not None


def python_command(path: Path, *extra_args: str) -> list[str]:
    if os.access(path, os.X_OK):
        return [str(path), *extra_args]
    return [sys.executable, str(path), *extra_args]


def runtime_candidate_paths(*parts: str) -> list[Path]:
    candidates: list[Path] = []
    uid = os.getuid() if hasattr(os, "getuid") else os.getpid()

    if os.environ.get("XDG_RUNTIME_DIR"):
        candidates.append(Path(os.environ["XDG_RUNTIME_DIR"]).expanduser() / "kesk" / Path(*parts))
    candidates.append(Path(tempfile.gettempdir()) / f"kesk-{uid}" / Path(*parts))
    return candidates


def ensure_writable_dir(candidates: Sequence[Path]) -> Path:
    seen: set[Path] = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        try:
            candidate.mkdir(parents=True, exist_ok=True)
        except OSError:
            continue
        return candidate
    fallback = candidates[-1] if candidates else Path(tempfile.gettempdir()) / f"kesk-{os.getpid()}"
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback


def resolve_runtime_paths(root: Path) -> RuntimePaths:
    usr_root = root.parents[1]
    staged_root = root.parents[2]
    home = Path.home()

    router_candidates = [usr_root / "bin" / "kesk", Path("/usr/bin/kesk")]
    gui_candidates = [usr_root / "bin" / "kesk-settings", Path("/usr/bin/kesk-settings")]
    docs_candidates = [staged_root / "docs", Path.cwd() / "docs", Path("/usr/share/doc/keskos")]

    router_path = next((path for path in router_candidates if path.is_file()), router_candidates[0])
    gui_path = next((path for path in gui_candidates if path.is_file()), gui_candidates[0])
    docs_local_path = next((path for path in docs_candidates if path.is_dir()), None)

    logs_candidates: list[Path] = []
    if os.environ.get("KESK_LOG_DIR"):
        logs_candidates.append(Path(os.environ["KESK_LOG_DIR"]).expanduser())
    if os.environ.get("XDG_STATE_HOME"):
        state_home = Path(os.environ["XDG_STATE_HOME"]).expanduser() / "kesk"
        logs_candidates.append(state_home / "logs")
        backup_candidates = [state_home / "settings-backups", *runtime_candidate_paths("settings-backups")]
    else:
        backup_candidates = [home / ".local" / "state" / "kesk" / "settings-backups", *runtime_candidate_paths("settings-backups")]

    logs_candidates.extend([home / ".local" / "state" / "kesk" / "logs", *runtime_candidate_paths("logs")])

    if os.environ.get("XDG_CONFIG_HOME"):
        config_candidates = [Path(os.environ["XDG_CONFIG_HOME"]).expanduser() / "kesk", *runtime_candidate_paths("config")]
    else:
        config_candidates = [home / ".config" / "kesk", *runtime_candidate_paths("config")]

    logs_dir = ensure_writable_dir(logs_candidates)
    backups_dir = ensure_writable_dir(backup_candidates)
    config_dir = ensure_writable_dir(config_candidates)
    settings_path = config_dir / "settings.json"
    ui_state_path = config_dir / "settings-gui.ini"

    return RuntimePaths(
        root=root,
        usr_root=usr_root,
        staged_root=staged_root,
        home=home,
        router_path=router_path,
        gui_path=gui_path,
        logs_dir=logs_dir,
        backups_dir=backups_dir,
        settings_path=settings_path,
        ui_state_path=ui_state_path,
        docs_local_path=docs_local_path,
    )


def load_prefs(path: Path) -> GuiPrefs:
    parser = configparser.ConfigParser()
    parser.optionxform = str
    if path.is_file():
        parser.read(path, encoding="utf-8")

    prefs = GuiPrefs()
    prefs.width = parser.getint("window", "width", fallback=prefs.width)
    prefs.height = parser.getint("window", "height", fallback=prefs.height)
    prefs.last_page = parser.get("window", "last_page", fallback=prefs.last_page)
    return prefs


def save_prefs(path: Path, prefs: GuiPrefs) -> None:
    parser = configparser.ConfigParser()
    parser.optionxform = str
    parser["window"] = {
        "width": str(prefs.width),
        "height": str(prefs.height),
        "last_page": prefs.last_page,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        parser.write(handle)


def open_target(target: str, logger: SessionLogger) -> tuple[bool, str]:
    if not command_exists("xdg-open"):
        logger.log(f"open_target=missing:{target}")
        return False, target

    command = ["xdg-open", target]
    logger.log(f"command={shell_join(command)}")
    try:
        process = subprocess.Popen(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
        )
    except OSError as exc:
        logger.log(f"open_target=failed:{exc!r}")
        return False, str(exc)

    logger.log(f"spawned_pid={process.pid}")
    return True, target


def launch_terminal_command(command: Sequence[str], logger: SessionLogger) -> tuple[subprocess.Popen[bytes] | None, str]:
    command_list: list[str]
    if command_exists("konsole"):
        command_list = ["konsole", "--hold", "--workdir", str(Path.home()), "-e", *command]
    elif command_exists("xterm"):
        command_list = ["xterm", "-hold", "-e", *command]
    elif command_exists("gnome-terminal"):
        command_list = ["gnome-terminal", "--", *command]
    else:
        return None, "No supported terminal launcher was found."

    logger.log(f"command={shell_join(command_list)}")
    try:
        process = subprocess.Popen(
            command_list,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
        )
    except OSError as exc:
        logger.log(f"terminal_launch_failed={exc!r}")
        return None, str(exc)
    logger.log(f"terminal_launch_pid={process.pid}")
    return process, shell_join(command)


def section_name(groups: Sequence[str]) -> str:
    return "][".join(groups)


def read_key_value_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return values
    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"')
    return values


def read_first_line(path: Path) -> str | None:
    if not path.is_file():
        return None
    try:
        for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            line = raw_line.strip()
            if line:
                return line
    except OSError:
        return None
    return None


def first_nonempty_line(command: Sequence[str], timeout: int = 10) -> str:
    try:
        result = subprocess.run(
            list(command),
            check=False,
            capture_output=True,
            text=True,
            errors="replace",
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired):
        return "unavailable"

    for line in (*result.stdout.splitlines(), *result.stderr.splitlines()):
        stripped = line.strip()
        if stripped:
            return stripped
    return "unavailable"


def detect_qt_version() -> str:
    if command_exists("qmake6"):
        return first_nonempty_line(["qmake6", "--version"])
    if command_exists("qtpaths6"):
        return first_nonempty_line(["qtpaths6", "--qt-version"])
    return "unavailable"


def detect_uptime() -> str:
    if command_exists("uptime"):
        value = first_nonempty_line(["uptime", "-p"])
        if value != "unavailable":
            return value

    proc_uptime = Path("/proc/uptime")
    if not proc_uptime.is_file():
        return "unavailable"

    try:
        total_seconds = int(float(proc_uptime.read_text(encoding="utf-8", errors="replace").split()[0]))
    except (OSError, ValueError, IndexError):
        return "unavailable"

    days, remainder = divmod(total_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, _seconds = divmod(remainder, 60)
    parts: list[str] = []
    if days:
        parts.append(f"{days} day{'s' if days != 1 else ''}")
    if hours:
        parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
    if minutes or not parts:
        parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
    return "up " + ", ".join(parts)


def detect_package_count() -> str:
    if not command_exists("pacman"):
        return "unavailable"
    try:
        result = subprocess.run(
            ["pacman", "-Qq"],
            check=False,
            capture_output=True,
            text=True,
            errors="replace",
            timeout=20,
        )
    except (OSError, subprocess.TimeoutExpired):
        return "unavailable"
    if result.returncode != 0:
        return "unavailable"
    return str(sum(1 for line in result.stdout.splitlines() if line.strip()))


def detect_frameworks_version() -> str:
    if command_exists("kf6-config"):
        return first_nonempty_line(["kf6-config", "--version"])
    return "unavailable"


def detect_cpu_model() -> str:
    cpuinfo = Path("/proc/cpuinfo")
    if cpuinfo.is_file():
        try:
            for line in cpuinfo.read_text(encoding="utf-8", errors="replace").splitlines():
                if line.lower().startswith("model name"):
                    return line.split(":", 1)[1].strip()
        except OSError:
            pass
    return "unavailable"


def detect_gpu_model() -> str:
    if command_exists("lspci"):
        try:
            result = subprocess.run(["lspci"], check=False, capture_output=True, text=True, errors="replace", timeout=10)
        except (OSError, subprocess.TimeoutExpired):
            result = None
        if result is not None:
            for line in result.stdout.splitlines():
                lowered = line.lower()
                if "vga compatible controller" in lowered or "3d controller" in lowered:
                    return line.split(":", 2)[-1].strip()
    return "unavailable"


def detect_total_ram() -> str:
    meminfo = Path("/proc/meminfo")
    if meminfo.is_file():
        try:
            for line in meminfo.read_text(encoding="utf-8", errors="replace").splitlines():
                if line.startswith("MemTotal:"):
                    parts = line.split()
                    kib = int(parts[1])
                    gib = kib / 1024 / 1024
                    return f"{gib:.1f} GiB"
        except (OSError, ValueError, IndexError):
            pass
    return "unavailable"


def detect_root_disk() -> str:
    try:
        usage = shutil.disk_usage(Path.home())
    except OSError:
        try:
            usage = shutil.disk_usage("/")
        except OSError:
            return "unavailable"
    total_gib = usage.total / 1024 / 1024 / 1024
    used_percent = int((usage.used / usage.total) * 100) if usage.total else 0
    return f"{total_gib:.1f} GiB total, {used_percent}% used"


def staged_root(root: Path) -> Path | None:
    try:
        candidate = root.parents[2]
    except IndexError:
        return None
    return candidate if candidate.is_dir() else None


def prefer_kesk_values(primary: dict[str, str], fallback: dict[str, str]) -> dict[str, str]:
    pretty = primary.get("PRETTY_NAME", "") or primary.get("NAME", "")
    if pretty and "kesk" in pretty.lower():
        return primary
    return fallback or primary


def collect_release_info(root: Path) -> tuple[str, str]:
    staged = staged_root(root)

    system_os_release = read_key_value_file(Path("/etc/os-release"))
    staged_os_release = read_key_value_file(staged / "etc" / "os-release") if staged else {}
    os_release = prefer_kesk_values(system_os_release, staged_os_release)

    system_kesk_release = read_key_value_file(Path("/etc/kesk-release"))
    staged_kesk_release = read_key_value_file(staged / "etc" / "kesk-release") if staged else {}
    kesk_release = staged_kesk_release or system_kesk_release

    system_kesk_version = read_key_value_file(Path("/usr/share/kesk/version"))
    staged_kesk_version = read_key_value_file(staged / "usr" / "share" / "kesk" / "version") if staged else {}
    kesk_version = staged_kesk_version or system_kesk_version

    raw_version_line = read_first_line(Path("/usr/share/kesk/version"))
    if raw_version_line is None and staged:
        raw_version_line = read_first_line(staged / "usr" / "share" / "kesk" / "version")

    version_name = (
        os_release.get("PRETTY_NAME")
        or kesk_release.get("PRETTY_NAME")
        or kesk_release.get("NAME")
        or kesk_version.get("PRETTY_NAME")
        or raw_version_line
        or "unknown"
    )
    build_id = (
        os_release.get("BUILD_ID")
        or kesk_release.get("BUILD_ID")
        or kesk_release.get("LAYER")
        or kesk_version.get("BUILD_ID")
        or kesk_version.get("VERSION")
        or "unknown"
    )
    return version_name, build_id


class SettingsBackend:
    def __init__(self, paths: RuntimePaths, logger: SessionLogger | None = None) -> None:
        self.paths = paths
        self.logger = logger or SessionLogger("settings-backend")
        self.tools = self._discover_tools()
        self.custom_settings = self._load_custom_settings()

    def _discover_tools(self) -> dict[str, str | None]:
        binaries = (
            "kwriteconfig6",
            "kreadconfig6",
            "lookandfeeltool",
            "plasma-apply-colorscheme",
            "plasma-apply-cursortheme",
            "plasma-apply-desktoptheme",
            "plasma-apply-wallpaperimage",
            "kscreen-doctor",
            "qdbus6",
            "kcminit6",
            "kbuildsycoca6",
            "kcmshell6",
            "systemsettings",
            "wpctl",
            "pactl",
            "dunst",
            "dunstctl",
            "notify-send",
            "nmcli",
            "powerprofilesctl",
            "hostnamectl",
            "pkexec",
            "pgrep",
            "pkill",
            "quickshell",
            "bluetoothctl",
            "rfkill",
            "systemctl",
            "balooctl6",
            "xdg-mime",
            "xdg-settings",
            "flatseal",
            "brightnessctl",
            "ddcutil",
            "kwalletd6",
            "plymouth-set-default-theme",
            "mkinitcpio",
            "keskos-launcher-switch",
            "keskos-reset-panel",
            "keskos-wallpaper-apply",
        )
        return {name: shutil.which(name) for name in binaries}

    def refresh(self) -> None:
        self.tools = self._discover_tools()
        self.custom_settings = self._load_custom_settings()

    def _log_command(self, command: Sequence[str]) -> None:
        self.logger.log(f"command={shell_join(command)}")

    def _run(
        self,
        command: Sequence[str],
        *,
        capture: bool = True,
        timeout: int = 20,
        check: bool = False,
        allow_failure: bool = True,
    ) -> subprocess.CompletedProcess[str] | None:
        self._log_command(command)
        try:
            result = subprocess.run(
                list(command),
                check=check,
                capture_output=capture,
                text=True,
                errors="replace",
                timeout=timeout,
            )
        except (OSError, subprocess.TimeoutExpired, subprocess.CalledProcessError) as exc:
            self.logger.log(f"command_error={exc!r}")
            if allow_failure:
                return None
            raise

        self.logger.log(f"exit_code={result.returncode}")
        if capture and result.stdout.strip():
            for line in result.stdout.splitlines():
                self.logger.log(f"stdout {line}")
        if capture and result.stderr.strip():
            for line in result.stderr.splitlines():
                self.logger.log(f"stderr {line}")
        return result

    def _load_custom_settings(self) -> dict[str, Any]:
        data = dict(DEFAULT_KESK_SETTINGS)
        if self.paths.settings_path.is_file():
            try:
                payload = json.loads(self.paths.settings_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                payload = {}
            if isinstance(payload, dict):
                data.update(payload)
        return data

    def _write_custom_settings(self) -> None:
        self.paths.settings_path.parent.mkdir(parents=True, exist_ok=True)
        self.paths.settings_path.write_text(json.dumps(self.custom_settings, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def custom_value(self, key: str, default: Any = None) -> Any:
        return self.custom_settings.get(key, default)

    def set_custom_values(self, updates: dict[str, Any]) -> None:
        self.custom_settings.update(updates)
        self._write_custom_settings()

    def _parser(self, path: Path) -> configparser.ConfigParser:
        parser = configparser.ConfigParser(interpolation=None)
        parser.optionxform = str
        if path.exists():
            parser.read(path, encoding="utf-8")
        return parser

    def _read_ini_value(self, path: Path, groups: Sequence[str], key: str, default: str = "") -> str:
        parser = self._parser(path)
        return parser.get(section_name(groups), key, fallback=default)

    def _write_ini_value(self, path: Path, groups: Sequence[str], key: str, value: str) -> None:
        parser = self._parser(path)
        section = section_name(groups)
        if not parser.has_section(section):
            parser.add_section(section)
        parser.set(section, key, value)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as handle:
            parser.write(handle)

    def kread(self, path: Path, groups: Sequence[str], key: str, default: str = "") -> str:
        tool = self.tools.get("kreadconfig6")
        if tool:
            command = [tool, "--file", str(path)]
            for group in groups:
                command.extend(["--group", group])
            command.extend(["--key", key])
            result = self._run(command, capture=True, timeout=10)
            if result is not None and result.returncode == 0:
                return result.stdout.strip() or default
        return self._read_ini_value(path, groups, key, default)

    def kwrite(self, path: Path, groups: Sequence[str], key: str, value: str) -> None:
        tool = self.tools.get("kwriteconfig6")
        if tool:
            command = [tool, "--file", str(path)]
            for group in groups:
                command.extend(["--group", group])
            command.extend(["--key", key, value])
            result = self._run(command, capture=True, timeout=10)
            if result is not None and result.returncode == 0:
                return
        self._write_ini_value(path, groups, key, value)

    def backup_files(self, label: str, files: Iterable[Path], metadata: dict[str, Any] | None = None) -> Path | None:
        items = [path.expanduser() for path in files if path and path.exists()]
        if not items and not self.paths.settings_path.exists():
            return None

        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup_root = self.paths.backups_dir / f"{timestamp}-{label}"
        backup_root.mkdir(parents=True, exist_ok=True)
        manifest: list[dict[str, str]] = []

        for path in items:
            if path.is_dir():
                continue
            if path.is_relative_to(self.paths.home):
                stored = backup_root / "home" / path.relative_to(self.paths.home)
            else:
                stored = backup_root / "system" / str(path).lstrip("/").replace(":", "")
            stored.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, stored)
            manifest.append({"original": str(path), "stored": str(stored.relative_to(backup_root))})

        if self.paths.settings_path.exists() and self.paths.settings_path not in items:
            stored = backup_root / "home" / self.paths.settings_path.relative_to(self.paths.home)
            stored.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(self.paths.settings_path, stored)
            manifest.append({"original": str(self.paths.settings_path), "stored": str(stored.relative_to(backup_root))})

        payload = {"label": label, "created_at": datetime.now().isoformat(), "files": manifest, "metadata": metadata or {}}
        (backup_root / "manifest.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        self.logger.log(f"settings_backup={backup_root}")
        return backup_root

    def latest_backup(self, label: str) -> Path | None:
        candidates = sorted(self.paths.backups_dir.glob(f"*-{label}"), reverse=True)
        for candidate in candidates:
            if candidate.is_dir():
                return candidate
        return None

    def restore_latest_backup(self, label: str, allowed_suffixes: Sequence[str] | None = None) -> ApplyResult:
        backup_root = self.latest_backup(label)
        if backup_root is None:
            return ApplyResult(False, "No backup is available for this settings group.")

        manifest_path = backup_root / "manifest.json"
        if not manifest_path.is_file():
            return ApplyResult(False, "The selected backup is missing its manifest.")

        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            return ApplyResult(False, f"Could not read backup manifest: {exc}")

        restored = 0
        for item in manifest.get("files", []):
            original = Path(item["original"])
            if allowed_suffixes and original.suffix not in allowed_suffixes:
                continue
            stored = backup_root / item["stored"]
            if not stored.is_file():
                continue
            original.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(stored, original)
            restored += 1

        self.refresh_runtime()
        return ApplyResult(True, f"Restored {restored} file(s) from the latest {label} backup.", backup_path=backup_root)

    def settings_file(self, name: str) -> Path:
        return self.paths.home / ".config" / name

    @property
    def kdeglobals(self) -> Path:
        return self.settings_file("kdeglobals")

    @property
    def kwinrc(self) -> Path:
        return self.settings_file("kwinrc")

    @property
    def plasmarc(self) -> Path:
        return self.settings_file("plasmarc")

    @property
    def plasmashellrc(self) -> Path:
        return self.settings_file("plasmashellrc")

    @property
    def kcminputrc(self) -> Path:
        return self.settings_file("kcminputrc")

    @property
    def kxkbrc(self) -> Path:
        return self.settings_file("kxkbrc")

    @property
    def kscreenlockerrc(self) -> Path:
        return self.settings_file("kscreenlockerrc")

    @property
    def ksplashrc(self) -> Path:
        return self.settings_file("ksplashrc")

    @property
    def mimeapps(self) -> Path:
        return self.paths.home / ".config" / "mimeapps.list"

    @property
    def baloofilerc(self) -> Path:
        return self.settings_file("baloofilerc")

    @property
    def kioslaverc(self) -> Path:
        return self.settings_file("kioslaverc")

    @property
    def kaccessrc(self) -> Path:
        return self.settings_file("kaccessrc")

    @property
    def kcmaccessrc(self) -> Path:
        return self.settings_file("kcmaccessrc")

    @property
    def kactivitymanagerdrc(self) -> Path:
        return self.settings_file("kactivitymanagerdrc")

    @property
    def launcher_mode_path(self) -> Path:
        return self.paths.home / ".config" / "keskos" / "launcher-mode"

    @property
    def prompt_overlay_path(self) -> Path:
        return self.paths.home / ".config" / "keskos" / "bashrc"

    def official_wallpaper_candidates(self) -> list[Path]:
        candidates: list[Path] = list(DEFAULT_WALLPAPER_CANDIDATES)
        asset_root = self.paths.staged_root / "assets"
        candidates.extend(
            [
                asset_root / "wallpaper.jpg",
                asset_root / "wallpaper-4096x2160.png",
                asset_root / "wallpaper-2560x1440.png",
                asset_root / "wallpaper-1920x1080.png",
                asset_root / "wallpaper.png",
                asset_root / "wallpaper.svg",
            ]
        )

        deduped: list[Path] = []
        seen: set[Path] = set()
        for candidate in candidates:
            if candidate in seen:
                continue
            seen.add(candidate)
            deduped.append(candidate)
        return deduped

    def official_wallpaper(self) -> str:
        for candidate in self.official_wallpaper_candidates():
            if candidate.is_file():
                return str(candidate)
        return ""

    def is_kesk_look_and_feel(self, value: str) -> bool:
        lowered = value.strip().lower()
        return lowered == DEFAULT_LOOK_AND_FEEL.lower() or "kesk" in lowered

    def is_official_wallpaper(self, value: str) -> bool:
        path = Path(value).expanduser()
        if not value:
            return False
        try:
            resolved = path.resolve()
        except OSError:
            return False
        for candidate in self.official_wallpaper_candidates():
            try:
                if candidate.resolve() == resolved:
                    return True
            except OSError:
                continue
        return False

    def default_wallpaper(self) -> str:
        custom_path = str(self.custom_value("wallpaper_path", "")).strip()
        if custom_path and Path(custom_path).expanduser().is_file():
            return custom_path
        return self.official_wallpaper()

    def metadata_label(self, path: Path) -> str:
        json_candidates = (path / "metadata.json", path / "contents" / "metadata.json")
        for candidate in json_candidates:
            if candidate.is_file():
                try:
                    payload = json.loads(candidate.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    continue
                plugin = payload.get("KPlugin", {})
                label = plugin.get("Name") or payload.get("Name")
                if label:
                    return str(label)

        desktop_candidates = (path / "metadata.desktop", path / "index.theme")
        for candidate in desktop_candidates:
            if candidate.is_file():
                parser = configparser.ConfigParser(interpolation=None)
                parser.optionxform = str
                try:
                    parser.read(candidate, encoding="utf-8")
                except (OSError, configparser.Error):
                    continue
                for section in ("Desktop Entry", "KDE", "Icon Theme"):
                    if parser.has_option(section, "Name"):
                        return parser.get(section, "Name")
        return path.name

    def _dir_options(self, roots: Sequence[Path], *relative_parts: str) -> list[SelectOption]:
        options: dict[str, str] = {}
        for root in roots:
            base = root.joinpath(*relative_parts)
            if not base.is_dir():
                continue
            for child in sorted(base.iterdir()):
                if not child.is_dir():
                    continue
                options[child.name] = self.metadata_label(child)
        return [SelectOption(value=value, label=options[value]) for value in sorted(options, key=lambda item: options[item].lower())]

    def _file_options(self, roots: Sequence[Path], relative: str, pattern: str, suffix_to_strip: str) -> list[SelectOption]:
        options: dict[str, str] = {}
        for root in roots:
            base = root / relative
            if not base.is_dir():
                continue
            for child in sorted(base.glob(pattern)):
                value = child.name.removesuffix(suffix_to_strip)
                options[value] = value
        return [SelectOption(value=value, label=options[value]) for value in sorted(options, key=str.lower)]

    def look_and_feel_options(self) -> list[SelectOption]:
        return self._dir_options((Path("/usr/share"), self.paths.home / ".local" / "share"), "plasma", "look-and-feel")

    def plasma_theme_options(self) -> list[SelectOption]:
        return self._dir_options((Path("/usr/share"), self.paths.home / ".local" / "share"), "plasma", "desktoptheme")

    def color_scheme_options(self) -> list[SelectOption]:
        return self._file_options((Path("/usr/share"), self.paths.home / ".local" / "share"), "color-schemes", "*.colors", ".colors")

    def icon_theme_options(self) -> list[SelectOption]:
        roots = [Path("/usr/share"), self.paths.home / ".local" / "share", self.paths.home]
        options: dict[str, str] = {}
        for root in roots:
            base = root / "icons" if root != self.paths.home else root / ".icons"
            if not base.is_dir():
                continue
            for child in sorted(base.iterdir()):
                if (child / "index.theme").is_file():
                    options[child.name] = self.metadata_label(child)
        return [SelectOption(value=value, label=options[value]) for value in sorted(options, key=lambda item: options[item].lower())]

    def cursor_theme_options(self) -> list[SelectOption]:
        options = []
        for choice in self.icon_theme_options():
            if (Path("/usr/share/icons") / choice.value / "cursors").is_dir() or (self.paths.home / ".local" / "share" / "icons" / choice.value / "cursors").is_dir() or (self.paths.home / ".icons" / choice.value / "cursors").is_dir():
                options.append(choice)
        return options

    def window_decoration_options(self) -> list[SelectOption]:
        return self._dir_options((Path("/usr/share"), self.paths.home / ".local" / "share"), "aurorae", "themes")

    def sddm_theme_options(self) -> list[SelectOption]:
        base = Path("/usr/share/sddm/themes")
        if not base.is_dir():
            return []
        return [SelectOption(child.name, child.name) for child in sorted(base.iterdir()) if child.is_dir()]

    def plymouth_theme_options(self) -> list[SelectOption]:
        base = Path("/usr/share/plymouth/themes")
        if not base.is_dir():
            return []
        return [SelectOption(child.name, child.name) for child in sorted(base.iterdir()) if child.is_dir()]

    def bool_text(self, value: bool) -> str:
        return "true" if value else "false"

    def find_option_value(self, options: Sequence[SelectOption], *patterns: str, fallback: str = "") -> str:
        for pattern in patterns:
            lowered = pattern.lower()
            for option in options:
                haystack = f"{option.value} {option.label}".lower()
                if lowered == option.value.lower() or lowered in haystack:
                    return option.value
        return fallback

    def as_bool(self, value: Any, default: bool = False) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return bool(value)
        if isinstance(value, str):
            lowered = value.strip().lower()
            if lowered in {"1", "true", "yes", "on"}:
                return True
            if lowered in {"0", "false", "no", "off"}:
                return False
        return default

    def parse_int(self, value: str, default: int) -> int:
        try:
            return int(str(value).strip())
        except (TypeError, ValueError):
            return default

    def ensure_choice(self, value: str, options: Sequence[SelectOption]) -> list[SelectOption]:
        if not value:
            return list(options)
        if any(option.value == value for option in options):
            return list(options)
        return [SelectOption(value, value), *options]

    def wallpaper_preview_candidates(self) -> list[str]:
        candidates = [self.default_wallpaper()]
        pictures = self.paths.home / "Pictures"
        if pictures.is_dir():
            for pattern in ("*.png", "*.jpg", "*.jpeg", "*.webp"):
                for match in sorted(pictures.glob(pattern))[:4]:
                    candidates.append(str(match))
        return [candidate for candidate in dict.fromkeys(candidates) if candidate]

    def appearance_state(self) -> dict[str, Any]:
        current_font = self.kread(self.kdeglobals, ("General",), "font", "JetBrains Mono,10,-1,5,50,0,0,0,0,0")
        icon_theme = self.kread(self.kdeglobals, ("Icons",), "Theme", "breeze")
        cursor_theme = self.kread(self.kcminputrc, ("Mouse",), "cursorTheme", "breeze_cursors")
        return {
            "look_and_feel": self.kread(self.kdeglobals, ("KDE",), "LookAndFeelPackage", DEFAULT_LOOK_AND_FEEL),
            "plasma_theme": self.kread(self.plasmarc, ("Theme",), "name", DEFAULT_PLASMA_THEME),
            "color_scheme": self.kread(self.kdeglobals, ("General",), "ColorScheme", DEFAULT_COLOR_SCHEME),
            "icon_theme": icon_theme or "breeze",
            "cursor_theme": cursor_theme or "breeze_cursors",
            "font_family": current_font.split(",", 1)[0],
            "accent_color": self.custom_value("accent_color", ACCENT_ORANGE),
            "wallpaper_path": self.default_wallpaper(),
            "window_decoration": self.kread(self.kwinrc, ("org.kde.kdecoration2",), "theme", DEFAULT_WINDOW_DECORATION),
            "crt_effects": self.as_bool(self.custom_value("crt_effects"), True),
            "scanlines": self.as_bool(self.custom_value("scanlines"), True),
            "glow_intensity": int(self.custom_value("glow_intensity", 70)),
        }

    def apply_wallpaper(self, path: str) -> str | None:
        wallpaper = Path(path).expanduser()
        if not wallpaper.is_file():
            return "Wallpaper file was not found."

        tool = self.tools.get("plasma-apply-wallpaperimage")
        if tool:
            result = self._run([tool, str(wallpaper)], capture=True, timeout=30)
            if result is not None and result.returncode == 0:
                return None

        qdbus = self.tools.get("qdbus6")
        if qdbus:
            escaped = str(wallpaper).replace("\\", "\\\\").replace('"', '\\"')
            script = (
                'var allDesktops = desktops();'
                "for (var i = 0; i < allDesktops.length; i++) {"
                '  var desktop = allDesktops[i];'
                '  desktop.wallpaperPlugin = "org.kde.image";'
                '  desktop.currentConfigGroup = ["Wallpaper", "org.kde.image", "General"];'
                f'  desktop.writeConfig("Image", "file://{escaped}");'
                '  desktop.writeConfig("FillMode", 2);'
                "}"
            )
            result = self._run([qdbus, "org.kde.plasmashell", "/PlasmaShell", "org.kde.PlasmaShell.evaluateScript", script], capture=True, timeout=30)
            if result is not None and result.returncode == 0:
                return None

        return "Plasma wallpaper tools were unavailable."

    def reconfigure_kwin(self) -> None:
        qdbus = self.tools.get("qdbus6")
        if qdbus:
            self._run([qdbus, "org.kde.KWin", "/KWin", "reconfigure"], capture=True, timeout=10)

    def refresh_runtime(self) -> None:
        if self.tools.get("kbuildsycoca6"):
            self._run([self.tools["kbuildsycoca6"]], capture=True, timeout=20)
        self.reconfigure_kwin()

    def _wrap_backend_payload(
        self,
        payload: dict[str, Any],
        *,
        backup_path: Path | None = None,
        refresh_runtime: bool = False,
    ) -> ApplyResult:
        if refresh_runtime:
            self.refresh_runtime()
        return ApplyResult(
            bool(payload.get("success", False)),
            str(payload.get("summary", "")),
            details=list(payload.get("details", [])),
            warnings=list(payload.get("warnings", [])),
            requires=list(payload.get("requires", [])),
            backup_path=backup_path,
        )

    def accessibility_state(self) -> dict[str, Any]:
        return accessibility_backend.read_current(self)

    def apply_accessibility(self, values: dict[str, Any]) -> ApplyResult:
        backup = self.backup_files("accessibility", (self.kdeglobals, self.kcminputrc, self.kaccessrc, self.kcmaccessrc))
        payload = accessibility_backend.apply_changes(self, values)
        return self._wrap_backend_payload(
            payload,
            backup_path=backup,
            refresh_runtime=True,
        )

    def bluetooth_state(self) -> dict[str, Any]:
        return bluetooth_backend.read_current(self)

    def apply_bluetooth(self, values: dict[str, Any]) -> ApplyResult:
        backup = self.backup_files("bluetooth", (self.paths.settings_path,))
        payload = bluetooth_backend.apply_changes(self, values)
        return self._wrap_backend_payload(payload, backup_path=backup)

    def bluetooth_connect_device(self, address: str) -> ApplyResult:
        payload = bluetooth_backend.connect_device(self, address)
        return self._wrap_backend_payload(payload)

    def bluetooth_disconnect_device(self, address: str) -> ApplyResult:
        payload = bluetooth_backend.disconnect_device(self, address)
        return self._wrap_backend_payload(payload)

    def bluetooth_pair_device(self, address: str) -> ApplyResult:
        payload = bluetooth_backend.pair_device(self, address)
        return self._wrap_backend_payload(payload)

    def bluetooth_trust_device(self, address: str) -> ApplyResult:
        payload = bluetooth_backend.trust_device(self, address)
        return self._wrap_backend_payload(payload)

    def bluetooth_remove_device(self, address: str) -> ApplyResult:
        payload = bluetooth_backend.remove_device(self, address)
        return self._wrap_backend_payload(payload)

    def online_accounts_state(self) -> dict[str, Any]:
        return accounts_backend.read_current(self)

    def apply_online_accounts(self, values: dict[str, Any]) -> ApplyResult:
        backup = self.backup_files("online-accounts", (self.paths.settings_path,))
        payload = accounts_backend.apply_changes(self, values)
        return self._wrap_backend_payload(payload, backup_path=backup)

    def vpn_state(self) -> dict[str, Any]:
        return vpn_backend.read_current(self)

    def apply_vpn(self, values: dict[str, Any]) -> ApplyResult:
        payload = vpn_backend.apply_changes(self, values)
        return self._wrap_backend_payload(payload)

    def import_vpn(self, file_path: str) -> ApplyResult:
        payload = vpn_backend.import_config(self, file_path)
        return self._wrap_backend_payload(payload)

    def proxy_state(self) -> dict[str, Any]:
        return proxy_backend.read_current(self)

    def apply_proxy(self, values: dict[str, Any]) -> ApplyResult:
        backup = self.backup_files("proxy", (self.kioslaverc,))
        payload = proxy_backend.apply_changes(self, values)
        return self._wrap_backend_payload(payload, backup_path=backup)

    def file_associations_state(self) -> dict[str, Any]:
        return file_associations_backend.read_current(self)

    def search_mime_types(self, query: str) -> list[str]:
        return file_associations_backend.search_mime_types(self, query)

    def current_file_association(self, mime_type: str) -> str:
        return file_associations_backend.current_default(self, mime_type)

    def apply_file_association(self, mime_type: str, desktop_id: str) -> ApplyResult:
        backup = self.backup_files("file-associations", (self.mimeapps,))
        payload = file_associations_backend.apply_changes(self, {"mime_type": mime_type, "desktop_id": desktop_id})
        return self._wrap_backend_payload(payload, backup_path=backup)

    def reset_file_association(self, mime_type: str) -> ApplyResult:
        backup = self.backup_files("file-associations", (self.mimeapps,))
        payload = file_associations_backend.reset_to_system_default(self, mime_type)
        return self._wrap_backend_payload(payload, backup_path=backup)

    def task_switcher_state(self) -> dict[str, Any]:
        return task_switcher_backend.read_current(self)

    def apply_task_switcher(self, values: dict[str, Any]) -> ApplyResult:
        backup = self.backup_files("task-switcher", (self.kwinrc,))
        payload = task_switcher_backend.apply_changes(self, values)
        return self._wrap_backend_payload(payload, backup_path=backup)

    def notifications_state(self, *, ensure_config: bool = True) -> dict[str, Any]:
        return notifications_backend.read_current(self, ensure_config=ensure_config)

    def apply_notifications(self, values: dict[str, Any]) -> ApplyResult:
        backup = notifications_backend.backup_config(self)
        payload = notifications_backend.apply_changes(self, values)
        return self._wrap_backend_payload(payload, backup_path=backup)

    def apply_notifications_preset(self) -> ApplyResult:
        backup = notifications_backend.backup_config(self)
        payload = notifications_backend.apply_kesk_preset(self)
        return self._wrap_backend_payload(payload, backup_path=backup)

    def reload_notifications(self) -> ApplyResult:
        payload = notifications_backend.reload_dunst(self)
        return self._wrap_backend_payload(payload)

    def test_notification(self, *, critical: bool = False) -> ApplyResult:
        payload = notifications_backend.send_test_notification(self, critical=critical)
        return self._wrap_backend_payload(payload)

    def open_notifications_config(self) -> ApplyResult:
        payload = notifications_backend.open_config(self)
        return self._wrap_backend_payload(payload)

    def search_backend_state(self) -> dict[str, Any]:
        return search_backend.read_current(self)

    def apply_search_backend(self, values: dict[str, Any]) -> ApplyResult:
        backup = self.backup_files("search", (self.baloofilerc,))
        payload = search_backend.apply_changes(self, values)
        return self._wrap_backend_payload(payload, backup_path=backup)

    def privacy_state(self) -> dict[str, Any]:
        return privacy_backend.read_current(self)

    def apply_privacy(self, values: dict[str, Any]) -> ApplyResult:
        backup = self.backup_files("privacy", (self.kactivitymanagerdrc, self.baloofilerc, self.paths.settings_path))
        payload = privacy_backend.apply_changes(self, values)
        return self._wrap_backend_payload(payload, backup_path=backup)

    def clear_recent_history(self) -> ApplyResult:
        payload = privacy_backend.clear_recent_history(self)
        return self._wrap_backend_payload(payload)

    def privileged_state(self) -> dict[str, Any]:
        return privileged_backend.read_current(self)

    def apply_appearance(self, values: dict[str, Any]) -> ApplyResult:
        files = (self.kdeglobals, self.kcminputrc, self.kwinrc, self.plasmarc, self.paths.settings_path)
        backup = self.backup_files("appearance", files)
        details: list[str] = []
        warnings: list[str] = []

        look_and_feel = str(values["look_and_feel"])
        color_scheme = str(values["color_scheme"])
        plasma_theme = str(values["plasma_theme"])
        icon_theme = str(values["icon_theme"])
        cursor_theme = str(values["cursor_theme"])
        font_family = str(values["font_family"])
        accent_color = str(values["accent_color"])
        wallpaper = str(values["wallpaper_path"]).strip()
        decoration = str(values["window_decoration"])
        is_kesk_theme = self.is_kesk_look_and_feel(look_and_feel)
        wallpaper_target = wallpaper or (self.official_wallpaper() if is_kesk_theme else "")

        if self.tools.get("lookandfeeltool") and not is_kesk_theme:
            self._run([self.tools["lookandfeeltool"], "-a", look_and_feel], capture=True, timeout=45)
            details.append(f"Applied look and feel package: {look_and_feel}")
        else:
            self.kwrite(self.kdeglobals, ("KDE",), "LookAndFeelPackage", look_and_feel)
            if is_kesk_theme:
                details.append(f"Recorded KeskOS look and feel package without forcing a Plasma layout reset: {look_and_feel}")
            else:
                details.append(f"Recorded look and feel package: {look_and_feel}")

        if self.tools.get("plasma-apply-colorscheme"):
            self._run([self.tools["plasma-apply-colorscheme"], color_scheme], capture=True, timeout=30)
        else:
            self.kwrite(self.kdeglobals, ("General",), "ColorScheme", color_scheme)
        details.append(f"Color scheme set to {color_scheme}")

        if self.tools.get("plasma-apply-desktoptheme"):
            self._run([self.tools["plasma-apply-desktoptheme"], plasma_theme], capture=True, timeout=30)
        else:
            self.kwrite(self.plasmarc, ("Theme",), "name", plasma_theme)
        details.append(f"Plasma style set to {plasma_theme}")

        if self.tools.get("plasma-apply-cursortheme"):
            self._run([self.tools["plasma-apply-cursortheme"], cursor_theme], capture=True, timeout=20)
        else:
            self.kwrite(self.kcminputrc, ("Mouse",), "cursorTheme", cursor_theme)
        details.append(f"Cursor theme set to {cursor_theme}")

        self.kwrite(self.kdeglobals, ("Icons",), "Theme", icon_theme)
        self.kwrite(self.kdeglobals, ("General",), "font", f"{font_family},10,-1,5,50,0,0,0,0,0")
        self.kwrite(self.kdeglobals, ("General",), "fixed", f"{font_family},10,-1,5,50,0,0,0,0,0")
        self.kwrite(self.kdeglobals, ("General",), "smallestReadableFont", f"{font_family},8,-1,5,50,0,0,0,0,0")
        self.kwrite(self.kwinrc, ("org.kde.kdecoration2",), "library", "org.kde.kwin.aurorae")
        self.kwrite(self.kwinrc, ("org.kde.kdecoration2",), "theme", decoration)
        self.kwrite(self.kdeglobals, ("General",), "AccentColor", accent_color)

        if is_kesk_theme and str(self.custom_value("panel_mode", "kesk_panel")) == "kesk_panel":
            reset_panel = self.tools.get("keskos-reset-panel")
            if reset_panel:
                result = self._run([reset_panel], capture=True, timeout=120)
                if result is None or result.returncode != 0:
                    warnings.append("KeskOS panel refresh did not complete cleanly after applying the branded theme.")
                else:
                    details.append("Reapplied the managed KeskOS taskbar after the branded theme update.")
            else:
                warnings.append("keskos-reset-panel was not available, so the taskbar could not be reasserted automatically.")

        if wallpaper_target:
            warning: str | None = None
            wallpaper_helper = self.tools.get("keskos-wallpaper-apply")
            if is_kesk_theme and wallpaper_helper and self.is_official_wallpaper(wallpaper_target):
                result = self._run([wallpaper_helper], capture=True, timeout=60)
                if result is None or result.returncode != 0:
                    warning = "KeskOS wallpaper helper did not complete cleanly."
                else:
                    details.append("Reapplied the official KeskOS wallpaper through the Plasma wallpaper helper.")
            else:
                warning = self.apply_wallpaper(wallpaper_target)
                if warning is None:
                    details.append(f"Wallpaper updated: {wallpaper_target}")
            if warning:
                warnings.append(warning)
        elif is_kesk_theme:
            warnings.append("No official KeskOS wallpaper asset was found, so the background could not be restored automatically.")

        self.set_custom_values(
            {
                "accent_color": accent_color,
                "crt_effects": bool(values["crt_effects"]),
                "scanlines": bool(values["scanlines"]),
                "glow_intensity": int(values["glow_intensity"]),
                "wallpaper_path": wallpaper_target,
            }
        )
        details.extend(
            [
                f"Icon theme set to {icon_theme}",
                f"Primary font set to {font_family}",
                f"Window decoration set to {decoration}",
                f"KeskOS accent stored as {accent_color}",
            ]
        )
        self.refresh_runtime()

        return ApplyResult(
            True,
            "Appearance settings applied.",
            details=details,
            warnings=warnings,
            requires=["Logout may be needed for some theme components."],
            backup_path=backup,
        )

    def apply_kesk_appearance_defaults(self) -> ApplyResult:
        values = self.appearance_state()
        values.update(
            {
                "look_and_feel": DEFAULT_LOOK_AND_FEEL,
                "plasma_theme": DEFAULT_PLASMA_THEME,
                "color_scheme": DEFAULT_COLOR_SCHEME,
                "accent_color": ACCENT_ORANGE,
                "wallpaper_path": self.official_wallpaper(),
                "window_decoration": DEFAULT_WINDOW_DECORATION,
                "crt_effects": True,
                "scanlines": True,
                "glow_intensity": 70,
            }
        )
        return self.apply_appearance(values)

    def apply_kde_appearance_defaults(self) -> ApplyResult:
        values = self.appearance_state()
        values.update(
            {
                "look_and_feel": "org.kde.breezedark.desktop",
                "plasma_theme": "default",
                "color_scheme": "BreezeDark",
                "icon_theme": "breeze",
                "cursor_theme": "breeze_cursors",
                "window_decoration": "org.kde.breeze",
                "crt_effects": False,
                "scanlines": False,
                "glow_intensity": 0,
            }
        )
        return self.apply_appearance(values)

    def desktop_state(self) -> dict[str, Any]:
        count = self.parse_int(self.kread(self.kwinrc, ("Desktops",), "Number", "4"), 4)
        names = []
        for index in range(1, max(count, 1) + 1):
            names.append(self.kread(self.kwinrc, ("Desktops",), f"Name_{index}", str(index)))
        return {
            "wallpaper_path": self.default_wallpaper(),
            "wallpaper_fit": str(self.custom_value("wallpaper_fit", "Fill")),
            "random_wallpaper": self.as_bool(self.custom_value("random_wallpaper"), False),
            "wallpaper_folder": str(self.custom_value("wallpaper_folder", "")),
            "apply_wallpaper_to_lock": self.as_bool(self.custom_value("apply_wallpaper_to_lock"), False),
            "desktop_icons": self.as_bool(self.custom_value("desktop_icons"), True),
            "desktop_toolbox": self.as_bool(self.custom_value("desktop_toolbox"), True),
            "desktop_containment": str(self.custom_value("desktop_containment", "folder_view")),
            "desktop_show_hidden": self.as_bool(self.custom_value("desktop_show_hidden"), False),
            "screen_edge_behavior": str(self.custom_value("screen_edge_behavior", "overview")),
            "desktop_count": count,
            "workspace_names": names,
        }

    def apply_desktop(self, values: dict[str, Any]) -> ApplyResult:
        backup = self.backup_files("desktop", (self.kwinrc, self.paths.settings_path))
        count = max(1, min(int(values["desktop_count"]), 10))
        names = [name.strip() or str(index) for index, name in enumerate(values["workspace_names"], start=1)]
        for index in range(1, count + 1):
            name = names[index - 1] if index - 1 < len(names) else str(index)
            self.kwrite(self.kwinrc, ("Desktops",), f"Name_{index}", name)
        self.kwrite(self.kwinrc, ("Desktops",), "Number", str(count))
        self.kwrite(self.kwinrc, ("Desktops",), "Rows", "1")

        wallpaper = str(values["wallpaper_path"]).strip()
        warnings: list[str] = []
        if wallpaper:
            warning = self.apply_wallpaper(wallpaper)
            if warning:
                warnings.append(warning)

        self.set_custom_values(
            {
                "wallpaper_path": wallpaper,
                "wallpaper_fit": str(values["wallpaper_fit"]),
                "random_wallpaper": bool(values["random_wallpaper"]),
                "wallpaper_folder": str(values["wallpaper_folder"]).strip(),
                "apply_wallpaper_to_lock": bool(values["apply_wallpaper_to_lock"]),
                "desktop_icons": bool(values["desktop_icons"]),
                "desktop_toolbox": bool(values["desktop_toolbox"]),
                "desktop_containment": str(values["desktop_containment"]),
                "desktop_show_hidden": bool(values["desktop_show_hidden"]),
                "screen_edge_behavior": str(values["screen_edge_behavior"]),
            }
        )
        self.refresh_runtime()
        return ApplyResult(
            True,
            "Desktop preferences applied.",
            details=[f"Configured {count} virtual desktop(s).", "Stored desktop visibility and containment preferences."],
            warnings=warnings,
            requires=["Plasma restart may be needed for desktop icon and toolbox changes."],
            backup_path=backup,
        )

    def launcher_mode(self) -> str:
        mode = read_first_line(self.launcher_mode_path) or str(self.custom_value("launcher_style", "keskos"))
        lowered = mode.strip().lower()
        return lowered if lowered in {"keskos", "kde"} else "keskos"

    def detect_launcher_keybind(self) -> str:
        meta_action = self.kread(self.kwinrc, ("ModifierOnlyShortcuts",), "Meta", "")
        launcher_shortcut = self.kread(self.settings_file("kglobalshortcutsrc"), ("plasmashell",), "activate application launcher", "")
        if "Meta+Space" in launcher_shortcut:
            return "Meta+Space"
        if "Meta+Q" in launcher_shortcut:
            return "Meta+Q"
        if meta_action:
            return "Meta"
        return str(self.custom_value("launcher_keybind", "Meta"))

    def panel_state(self) -> dict[str, Any]:
        return {
            "launcher_enabled": self.as_bool(self.custom_value("launcher_enabled"), True),
            "launcher_style": self.launcher_mode(),
            "launcher_keybind": self.detect_launcher_keybind(),
            "panel_mode": str(self.custom_value("panel_mode", "kesk_panel")),
            "top_panel_enabled": self.as_bool(self.custom_value("top_panel_enabled"), True),
            "bottom_panel_enabled": self.as_bool(self.custom_value("bottom_panel_enabled"), True),
            "panel_opacity": int(self.custom_value("panel_opacity", 100)),
            "panel_glow_intensity": int(self.custom_value("panel_glow_intensity", 60)),
            "bottom_panel_autohide": self.as_bool(self.custom_value("bottom_panel_autohide"), False),
            "workspace_switcher": self.as_bool(self.custom_value("workspace_switcher"), True),
            "hud_widgets_enabled": self.as_bool(self.custom_value("hud_widgets_enabled"), True),
            "hud_cpu_widget": self.as_bool(self.custom_value("hud_cpu_widget"), True),
            "hud_memory_widget": self.as_bool(self.custom_value("hud_memory_widget"), True),
            "hud_network_widget": self.as_bool(self.custom_value("hud_network_widget"), True),
            "hud_media_widget": self.as_bool(self.custom_value("hud_media_widget"), True),
            "hud_clock_widget": self.as_bool(self.custom_value("hud_clock_widget"), True),
            "hud_widget_position": str(self.custom_value("hud_widget_position", "top-right")),
            "quickshell_available": bool(self.tools.get("quickshell")),
        }

    def set_launcher_keybind(self, keybind: str, enabled: bool) -> None:
        shortcuts = self.settings_file("kglobalshortcutsrc")
        meta_action = "org.kde.plasmashell,/PlasmaShell,org.kde.PlasmaShell,activateLauncherMenu"
        if not enabled:
            self.kwrite(self.kwinrc, ("ModifierOnlyShortcuts",), "Meta", "")
            self.kwrite(shortcuts, ("plasmashell",), "activate application launcher", "none,none,Activate Application Launcher")
            return
        if keybind == "Meta":
            self.kwrite(self.kwinrc, ("ModifierOnlyShortcuts",), "Meta", meta_action)
            self.kwrite(shortcuts, ("plasmashell",), "activate application launcher", "Alt+F1,Alt+F1,Activate Application Launcher")
        else:
            self.kwrite(self.kwinrc, ("ModifierOnlyShortcuts",), "Meta", "")
            self.kwrite(shortcuts, ("plasmashell",), "activate application launcher", f"{keybind},{keybind},Activate Application Launcher")

    def apply_panels(self, values: dict[str, Any]) -> ApplyResult:
        backup = self.backup_files(
            "panels",
            (self.kwinrc, self.settings_file("kglobalshortcutsrc"), self.launcher_mode_path, self.paths.settings_path),
        )
        details: list[str] = []
        warnings: list[str] = []

        enabled = bool(values["launcher_enabled"])
        launcher_style = str(values["launcher_style"])
        if self.tools.get("keskos-launcher-switch"):
            target_mode = launcher_style if launcher_style in {"keskos", "kde"} else "keskos"
            result = self._run([self.tools["keskos-launcher-switch"], target_mode], capture=True, timeout=90)
            if result is None or result.returncode != 0:
                warnings.append("Could not fully apply the requested launcher mode.")
            else:
                details.append(f"Launcher mode set to {target_mode}.")
        else:
            self.launcher_mode_path.parent.mkdir(parents=True, exist_ok=True)
            self.launcher_mode_path.write_text(f"{launcher_style}\n", encoding="utf-8")
            details.append(f"Stored launcher mode preference: {launcher_style}.")

        self.set_launcher_keybind(str(values["launcher_keybind"]), enabled)
        details.append(f"Launcher shortcut set to {values['launcher_keybind'] if enabled else 'disabled'}.")

        panel_mode = str(values["panel_mode"])
        if panel_mode == "kesk_panel" and self.tools.get("keskos-reset-panel"):
            result = self._run([self.tools["keskos-reset-panel"]], capture=True, timeout=120)
            if result is None or result.returncode != 0:
                warnings.append("KeskOS panel reset did not complete cleanly.")
            else:
                details.append("Reapplied the branded KeskOS Plasma panel.")
        elif panel_mode == "quickshell_hud":
            details.append("Stored Quickshell HUD preference. Log out and back in to switch shells cleanly.")
        else:
            details.append("Stored KDE panel fallback preference.")

        self.set_custom_values(
            {
                "launcher_enabled": enabled,
                "launcher_style": launcher_style,
                "launcher_keybind": str(values["launcher_keybind"]),
                "panel_mode": panel_mode,
                "top_panel_enabled": bool(values["top_panel_enabled"]),
                "bottom_panel_enabled": bool(values["bottom_panel_enabled"]),
                "panel_opacity": int(values["panel_opacity"]),
                "panel_glow_intensity": int(values["panel_glow_intensity"]),
                "bottom_panel_autohide": bool(values["bottom_panel_autohide"]),
                "workspace_switcher": bool(values["workspace_switcher"]),
                "hud_widgets_enabled": bool(values["hud_widgets_enabled"]),
                "hud_cpu_widget": bool(values["hud_cpu_widget"]),
                "hud_memory_widget": bool(values["hud_memory_widget"]),
                "hud_network_widget": bool(values["hud_network_widget"]),
                "hud_media_widget": bool(values["hud_media_widget"]),
                "hud_clock_widget": bool(values["hud_clock_widget"]),
                "hud_widget_position": str(values["hud_widget_position"]),
            }
        )
        self.refresh_runtime()
        return ApplyResult(
            True,
            "Panel and launcher preferences applied.",
            details=details,
            warnings=warnings,
            requires=["Plasma restart may be needed for panel layout changes."],
            backup_path=backup,
        )

    def window_state(self) -> dict[str, Any]:
        buttons_left = self.kread(self.kwinrc, ("org.kde.kdecoration2",), "ButtonsOnLeft", "MS")
        buttons_right = self.kread(self.kwinrc, ("org.kde.kdecoration2",), "ButtonsOnRight", "HIAX")
        titlebar_layout = next((name for name, layout in TITLEBAR_LAYOUTS.items() if layout == (buttons_left, buttons_right)), "Custom")
        return {
            "focus_policy": self.kread(self.kwinrc, ("Windows",), "FocusPolicy", "ClickToFocus"),
            "border_size": self.kread(self.kwinrc, ("org.kde.kdecoration2",), "BorderSize", "Normal"),
            "animation_speed": float(self.kread(self.kdeglobals, ("KDE",), "AnimationDurationFactor", "1.0") or "1.0"),
            "compositor_enabled": self.as_bool(self.kread(self.kwinrc, ("Compositing",), "Enabled", "true"), True),
            "blur_enabled": self.as_bool(self.kread(self.kwinrc, ("Plugins",), "blurEnabled", "true"), True),
            "transparency_enabled": self.as_bool(self.kread(self.kwinrc, ("Plugins",), "translucencyEnabled", "true"), True),
            "snap_enabled": self.as_bool(self.kread(self.kwinrc, ("Windows",), "ElectricBorderTiling", "true"), True),
            "titlebar_layout": titlebar_layout,
        }

    def quick_settings_state(self) -> dict[str, Any]:
        appearance = self.appearance_state()
        windows = self.window_state()
        look_and_feel = str(appearance["look_and_feel"]).lower()
        color_scheme = str(appearance["color_scheme"]).lower()

        if self.is_kesk_look_and_feel(str(appearance["look_and_feel"])):
            theme_preset = "keskos_dark"
        elif "breezedark" in look_and_feel or "breeze dark" in look_and_feel or "dark" in color_scheme:
            theme_preset = "breeze_dark"
        elif "breeze" in look_and_feel or color_scheme.startswith("breeze"):
            theme_preset = "breeze"
        else:
            theme_preset = "automatic"

        return {
            "theme_preset": theme_preset,
            "animation_speed": float(windows["animation_speed"]),
            "single_click": self.as_bool(self.kread(self.kdeglobals, ("KDE",), "SingleClick", "false"), False),
            "accent_color": str(self.custom_value("accent_color", ACCENT_ORANGE)),
        }

    def _theme_values_for_preset(self, preset: str) -> tuple[dict[str, Any] | None, list[str]]:
        warnings: list[str] = []
        current = self.appearance_state()

        if preset == "keskos_dark":
            return None, warnings

        look_and_feel_options = self.look_and_feel_options()
        plasma_options = self.plasma_theme_options()
        color_options = self.color_scheme_options()
        icon_options = self.icon_theme_options()
        cursor_options = self.cursor_theme_options()
        decoration_options = self.window_decoration_options()

        if preset == "breeze_dark":
            look_value = self.find_option_value(look_and_feel_options, "org.kde.breezedark.desktop", "breezedark", "breeze dark", fallback=current["look_and_feel"])
            color_value = self.find_option_value(color_options, "breezedark", "breeze dark", fallback=current["color_scheme"])
        else:
            look_value = self.find_option_value(look_and_feel_options, "org.kde.breeze.desktop", "breeze", fallback=current["look_and_feel"])
            color_value = self.find_option_value(color_options, "breezelight", "breeze light", "breeze", fallback=current["color_scheme"])

        if look_value == current["look_and_feel"]:
            warnings.append(f"Look-and-feel preset for {preset.replace('_', ' ')} was not found exactly; keeping the current package.")
        if color_value == current["color_scheme"]:
            warnings.append(f"Color scheme preset for {preset.replace('_', ' ')} was not found exactly; keeping the current scheme.")

        values = dict(current)
        values.update(
            {
                "look_and_feel": look_value,
                "plasma_theme": self.find_option_value(plasma_options, "default", "breeze", fallback=current["plasma_theme"]),
                "color_scheme": color_value,
                "icon_theme": self.find_option_value(icon_options, "breeze", fallback=current["icon_theme"]),
                "cursor_theme": self.find_option_value(cursor_options, "breeze_cursors", "breeze", fallback=current["cursor_theme"]),
                "window_decoration": self.find_option_value(decoration_options, "org.kde.breeze", "breeze", fallback=current["window_decoration"]),
                "crt_effects": False,
                "scanlines": False,
                "glow_intensity": 0,
            }
        )
        return values, warnings

    def apply_quick_settings(self, values: dict[str, Any]) -> ApplyResult:
        backup = self.backup_files("quick-settings", (self.kdeglobals, self.kwinrc, self.plasmarc, self.paths.settings_path))
        details: list[str] = []
        warnings: list[str] = []
        requires: list[str] = []
        theme_preset = str(values.get("theme_preset", "automatic"))

        if theme_preset == "keskos_dark":
            theme_result = self.apply_kesk_appearance_defaults()
            details.extend(theme_result.details)
            warnings.extend(theme_result.warnings)
            requires.extend(theme_result.requires)
        elif theme_preset in {"breeze", "breeze_dark"}:
            appearance_values, preset_warnings = self._theme_values_for_preset(theme_preset)
            warnings.extend(preset_warnings)
            if appearance_values is not None:
                theme_result = self.apply_appearance(appearance_values)
                details.extend(theme_result.details)
                warnings.extend(theme_result.warnings)
                requires.extend(theme_result.requires)
        else:
            details.append("Automatic theme card selected. Current appearance was kept because scheduled theme switching is not wired yet.")

        self.kwrite(self.kdeglobals, ("KDE",), "AnimationDurationFactor", f"{float(values.get('animation_speed', 1.0)):.2f}")
        details.append(f"Animation speed set to {float(values.get('animation_speed', 1.0)):.2f}x")

        single_click = bool(values.get("single_click", False))
        self.kwrite(self.kdeglobals, ("KDE",), "SingleClick", self.bool_text(single_click))
        details.append("File click behavior set to open items on single click." if single_click else "File click behavior set to select items on single click.")

        self.refresh_runtime()
        summary = "Quick settings applied."
        if theme_preset == "automatic":
            summary = "Quick settings updated. Automatic theme scheduling is still pending."

        return ApplyResult(
            True,
            summary,
            details=details,
            warnings=warnings,
            requires=list(dict.fromkeys(requires)),
            backup_path=backup,
        )

    def apply_windows(self, values: dict[str, Any]) -> ApplyResult:
        backup = self.backup_files("windows", (self.kwinrc, self.kdeglobals))
        self.kwrite(self.kwinrc, ("Windows",), "FocusPolicy", str(values["focus_policy"]))
        self.kwrite(self.kwinrc, ("org.kde.kdecoration2",), "BorderSize", str(values["border_size"]))
        self.kwrite(self.kdeglobals, ("KDE",), "AnimationDurationFactor", f"{float(values['animation_speed']):.2f}")
        self.kwrite(self.kwinrc, ("Compositing",), "Enabled", self.bool_text(bool(values["compositor_enabled"])))
        self.kwrite(self.kwinrc, ("Plugins",), "blurEnabled", self.bool_text(bool(values["blur_enabled"])))
        self.kwrite(self.kwinrc, ("Plugins",), "translucencyEnabled", self.bool_text(bool(values["transparency_enabled"])))
        self.kwrite(self.kwinrc, ("Windows",), "ElectricBorderTiling", self.bool_text(bool(values["snap_enabled"])))

        buttons_left, buttons_right = TITLEBAR_LAYOUTS.get(str(values["titlebar_layout"]), TITLEBAR_LAYOUTS["Breeze"])
        self.kwrite(self.kwinrc, ("org.kde.kdecoration2",), "ButtonsOnLeft", buttons_left)
        self.kwrite(self.kwinrc, ("org.kde.kdecoration2",), "ButtonsOnRight", buttons_right)
        self.reconfigure_kwin()
        return ApplyResult(
            True,
            "Window behavior updated.",
            details=["Focus policy, border size, animation speed, compositor, and titlebar layout were updated."],
            requires=["A few window effects may only refresh after opening a new window."],
            backup_path=backup,
        )

    def input_state(self) -> dict[str, Any]:
        return {
            "keyboard_layout": self.kread(self.kxkbrc, ("Layout",), "LayoutList", "us"),
            "repeat_delay": self.parse_int(self.kread(self.kcminputrc, ("Keyboard",), "RepeatDelay", "600"), 600),
            "repeat_rate": self.parse_int(self.kread(self.kcminputrc, ("Keyboard",), "RepeatRate", "25"), 25),
            "tap_to_click": self.as_bool(self.custom_value("input_tap_to_click"), True),
            "natural_scroll": self.as_bool(self.custom_value("input_natural_scroll"), False),
            "two_finger_scroll": self.as_bool(self.custom_value("input_two_finger_scroll"), True),
            "disable_while_typing": self.as_bool(self.custom_value("input_disable_touchpad_while_typing"), True),
            "acceleration_profile": str(self.custom_value("input_acceleration_profile", "adaptive")),
            "right_click_method": str(self.custom_value("input_right_click_method", "two_finger")),
            "repeat_enabled": self.as_bool(self.custom_value("input_repeat_enabled"), True),
            "numlock_startup": str(self.custom_value("input_numlock_startup", "unchanged")),
            "compose_key": str(self.custom_value("input_compose_key", "Disabled")),
            "mouse_speed": int(self.custom_value("mouse_speed", 50)),
        }

    def apply_input(self, values: dict[str, Any]) -> ApplyResult:
        backup = self.backup_files("input", (self.kxkbrc, self.kcminputrc, self.paths.settings_path))
        self.kwrite(self.kxkbrc, ("Layout",), "LayoutList", str(values["keyboard_layout"]))
        self.kwrite(self.kcminputrc, ("Keyboard",), "RepeatDelay", str(int(values["repeat_delay"])))
        self.kwrite(self.kcminputrc, ("Keyboard",), "RepeatRate", str(int(values["repeat_rate"])))
        self.set_custom_values(
            {
                "input_tap_to_click": bool(values["tap_to_click"]),
                "input_natural_scroll": bool(values["natural_scroll"]),
                "input_two_finger_scroll": bool(values["two_finger_scroll"]),
                "input_disable_touchpad_while_typing": bool(values["disable_while_typing"]),
                "input_acceleration_profile": str(values["acceleration_profile"]),
                "input_right_click_method": str(values["right_click_method"]),
                "input_repeat_enabled": bool(values["repeat_enabled"]),
                "input_numlock_startup": str(values["numlock_startup"]),
                "input_compose_key": str(values["compose_key"]),
                "mouse_speed": int(values["mouse_speed"]),
            }
        )
        return ApplyResult(
            True,
            "Input settings applied.",
            details=["Keyboard layout and repeat settings were written to KDE user config.", "Touchpad, pointer, NumLock, and compose-key preferences were stored for KeskOS integration."],
            requires=["Keyboard layout changes may require logging out on Wayland."],
            backup_path=backup,
        )

    def parse_display_info(self) -> dict[str, Any]:
        info = {
            "session": os.environ.get("XDG_SESSION_TYPE", "unknown"),
            "plasma_version": first_nonempty_line(["plasmashell", "--version"]) if command_exists("plasmashell") else "unavailable",
            "output_summary": "Display detection unavailable",
            "monitor_list": [],
        }
        tool = self.tools.get("kscreen-doctor")
        if tool:
            result = self._run([tool, "-o"], capture=True, timeout=4)
            if result is not None and result.returncode == 0:
                info["output_summary"] = result.stdout.strip() or "No output details were returned."
                monitors: list[str] = []
                for line in result.stdout.splitlines():
                    stripped = line.strip()
                    if stripped.startswith("Output:"):
                        monitors.append(stripped.split("Output:", 1)[1].strip())
                info["monitor_list"] = monitors
        return info

    def display_state(self) -> dict[str, Any]:
        data = display_backend.read_current(self)
        data["night_color"] = self.as_bool(self.custom_value("display_night_color"), False)
        data["scale_percent"] = int(self.custom_value("display_scale_percent", data.get("scale_percent", 100)))
        data["refresh_rate"] = int(self.custom_value("display_refresh_rate", data.get("refresh_rate", 60)))
        data["orientation"] = str(self.custom_value("display_orientation", data.get("orientation", "Normal")))
        data["brightness"] = int(self.custom_value("display_brightness", data.get("brightness", 100)))
        data["resolution"] = str(self.custom_value("display_resolution", data.get("resolution", "Automatic")))
        return data

    def apply_display(self, values: dict[str, Any]) -> ApplyResult:
        backup = self.backup_files("display", (self.kwinrc, self.paths.settings_path))
        payload = display_backend.apply_changes(self, values)
        self.set_custom_values(
            {
                "display_night_color": bool(values["night_color"]),
                "display_scale_percent": int(values["scale_percent"]),
                "display_refresh_rate": int(values["refresh_rate"]),
                "display_orientation": str(values["orientation"]),
                "display_brightness": int(values["brightness"]),
                "display_resolution": str(values["resolution"]),
            }
        )
        return self._wrap_backend_payload(payload, backup_path=backup, refresh_runtime=True)

    def _parse_wpctl_volume(self, target: str) -> tuple[int, bool]:
        tool = self.tools.get("wpctl")
        if not tool:
            return 50, False
        result = self._run([tool, "get-volume", target], capture=True, timeout=10)
        if result is None or result.returncode != 0:
            return 50, False
        text = result.stdout.strip()
        match = re.search(r"([0-9]*\.[0-9]+|[0-9]+)", text)
        volume = 50
        if match:
            volume = max(0, min(int(float(match.group(1)) * 100), 150))
        return volume, "[MUTED]" in text

    def _pactl_short(self, category: str) -> list[str]:
        tool = self.tools.get("pactl")
        if not tool:
            return []
        result = self._run([tool, "list", "short", category], capture=True, timeout=10)
        if result is None or result.returncode != 0:
            return []
        rows: list[str] = []
        for line in result.stdout.splitlines():
            parts = line.split("\t")
            if len(parts) >= 2:
                rows.append(parts[1].strip())
        return rows

    def sound_state(self) -> dict[str, Any]:
        state = audio_backend.read_current(self)
        state["audio_profile"] = str(self.custom_value("sound_audio_profile", "Stereo"))
        return state

    def apply_sound(self, values: dict[str, Any]) -> ApplyResult:
        backup = self.backup_files("sound", (self.paths.settings_path,))
        self.set_custom_values({"sound_audio_profile": str(values["audio_profile"])})
        payload = audio_backend.apply_changes(self, values)
        return self._wrap_backend_payload(payload, backup_path=backup)

    def network_state(self) -> dict[str, Any]:
        wifi_enabled = None
        current_network = "unavailable"
        available_networks: list[str] = []
        ethernet_status = "unknown"
        tool = self.tools.get("nmcli")
        if tool:
            result = self._run([tool, "radio", "wifi"], capture=True, timeout=10)
            if result is not None and result.returncode == 0:
                wifi_enabled = result.stdout.strip().lower() == "enabled"
            result = self._run([tool, "-t", "-f", "ACTIVE,SSID", "dev", "wifi"], capture=True, timeout=10)
            if result is not None:
                for line in result.stdout.splitlines():
                    if line.startswith("yes:"):
                        current_network = line.split(":", 1)[1].strip() or "hidden network"
                        break
            result = self._run([tool, "-t", "-f", "SSID", "dev", "wifi"], capture=True, timeout=10)
            if result is not None:
                available_networks = [line.strip() for line in result.stdout.splitlines() if line.strip()]
            result = self._run([tool, "-t", "-f", "DEVICE,TYPE,STATE", "dev"], capture=True, timeout=10)
            if result is not None:
                for line in result.stdout.splitlines():
                    parts = line.split(":")
                    if len(parts) >= 3 and parts[1] == "ethernet":
                        ethernet_status = parts[2]
                        break
        return {
            "wifi_enabled": wifi_enabled,
            "current_network": current_network,
            "available_networks": available_networks,
            "ethernet_status": ethernet_status,
            "metered": self.as_bool(self.custom_value("network_metered"), False),
            "hostname": socket.gethostname(),
        }

    def run_pkexec(self, command: Sequence[str]) -> bool:
        tool = self.tools.get("pkexec")
        if not tool:
            return False
        result = self._run([tool, *command], capture=True, timeout=60)
        return result is not None and result.returncode == 0

    def apply_network(self, values: dict[str, Any]) -> ApplyResult:
        details: list[str] = []
        warnings: list[str] = []
        tool = self.tools.get("nmcli")
        if tool and values["wifi_enabled"] is not None:
            self._run([tool, "radio", "wifi", "on" if values["wifi_enabled"] else "off"], capture=True, timeout=15)
            details.append(f"Wi-Fi radio set to {'enabled' if values['wifi_enabled'] else 'disabled'}.")
        elif values["wifi_enabled"] is not None:
            warnings.append("nmcli was not available, so Wi-Fi could not be changed.")

        requested_hostname = str(values["hostname"]).strip()
        if requested_hostname and requested_hostname != socket.gethostname():
            if self.tools.get("hostnamectl") and self.run_pkexec([self.tools["hostnamectl"], "set-hostname", requested_hostname]):
                details.append(f"Hostname changed to {requested_hostname}.")
            else:
                warnings.append("Hostname change requires pkexec and hostnamectl.")

        self.set_custom_values({"network_metered": bool(values.get("metered", False))})
        return ApplyResult(True, "Network settings updated.", details=details, warnings=warnings, requires=["System hostname changes affect new sessions immediately."])

    def power_state(self) -> dict[str, Any]:
        profile = "balanced"
        tool = self.tools.get("powerprofilesctl")
        if tool:
            result = self._run([tool, "get"], capture=True, timeout=10)
            if result is not None and result.returncode == 0:
                profile = result.stdout.strip() or profile
        return {
            "profile": profile,
            "blank_timeout": int(self.custom_value("power_blank_timeout", 10)),
            "sleep_timeout": int(self.custom_value("power_sleep_timeout", 30)),
            "show_battery_percent": self.as_bool(self.custom_value("power_show_battery_percent"), True),
            "lid_action": str(self.custom_value("power_lid_action", "sleep")),
            "dim_screen": self.as_bool(self.custom_value("power_dim_screen"), True),
            "low_battery_action": str(self.custom_value("power_low_battery_action", "suspend")),
        }

    def apply_power(self, values: dict[str, Any]) -> ApplyResult:
        details: list[str] = []
        warnings: list[str] = []
        tool = self.tools.get("powerprofilesctl")
        if tool:
            result = self._run([tool, "set", str(values["profile"])], capture=True, timeout=10)
            if result is not None and result.returncode == 0:
                details.append(f"Power profile set to {values['profile']}.")
            else:
                warnings.append("The requested power profile could not be applied.")
        else:
            warnings.append("powerprofilesctl is not available on this system.")

        self.set_custom_values(
            {
                "power_blank_timeout": int(values["blank_timeout"]),
                "power_sleep_timeout": int(values["sleep_timeout"]),
                "power_show_battery_percent": bool(values["show_battery_percent"]),
                "power_lid_action": str(values["lid_action"]),
                "power_dim_screen": bool(values["dim_screen"]),
                "power_low_battery_action": str(values["low_battery_action"]),
            }
        )
        return ApplyResult(
            True,
            "Power settings saved.",
            details=details + ["Stored screen blank, sleep, and battery display preferences for KeskOS."],
            warnings=warnings,
        )

    def user_state(self) -> dict[str, Any]:
        current_user = getpass.getuser()
        if pwd is not None:
            pw_entry = pwd.getpwnam(current_user)
            gecos_name = pw_entry.pw_gecos.split(",", 1)[0] if pw_entry.pw_gecos else current_user
        else:
            gecos_name = current_user
        display_name = str(self.custom_value("user_display_name") or gecos_name)
        avatar_candidates = (
            self.paths.home / ".face.icon",
            Path("/var/lib/AccountsService/icons") / current_user,
        )
        avatar = next((str(path) for path in avatar_candidates if path.exists()), "")
        autologin = False
        for config_path in (Path("/etc/sddm.conf"), *Path("/etc/sddm.conf.d").glob("*.conf")):
            if not config_path.exists():
                continue
            parser = configparser.ConfigParser(interpolation=None)
            parser.optionxform = str
            parser.read(config_path, encoding="utf-8")
            if parser.get("Autologin", "User", fallback="") == current_user:
                autologin = True
                break
        return {
            "username": current_user,
            "display_name": display_name,
            "avatar_path": avatar,
            "autologin": autologin,
            "account_type": "Administrator" if os.geteuid() == 0 or current_user == "root" else "Standard user",
        }

    def apply_user(self, values: dict[str, Any]) -> ApplyResult:
        backup = self.backup_files("users", (self.paths.settings_path, self.paths.home / ".face.icon"))
        details: list[str] = []
        avatar = str(values["avatar_path"]).strip()
        if avatar and Path(avatar).is_file():
            shutil.copy2(Path(avatar), self.paths.home / ".face.icon")
            details.append("Updated the user avatar at ~/.face.icon.")
        self.set_custom_values({"user_display_name": str(values["display_name"]).strip()})
        details.append("Stored the KeskOS display name preference.")
        return ApplyResult(True, "User settings saved.", details=details, backup_path=backup)

    def installed_desktop_ids(self) -> set[str]:
        roots = (Path("/usr/share/applications"), self.paths.home / ".local" / "share" / "applications")
        found: set[str] = set()
        for root in roots:
            if not root.is_dir():
                continue
            for child in root.glob("*.desktop"):
                found.add(child.name)
        return found

    def available_desktop_options(self, choices: Sequence[tuple[str, str]], fallback_value: str = "") -> list[SelectOption]:
        installed = self.installed_desktop_ids()
        options = [SelectOption(value, label) for value, label in choices if value in installed]
        if fallback_value and not any(option.value == fallback_value for option in options):
            options.insert(0, SelectOption(fallback_value, fallback_value))
        return options

    def available_terminal_options(self) -> list[SelectOption]:
        installed = self.installed_desktop_ids()
        return [SelectOption(value, label) for value, label, _command in TERMINAL_OPTIONS if value in installed]

    def mime_default(self, mime: str) -> str:
        parser = configparser.ConfigParser(interpolation=None)
        parser.optionxform = str
        if self.mimeapps.is_file():
            parser.read(self.mimeapps, encoding="utf-8")
        return parser.get("Default Applications", mime, fallback="")

    def write_mime_defaults(self, mappings: dict[str, str]) -> None:
        parser = configparser.ConfigParser(interpolation=None)
        parser.optionxform = str
        if self.mimeapps.exists():
            parser.read(self.mimeapps, encoding="utf-8")
        if not parser.has_section("Default Applications"):
            parser.add_section("Default Applications")
        for mime, desktop_id in mappings.items():
            parser.set("Default Applications", mime, desktop_id)
        self.mimeapps.parent.mkdir(parents=True, exist_ok=True)
        with self.mimeapps.open("w", encoding="utf-8") as handle:
            parser.write(handle)

    def default_browser_id(self) -> str:
        if command_exists("xdg-settings"):
            result = self._run(["xdg-settings", "get", "default-web-browser"], capture=True, timeout=10)
            if result is not None and result.returncode == 0:
                browser = result.stdout.strip()
                if browser:
                    return browser
        return self.mime_default("x-scheme-handler/https") or str(self.custom_value("default_browser_preference", "librewolf.desktop"))

    def default_apps_state(self) -> dict[str, Any]:
        terminal = self.kread(self.kdeglobals, ("General",), "TerminalApplication", "konsole")
        reverse_terminal = next((desktop_id for desktop_id, _label, command in TERMINAL_OPTIONS if command == terminal), "konsole.desktop")
        return {
            "browser": self.default_browser_id(),
            "terminal": reverse_terminal,
            "file_manager": self.mime_default("inode/directory") or "org.kde.dolphin.desktop",
            "text_editor": self.mime_default("text/plain") or "org.kde.kate.desktop",
            "image_viewer": self.mime_default("image/png") or "org.kde.gwenview.desktop",
            "video_player": str(self.custom_value("default_video_player_preference", "")),
            "music_player": str(self.custom_value("default_music_player_preference", "")),
            "mail_app": str(self.custom_value("default_mail_preference", "")),
            "browser_homepage_enabled": self.as_bool(self.custom_value("browser_homepage_enabled"), True),
            "browser_theme_enabled": self.as_bool(self.custom_value("browser_theme_enabled"), False),
        }

    def apply_default_apps(self, values: dict[str, Any]) -> ApplyResult:
        backup = self.backup_files("defaults", (self.mimeapps, self.kdeglobals))
        browser = str(values["browser"])
        if browser:
            if command_exists("xdg-settings"):
                self._run(["xdg-settings", "set", "default-web-browser", browser], capture=True, timeout=10)
            if command_exists("xdg-mime"):
                for mime in ("x-scheme-handler/http", "x-scheme-handler/https", "text/html", "application/xhtml+xml"):
                    self._run(["xdg-mime", "default", browser, mime], capture=True, timeout=10)

        self.write_mime_defaults(
            {
                "x-scheme-handler/http": browser,
                "x-scheme-handler/https": browser,
                "text/html": browser,
                "application/xhtml+xml": browser,
                "inode/directory": str(values["file_manager"]),
                "text/plain": str(values["text_editor"]),
                "image/png": str(values["image_viewer"]),
                "image/jpeg": str(values["image_viewer"]),
            }
        )
        terminal_command = next((command for desktop_id, _label, command in TERMINAL_OPTIONS if desktop_id == values["terminal"]), "konsole")
        self.kwrite(self.kdeglobals, ("General",), "TerminalApplication", terminal_command)
        self.set_custom_values(
            {
                "default_browser_preference": browser,
                "default_video_player_preference": str(values.get("video_player", "")),
                "default_music_player_preference": str(values.get("music_player", "")),
                "default_mail_preference": str(values.get("mail_app", "")),
                "browser_homepage_enabled": bool(values.get("browser_homepage_enabled", True)),
                "browser_theme_enabled": bool(values.get("browser_theme_enabled", False)),
            }
        )
        return ApplyResult(
            True,
            "Default applications updated.",
            details=["Updated xdg-settings, xdg-mime, mimeapps.list, and the KDE terminal preference.", "Stored browser homepage and extra media/mail preferences for KeskOS integration."],
            backup_path=backup,
        )

    def updates_state(self) -> dict[str, Any]:
        return {
            "notifications": self.as_bool(self.custom_value("update_notifications"), True),
            "auto_check": self.as_bool(self.custom_value("update_auto_check"), True),
            "interval": int(self.custom_value("update_check_interval", 24)),
            "include_aur": self.as_bool(self.custom_value("update_include_aur"), True),
            "include_flatpak": self.as_bool(self.custom_value("update_include_flatpak"), True),
            "include_firmware": self.as_bool(self.custom_value("update_include_firmware"), True),
        }

    def apply_updates(self, values: dict[str, Any]) -> ApplyResult:
        backup = self.backup_files("updates", (self.paths.settings_path,))
        self.set_custom_values(
            {
                "update_notifications": bool(values["notifications"]),
                "update_auto_check": bool(values["auto_check"]),
                "update_check_interval": int(values["interval"]),
                "update_include_aur": bool(values["include_aur"]),
                "update_include_flatpak": bool(values["include_flatpak"]),
                "update_include_firmware": bool(values["include_firmware"]),
            }
        )
        return ApplyResult(True, "Update preferences saved.", details=["Stored Kesk Upgrade notification and source preferences."], backup_path=backup)

    def boot_state(self) -> dict[str, Any]:
        return boot_login_backend.read_current(self)

    def apply_boot(self, values: dict[str, Any]) -> ApplyResult:
        backup = self.backup_files("boot", (self.paths.settings_path,))
        payload = boot_login_backend.apply_changes(self, values)
        return self._wrap_backend_payload(payload, backup_path=backup)

    def prompt_style(self) -> str:
        if self.prompt_overlay_path.is_file():
            text = self.prompt_overlay_path.read_text(encoding="utf-8", errors="replace")
            if "keskos ::" in text:
                return "keskos"
        return str(self.custom_value("prompt_style", "keskos"))

    def write_prompt_style(self, style: str) -> None:
        self.prompt_overlay_path.parent.mkdir(parents=True, exist_ok=True)
        if style == "minimal":
            content = (
                "# KeskOS Bash prompt overlay\n\n"
                "if [[ -r /etc/bash.bashrc ]]; then\n"
                "  . /etc/bash.bashrc\n"
                "fi\n\n"
                "if [[ -r \"$HOME/.bashrc\" ]]; then\n"
                "  . \"$HOME/.bashrc\"\n"
                "fi\n\n"
                "PS1='\\u@\\h:\\W\\\\$ '\n"
            )
        else:
            content = (
                "# KeskOS Bash prompt overlay\n\n"
                "if [[ -r /etc/bash.bashrc ]]; then\n"
                "  . /etc/bash.bashrc\n"
                "fi\n\n"
                "if [[ -r \"$HOME/.bashrc\" ]]; then\n"
                "  . \"$HOME/.bashrc\"\n"
                "fi\n\n"
                "export HOSTNAME=\"keskos\"\n"
                "PS1='\\[\\e[38;2;206;106;53m\\]keskos :: \\W > \\[\\e[0m\\]'\n"
            )
        self.prompt_overlay_path.write_text(content, encoding="utf-8")

    def _apply_firefox_homepage(self, root_dir: Path) -> str:
        theme_root = Path("/usr/share/keskos/first-run/browser-theme")
        startpage = "file:///usr/share/keskos/startpage/index.html"
        if not root_dir.exists():
            return "Browser profile directory is not present yet."
        profiles = []
        profiles_ini = root_dir / "profiles.ini"
        if profiles_ini.is_file():
            current_path = ""
            relative = True
            for line in profiles_ini.read_text(encoding="utf-8", errors="replace").splitlines():
                if line.startswith("Path="):
                    current_path = line.split("=", 1)[1].strip()
                elif line.startswith("IsRelative="):
                    relative = line.split("=", 1)[1].strip() != "0"
                elif line.startswith("[") and current_path:
                    profile = root_dir / current_path if relative else Path(current_path)
                    if profile.is_dir():
                        profiles.append(profile)
                    current_path = ""
            if current_path:
                profile = root_dir / current_path if relative else Path(current_path)
                if profile.is_dir():
                    profiles.append(profile)
        if not profiles:
            profiles = [path for path in root_dir.glob("*.default*") if path.is_dir()]
        if not profiles:
            return "Browser profile has not been created yet."
        for profile in profiles:
            chrome_dir = profile / "chrome"
            chrome_dir.mkdir(parents=True, exist_ok=True)
            for source, target in (("firefox-userChrome.css", "userChrome.css"), ("firefox-userContent.css", "userContent.css")):
                source_path = theme_root / source
                if source_path.is_file():
                    shutil.copy2(source_path, chrome_dir / target)
            user_js = profile / "user.js"
            user_js.write_text(
                "\n".join(
                    [
                        'user_pref("toolkit.legacyUserProfileCustomizations.stylesheets", true);',
                        f'user_pref("browser.startup.homepage", "{startpage}");',
                        'user_pref("browser.startup.page", 1);',
                        'user_pref("browser.newtabpage.enabled", false);',
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
        return f"Updated {len(profiles)} Firefox-family profile(s)."

    def _apply_brave_homepage(self) -> str:
        startpage = "file:///usr/share/keskos/startpage/index.html"
        preferences_path = self.paths.home / ".config" / "BraveSoftware" / "Brave-Browser" / "Default" / "Preferences"
        if not preferences_path.is_file():
            return "Brave profile data is not available yet."
        payload = json.loads(preferences_path.read_text(encoding="utf-8"))
        payload["homepage"] = startpage
        payload["homepage_is_newtabpage"] = False
        payload.setdefault("browser", {})["show_home_button"] = True
        payload.setdefault("session", {})["restore_on_startup"] = 4
        payload["session"]["startup_urls"] = [startpage]
        preferences_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        return "Updated Brave startup and homepage settings."

    def apply_browser_homepage_theme(self, browser_desktop_id: str) -> str:
        desktop_id = browser_desktop_id.lower()
        if "librewolf" in desktop_id:
            return self._apply_firefox_homepage(self.paths.home / ".librewolf")
        if "zen" in desktop_id:
            return self._apply_firefox_homepage(self.paths.home / ".zen")
        if "firefox" in desktop_id:
            return self._apply_firefox_homepage(self.paths.home / ".mozilla" / "firefox")
        if "brave" in desktop_id:
            return self._apply_brave_homepage()
        return "The selected browser does not have a KeskOS homepage handler yet."

    def kesk_state(self) -> dict[str, Any]:
        return {
            "accent_color": str(self.custom_value("accent_color", ACCENT_ORANGE)),
            "kesk_theme_mode": str(self.custom_value("kesk_theme_mode", "full")),
            "crt_effects": self.as_bool(self.custom_value("crt_effects"), True),
            "scanlines": self.as_bool(self.custom_value("scanlines"), True),
            "glow_intensity": int(self.custom_value("glow_intensity", 70)),
            "terminal_font": str(self.custom_value("terminal_font", "JetBrains Mono")),
            "prompt_style": self.prompt_style(),
            "browser_homepage_enabled": self.as_bool(self.custom_value("browser_homepage_enabled"), True),
            "first_run_completed": FIRST_RUN_STATE_FILE.exists(),
            "telemetry_enabled": self.as_bool(self.custom_value("telemetry_enabled"), False),
            "local_analytics_dashboard": self.as_bool(self.custom_value("local_analytics_dashboard"), False),
            "experimental_features": self.as_bool(self.custom_value("experimental_features"), False),
            "quickshell_experimental_mode": self.as_bool(self.custom_value("quickshell_experimental_mode"), False),
            "new_launcher_backend": self.as_bool(self.custom_value("new_launcher_backend"), False),
            "new_settings_backend": self.as_bool(self.custom_value("new_settings_backend"), False),
            "debug_ui_overlays": self.as_bool(self.custom_value("debug_ui_overlays"), False),
        }

    def apply_kesk(self, values: dict[str, Any], default_browser: str) -> ApplyResult:
        backup = self.backup_files("keskos", (self.paths.settings_path, self.prompt_overlay_path, FIRST_RUN_STATE_FILE))
        details: list[str] = []
        self.set_custom_values(
            {
                "accent_color": str(values["accent_color"]),
                "kesk_theme_mode": str(values.get("kesk_theme_mode", "full")),
                "crt_effects": bool(values["crt_effects"]),
                "scanlines": bool(values["scanlines"]),
                "glow_intensity": int(values.get("glow_intensity", 70)),
                "terminal_font": str(values.get("terminal_font", "JetBrains Mono")),
                "prompt_style": str(values["prompt_style"]),
                "browser_homepage_enabled": bool(values["browser_homepage_enabled"]),
                "telemetry_enabled": bool(values["telemetry_enabled"]),
                "local_analytics_dashboard": bool(values["local_analytics_dashboard"]),
                "experimental_features": bool(values["experimental_features"]),
                "quickshell_experimental_mode": bool(values.get("quickshell_experimental_mode", False)),
                "new_launcher_backend": bool(values.get("new_launcher_backend", False)),
                "new_settings_backend": bool(values.get("new_settings_backend", False)),
                "debug_ui_overlays": bool(values.get("debug_ui_overlays", False)),
            }
        )
        self.write_prompt_style(str(values["prompt_style"]))
        details.append(f"Prompt style updated to {values['prompt_style']}.")
        if bool(values["browser_homepage_enabled"]):
            details.append(self.apply_browser_homepage_theme(default_browser))
        if bool(values["first_run_completed"]):
            FIRST_RUN_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
            if not FIRST_RUN_STATE_FILE.exists():
                FIRST_RUN_STATE_FILE.write_text(json.dumps({"reason": "settings-app", "completed_at": datetime.now().isoformat()}, indent=2) + "\n", encoding="utf-8")
        elif FIRST_RUN_STATE_FILE.exists():
            FIRST_RUN_STATE_FILE.unlink()
            details.append("First-boot welcome state reset.")
        return ApplyResult(True, "KeskOS preferences applied.", details=details, backup_path=backup)

    def about_rows(self) -> list[tuple[str, str]]:
        version_name, build_id = collect_release_info(self.paths.root)
        desktop_session = os.environ.get("DESKTOP_SESSION", "unavailable")
        current_desktop = os.environ.get("XDG_CURRENT_DESKTOP", "unavailable")
        session_type = os.environ.get("XDG_SESSION_TYPE", "unavailable")
        current_shell = os.environ.get("SHELL", "unavailable")
        plasma_version = first_nonempty_line(["plasmashell", "--version"]) if command_exists("plasmashell") else "unavailable"
        frameworks_version = detect_frameworks_version()
        qt_version = detect_qt_version()
        kernel = first_nonempty_line(["uname", "-r"])
        return [
            ("KeskOS version", version_name),
            ("Build layer", build_id),
            ("Base distro", "Arch Linux"),
            ("Desktop", current_desktop),
            ("Desktop session", desktop_session),
            ("Graphics platform", session_type),
            ("Plasma version", plasma_version),
            ("KDE Frameworks version", frameworks_version),
            ("Qt version", qt_version),
            ("Kernel", kernel),
            ("CPU", detect_cpu_model()),
            ("GPU", detect_gpu_model()),
            ("RAM", detect_total_ram()),
            ("Root disk", detect_root_disk()),
            ("Active user", getpass.getuser()),
            ("Hostname", socket.gethostname()),
            ("Uptime", detect_uptime()),
            ("Package count", detect_package_count()),
            ("Current shell", current_shell),
            ("Website", DOC_LINKS[1][1]),
            ("Docs", DOC_LINKS[0][1]),
            ("GitHub", DOC_LINKS[3][1]),
            ("Versioned toolset", f"kesk {APP_VERSION}"),
        ]

    def tool_command(self, tool_name: str, *extra_args: str) -> list[str]:
        if self.paths.router_path.is_file():
            return python_command(self.paths.router_path, tool_name, *extra_args)
        return ["kesk", tool_name, *extra_args]

    def open_kcm(self, module: str) -> tuple[bool, str]:
        if self.tools.get("systemsettings"):
            command = [self.tools["systemsettings"], module]
        elif self.tools.get("kcmshell6"):
            command = [self.tools["kcmshell6"], module]
        else:
            return False, "systemsettings and kcmshell6 were not found."
        self._log_command(command)
        try:
            subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL, start_new_session=True)
        except OSError as exc:
            self.logger.log(f"kcm_launch_failed={exc!r}")
            return False, str(exc)
        return True, module

    def dry_run_report(self) -> dict[str, Any]:
        config_paths = {
            "kdeglobals": self.kdeglobals,
            "kwinrc": self.kwinrc,
            "plasmarc": self.plasmarc,
            "kcminputrc": self.kcminputrc,
            "kxkbrc": self.kxkbrc,
            "mimeapps": self.mimeapps,
            "baloofilerc": self.baloofilerc,
            "kioslaverc": self.kioslaverc,
            "dunstrc": notifications_backend.get_config_path(self),
            "kesk_settings": self.paths.settings_path,
            "backups_dir": self.paths.backups_dir,
            "privileged_helper": privileged_backend.helper_path(self),
        }
        writable = {name: path.parent.exists() and os.access(path.parent, os.W_OK) for name, path in config_paths.items()}
        plasma_desktop = os.environ.get("XDG_CURRENT_DESKTOP", "")
        accessibility_state = self.accessibility_state()
        bluetooth_state = self.bluetooth_state()
        online_accounts_state = self.online_accounts_state()
        vpn_state = self.vpn_state()
        proxy_state = self.proxy_state()
        file_associations_state = self.file_associations_state()
        task_switcher_state = self.task_switcher_state()
        notifications_state = notifications_backend.read_current(self, ensure_config=False)
        search_state = self.search_backend_state()
        privacy_state = self.privacy_state()
        audio_state = self.sound_state()
        display_state = self.display_state()
        boot_state = self.boot_state()
        backend_states = {
            "accessibility": accessibility_state["status"],
            "bluetooth": bluetooth_state["status"],
            "online_accounts": online_accounts_state["status"],
            "vpn": vpn_state["status"],
            "proxy": proxy_state["status"],
            "file_associations": file_associations_state["status"],
            "task_switcher": task_switcher_state["status"],
            "notifications": notifications_state["status"],
            "search": search_state["status"],
            "privacy": privacy_state["status"],
            "audio": audio_state["status"],
            "display": display_state["status"],
            "boot_login": boot_state["status"],
        }
        return {
            "session_type": os.environ.get("XDG_SESSION_TYPE", "unknown"),
            "display": os.environ.get("DISPLAY", ""),
            "wayland_display": os.environ.get("WAYLAND_DISPLAY", ""),
            "plasma_session_detected": "plasma" in plasma_desktop.lower() or "kde" in plasma_desktop.lower(),
            "graphical_session_available": bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")),
            "plasma_version": first_nonempty_line(["plasmashell", "--version"]) if command_exists("plasmashell") else "unavailable",
            "qt_version": detect_qt_version(),
            "tools": {name: bool(path) for name, path in self.tools.items()},
            "config_paths": {name: str(path) for name, path in config_paths.items()},
            "writable": writable,
            "policy_present": privileged_backend.policy_path(self).is_file(),
            "notifications_runtime": {
                "runtime_notifier": str(notifications_state["runtime_notifier"]),
                "dunst_found": bool(notifications_state["dunst_available"]),
                "dunstctl_found": bool(notifications_state["dunstctl_available"]),
                "notify_send_found": bool(notifications_state["notify_send_available"]),
                "running": bool(notifications_state["dunst_running"]),
                "possible_duplicate_risk": bool(notifications_state.get("duplicate_notification_risk")),
                "config_path": str(notifications_state["config_path"]),
                "config_writable": bool(notifications_state["config_writable"]),
                "do_not_disturb": notifications_state["do_not_disturb"] if notifications_state["dnd_supported"] else "unavailable",
                "dnd_supported": bool(notifications_state["dnd_supported"]),
            },
            "backend_statuses": {
                name: {
                    "code": status.code,
                    "summary": status.summary,
                    "missing_tools": list(status.missing_tools),
                    "admin_required": status.admin_required,
                }
                for name, status in backend_states.items()
            },
            "limitations_matrix": {
                "notifications": {
                    "runtime_notifier": str(notifications_state["runtime_notifier"]).lower(),
                    "dunst_found": bool(notifications_state["dunst_available"]),
                    "dunstctl_found": bool(notifications_state["dunstctl_available"]),
                    "notify_send_found": bool(notifications_state["notify_send_available"]),
                    "dunst_running": bool(notifications_state["dunst_running"]),
                    "possible_plasma_duplicate_risk": bool(notifications_state.get("duplicate_notification_risk")),
                    "per_app_rules": "KDE handoff",
                },
                "accessibility": {
                    "direct_backend": "limited",
                    "advanced_controls": "KDE handoff",
                },
                "online_accounts": {
                    "backend": "KDE handoff",
                },
                "task_switcher": {
                    "backend": "KDE handoff",
                },
                "display": {
                    "backend": "KDE handoff only",
                    "reason": str(display_state.get("handoff_reason", "avoid black-screen risk")),
                },
                "boot_login": {
                    "pkexec_found": bool(boot_state.get("pkexec_found")),
                    "helper_found": bool(boot_state.get("helper_found")),
                    "sddm_assets_found": bool(boot_state.get("sddm_assets_found")),
                    "plymouth_found": bool(boot_state.get("plymouth_found")),
                    "bootloader_detected": str(boot_state.get("bootloader_detected", "unknown")),
                },
            },
        }
