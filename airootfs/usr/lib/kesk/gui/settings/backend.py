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
from typing import Any, Iterable, Sequence

try:
    import pwd
except ImportError:  # pragma: no cover - non-POSIX fallback for smoke tests
    pwd = None

from common import APP_VERSION, SessionLogger, shell_join


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
    "crt_effects": True,
    "scanlines": True,
    "glow_intensity": 70,
    "wallpaper_path": "",
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
    "input_tap_to_click": True,
    "input_natural_scroll": False,
    "mouse_speed": 50,
    "display_night_color": False,
    "power_blank_timeout": 10,
    "power_sleep_timeout": 30,
    "power_show_battery_percent": True,
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
    "login_background": "",
    "default_browser_preference": "librewolf.desktop",
    "browser_homepage_enabled": True,
    "telemetry_enabled": False,
    "local_analytics_dashboard": False,
    "experimental_features": False,
    "prompt_style": "keskos",
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

    logs_dir = home / ".local" / "state" / "kesk" / "logs"
    backups_dir = home / ".local" / "state" / "kesk" / "settings-backups"
    config_dir = home / ".config" / "kesk"
    settings_path = config_dir / "settings.json"
    ui_state_path = config_dir / "settings-gui.ini"

    logs_dir.mkdir(parents=True, exist_ok=True)
    backups_dir.mkdir(parents=True, exist_ok=True)
    config_dir.mkdir(parents=True, exist_ok=True)

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
            "nmcli",
            "powerprofilesctl",
            "hostnamectl",
            "pkexec",
            "keskos-launcher-switch",
            "keskos-reset-panel",
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
    def launcher_mode_path(self) -> Path:
        return self.paths.home / ".config" / "keskos" / "launcher-mode"

    @property
    def prompt_overlay_path(self) -> Path:
        return self.paths.home / ".config" / "keskos" / "bashrc"

    def default_wallpaper(self) -> str:
        if self.custom_value("wallpaper_path"):
            return str(self.custom_value("wallpaper_path"))
        for candidate in DEFAULT_WALLPAPER_CANDIDATES:
            if candidate.is_file():
                return str(candidate)
        return ""

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
                parser.read(candidate, encoding="utf-8")
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

        if self.tools.get("lookandfeeltool"):
            self._run([self.tools["lookandfeeltool"], "-a", look_and_feel], capture=True, timeout=45)
            details.append(f"Applied look and feel package: {look_and_feel}")
        else:
            self.kwrite(self.kdeglobals, ("KDE",), "LookAndFeelPackage", look_and_feel)
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

        if wallpaper:
            warning = self.apply_wallpaper(wallpaper)
            if warning:
                warnings.append(warning)
            else:
                details.append(f"Wallpaper updated: {wallpaper}")

        self.set_custom_values(
            {
                "accent_color": accent_color,
                "crt_effects": bool(values["crt_effects"]),
                "scanlines": bool(values["scanlines"]),
                "glow_intensity": int(values["glow_intensity"]),
                "wallpaper_path": wallpaper,
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
                "mouse_speed": int(values["mouse_speed"]),
            }
        )
        return ApplyResult(
            True,
            "Input settings applied.",
            details=["Keyboard layout and repeat settings were written to KDE user config.", "Touchpad and pointer preferences were stored for KeskOS integration."],
            requires=["Keyboard layout changes may require logging out on Wayland."],
            backup_path=backup,
        )

    def parse_display_info(self) -> dict[str, Any]:
        info = {
            "session": os.environ.get("XDG_SESSION_TYPE", "unknown"),
            "plasma_version": first_nonempty_line(["plasmashell", "--version"]) if command_exists("plasmashell") else "unavailable",
            "output_summary": "Display detection unavailable",
        }
        tool = self.tools.get("kscreen-doctor")
        if tool:
            result = self._run([tool, "-o"], capture=True, timeout=20)
            if result is not None and result.returncode == 0:
                info["output_summary"] = result.stdout.strip() or "No output details were returned."
        return info

    def display_state(self) -> dict[str, Any]:
        data = self.parse_display_info()
        data["night_color"] = self.as_bool(self.custom_value("display_night_color"), False)
        return data

    def apply_display(self, values: dict[str, Any]) -> ApplyResult:
        backup = self.backup_files("display", (self.kwinrc, self.paths.settings_path))
        self.kwrite(self.kwinrc, ("NightColor",), "Active", self.bool_text(bool(values["night_color"])))
        self.set_custom_values({"display_night_color": bool(values["night_color"])})
        self.reconfigure_kwin()
        return ApplyResult(
            True,
            "Display preferences stored.",
            details=["Night Color preference was updated."],
            requires=["Use the advanced KDE display page for monitor layout, scale, and refresh-rate changes."],
            backup_path=backup,
        )

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

    def sound_state(self) -> dict[str, Any]:
        output_volume, output_muted = self._parse_wpctl_volume("@DEFAULT_AUDIO_SINK@")
        input_volume, input_muted = self._parse_wpctl_volume("@DEFAULT_AUDIO_SOURCE@")
        default_sink = "unavailable"
        default_source = "unavailable"
        if self.tools.get("pactl"):
            result = self._run([self.tools["pactl"], "info"], capture=True, timeout=10)
            if result is not None:
                for line in result.stdout.splitlines():
                    if line.startswith("Default Sink:"):
                        default_sink = line.split(":", 1)[1].strip()
                    if line.startswith("Default Source:"):
                        default_source = line.split(":", 1)[1].strip()
        return {
            "default_sink": default_sink,
            "default_source": default_source,
            "output_volume": output_volume,
            "output_muted": output_muted,
            "input_volume": input_volume,
            "input_muted": input_muted,
        }

    def apply_sound(self, values: dict[str, Any]) -> ApplyResult:
        details: list[str] = []
        warnings: list[str] = []
        tool = self.tools.get("wpctl")
        if tool:
            self._run([tool, "set-volume", "@DEFAULT_AUDIO_SINK@", f"{int(values['output_volume'])}%"], capture=True, timeout=10)
            self._run([tool, "set-mute", "@DEFAULT_AUDIO_SINK@", "1" if values["output_muted"] else "0"], capture=True, timeout=10)
            self._run([tool, "set-volume", "@DEFAULT_AUDIO_SOURCE@", f"{int(values['input_volume'])}%"], capture=True, timeout=10)
            self._run([tool, "set-mute", "@DEFAULT_AUDIO_SOURCE@", "1" if values["input_muted"] else "0"], capture=True, timeout=10)
            details.append("Updated PipeWire default input and output volume.")
        else:
            warnings.append("wpctl was not available, so volume changes could not be applied.")
        return ApplyResult(True, "Sound settings applied.", details=details, warnings=warnings)

    def network_state(self) -> dict[str, Any]:
        wifi_enabled = None
        current_network = "unavailable"
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
        return {
            "wifi_enabled": wifi_enabled,
            "current_network": current_network,
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
        self.set_custom_values({"default_browser_preference": browser})
        return ApplyResult(
            True,
            "Default applications updated.",
            details=["Updated xdg-settings, xdg-mime, mimeapps.list, and the KDE terminal preference."],
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
        sddm_theme = "unavailable"
        plymouth_theme = "unavailable"
        quiet_boot = self.as_bool(self.custom_value("boot_quiet_boot"), True)
        if Path("/etc/sddm.conf.d").is_dir():
            for config_path in sorted(Path("/etc/sddm.conf.d").glob("*.conf")):
                parser = configparser.ConfigParser(interpolation=None)
                parser.optionxform = str
                parser.read(config_path, encoding="utf-8")
                value = parser.get("Theme", "Current", fallback="")
                if value:
                    sddm_theme = value
                    break
        plymouth_config = Path("/etc/plymouth/plymouthd.conf")
        if plymouth_config.is_file():
            parser = configparser.ConfigParser(interpolation=None)
            parser.optionxform = str
            parser.read(plymouth_config, encoding="utf-8")
            plymouth_theme = parser.get("Daemon", "Theme", fallback=plymouth_theme)
        grub_default = Path("/etc/default/grub")
        if grub_default.is_file():
            quiet_boot = "quiet" in grub_default.read_text(encoding="utf-8", errors="replace")
        return {
            "sddm_theme": sddm_theme,
            "plymouth_theme": plymouth_theme,
            "boot_splash_min_duration": int(self.custom_value("boot_splash_min_duration", 2)),
            "show_boot_logs": self.as_bool(self.custom_value("boot_show_logs"), False),
            "quiet_boot": quiet_boot,
            "login_background": str(self.custom_value("login_background", "")),
        }

    def apply_boot(self, values: dict[str, Any]) -> ApplyResult:
        backup = self.backup_files("boot", (self.paths.settings_path,))
        self.set_custom_values(
            {
                "boot_splash_min_duration": int(values["boot_splash_min_duration"]),
                "boot_show_logs": bool(values["show_boot_logs"]),
                "boot_quiet_boot": bool(values["quiet_boot"]),
                "login_background": str(values["login_background"]).strip(),
            }
        )
        return ApplyResult(
            True,
            "Boot and login preferences stored.",
            details=["System-level SDDM, Plymouth, and bootloader changes still require a dedicated root-backed apply path.", "User-visible KeskOS boot preferences were saved."],
            requires=["A reboot is required after any future system boot theme changes."],
            backup_path=backup,
        )

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
            "crt_effects": self.as_bool(self.custom_value("crt_effects"), True),
            "scanlines": self.as_bool(self.custom_value("scanlines"), True),
            "prompt_style": self.prompt_style(),
            "browser_homepage_enabled": self.as_bool(self.custom_value("browser_homepage_enabled"), True),
            "first_run_completed": FIRST_RUN_STATE_FILE.exists(),
            "telemetry_enabled": self.as_bool(self.custom_value("telemetry_enabled"), False),
            "local_analytics_dashboard": self.as_bool(self.custom_value("local_analytics_dashboard"), False),
            "experimental_features": self.as_bool(self.custom_value("experimental_features"), False),
        }

    def apply_kesk(self, values: dict[str, Any], default_browser: str) -> ApplyResult:
        backup = self.backup_files("keskos", (self.paths.settings_path, self.prompt_overlay_path, FIRST_RUN_STATE_FILE))
        details: list[str] = []
        self.set_custom_values(
            {
                "accent_color": str(values["accent_color"]),
                "crt_effects": bool(values["crt_effects"]),
                "scanlines": bool(values["scanlines"]),
                "prompt_style": str(values["prompt_style"]),
                "browser_homepage_enabled": bool(values["browser_homepage_enabled"]),
                "telemetry_enabled": bool(values["telemetry_enabled"]),
                "local_analytics_dashboard": bool(values["local_analytics_dashboard"]),
                "experimental_features": bool(values["experimental_features"]),
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
        current_shell = os.environ.get("SHELL", "unavailable")
        plasma_version = first_nonempty_line(["plasmashell", "--version"]) if command_exists("plasmashell") else "unavailable"
        qt_version = detect_qt_version()
        kernel = first_nonempty_line(["uname", "-r"])
        return [
            ("KeskOS version", version_name),
            ("Build layer", build_id),
            ("Base distro", "Arch Linux"),
            ("Desktop", current_desktop),
            ("Desktop session", desktop_session),
            ("Plasma version", plasma_version),
            ("Qt version", qt_version),
            ("Kernel", kernel),
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
            "kesk_settings": self.paths.settings_path,
            "backups_dir": self.paths.backups_dir,
        }
        writable = {name: path.parent.exists() and os.access(path.parent, os.W_OK) for name, path in config_paths.items()}
        return {
            "session_type": os.environ.get("XDG_SESSION_TYPE", "unknown"),
            "display": os.environ.get("DISPLAY", ""),
            "wayland_display": os.environ.get("WAYLAND_DISPLAY", ""),
            "plasma_version": first_nonempty_line(["plasmashell", "--version"]) if command_exists("plasmashell") else "unavailable",
            "qt_version": detect_qt_version(),
            "tools": {name: bool(path) for name, path in self.tools.items()},
            "config_paths": {name: str(path) for name, path in config_paths.items()},
            "writable": writable,
        }
