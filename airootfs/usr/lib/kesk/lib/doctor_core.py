from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
from typing import Iterable, Sequence

from common import KeskConsole, SessionLogger, log_dir_candidates, shell_join

PACMAN_DB_PATH = Path(os.environ.get("KESK_PACMAN_DB_PATH", "/var/lib/pacman"))
PACMAN_LOCK_PATH = Path(os.environ.get("KESK_PACMAN_LOCK_PATH", "/var/lib/pacman/db.lck"))
PACMAN_CONF_PATH = Path(os.environ.get("KESK_PACMAN_CONF_PATH", "/etc/pacman.conf"))
PACMAN_MIRRORLIST_PATH = Path(os.environ.get("KESK_PACMAN_MIRRORLIST_PATH", "/etc/pacman.d/mirrorlist"))
PACMAN_CACHE_PATH = Path(os.environ.get("KESK_PACMAN_CACHE_PATH", "/var/cache/pacman/pkg"))
PACMAN_LOG_PATH = Path(os.environ.get("KESK_PACMAN_LOG_PATH", "/var/log/pacman.log"))
REBOOT_REQUIRED_PATH = Path(os.environ.get("KESK_REBOOT_REQUIRED_PATH", "/var/run/reboot-required"))
HOME_PATH = Path.home()
DEBUG_REPORT_PATH = HOME_PATH / "kesk-debug-report.txt"
INTERNET_TARGET = ("archlinux.org", 443)
INTERNET_TIMEOUT = 4.0
COMMAND_TIMEOUT = 20
PACMAN_CACHE_WARN_BYTES = 5 * 1024 * 1024 * 1024
PACMAN_CACHE_CRITICAL_BYTES = 10 * 1024 * 1024 * 1024
CRITICAL_DISK_PERCENT = 95
WARN_DISK_PERCENT = 85

SDDM_THEME_PATHS = (
    Path("/usr/share/sddm/themes/kesk"),
    Path("/usr/share/sddm/themes/keskos"),
    Path("/usr/share/sddm/themes/kesk-os"),
)
PLYMOUTH_THEME_PATHS = (
    Path("/usr/share/plymouth/themes/kesk"),
    Path("/usr/share/plymouth/themes/keskos"),
    Path("/usr/share/plymouth/themes/kesk-os"),
)
LAUNCHER_SEARCH_PATHS = (
    Path("/usr/share/plasma/plasmoids"),
    HOME_PATH / ".local" / "share" / "plasma" / "plasmoids",
    Path("/usr/share/keskos"),
    Path("/usr/lib/kesk"),
)
BROWSER_ASSET_PATHS = (
    Path("/usr/share/keskos/browser-home"),
    Path("/usr/share/keskos/homepage"),
    Path("/usr/share/keskos/startpage"),
)
QUICKSHELL_CONFIG_PATHS = (
    HOME_PATH / ".config" / "quickshell" / "keskos",
    Path("/etc/xdg/quickshell"),
    Path("/usr/local/share/keskos/source/configs/quickshell/keskos"),
    Path("/usr/share/kesk/quickshell"),
)
PLASMA_CONFIG_PATHS = (
    HOME_PATH / ".config" / "plasma-org.kde.plasma.desktop-appletsrc",
    HOME_PATH / ".config" / "kdeglobals",
    HOME_PATH / ".config" / "kwinrc",
)
BROWSER_COMMANDS = (
    ("librewolf", "LibreWolf"),
    ("brave-browser", "Brave"),
    ("brave", "Brave"),
    ("zen-browser", "Zen Browser"),
    ("firefox", "Firefox"),
)
REBOOT_PACKAGE_PREFIXES = (
    "linux",
    "systemd",
    "mesa",
    "lib32-mesa",
    "nvidia",
    "linux-firmware",
)
CRITICAL_SERVICES = {
    "NetworkManager.service",
    "dbus.service",
    "display-manager.service",
    "plasma-plasmashell.service",
    "sddm.service",
    "systemd-logind.service",
}


@dataclass
class CheckLine:
    kind: str
    message: str
    details: list[str] = field(default_factory=list)
    serious: bool = False


@dataclass
class UpdateSourceStatus:
    key: str
    label: str
    tool_name: str
    available: bool = False
    availability_kind: str = "skip"
    availability_message: str = ""
    count_kind: str = "skip"
    count_message: str = ""
    items: list[str] = field(default_factory=list)
    details: list[str] = field(default_factory=list)


@dataclass
class DiskStatus:
    label: str
    path: Path
    kind: str
    message: str
    percent: int | None = None
    used_bytes: int | None = None
    total_bytes: int | None = None
    serious: bool = False


@dataclass
class DoctorState:
    sections: dict[str, list[CheckLine]] = field(default_factory=dict)
    section_order: list[str] = field(default_factory=list)
    version_info: list[tuple[str, str]] = field(default_factory=list)
    update_sources: dict[str, UpdateSourceStatus] = field(default_factory=dict)
    failed_services: list[str] = field(default_factory=list)
    disks: list[DiskStatus] = field(default_factory=list)
    detected_browsers: list[str] = field(default_factory=list)
    launcher_matches: list[str] = field(default_factory=list)
    quickshell_matches: list[str] = field(default_factory=list)
    browser_asset_matches: list[str] = field(default_factory=list)
    sddm_theme_matches: list[str] = field(default_factory=list)
    plymouth_theme_matches: list[str] = field(default_factory=list)
    sddm_active_theme: str | None = None
    plymouth_active_theme: str | None = None
    reboot_reason: str = "unknown"
    reboot_details: list[str] = field(default_factory=list)
    logs_dir: Path | None = None
    log_path: Path | str = "logging unavailable"
    latest_upgrade_log: Path | None = None
    latest_doctor_log: Path | None = None
    debug_report_path: Path = DEBUG_REPORT_PATH
    serious_issue: bool = False
    pacman_missing: bool = False
    pacman_db_missing: bool = False
    pacman_lock_detected: bool = False


def command_exists(name: str) -> bool:
    return shutil.which(name) is not None


def clean_lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


def dedupe(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered


def add_result(
    state: DoctorState,
    section: str,
    kind: str,
    message: str,
    *,
    details: Iterable[str] = (),
    serious: bool = False,
) -> None:
    if section not in state.sections:
        state.section_order.append(section)
        state.sections[section] = []
    state.sections[section].append(CheckLine(kind=kind, message=message, details=list(details), serious=serious))
    if serious:
        state.serious_issue = True


def log_lines(logger: SessionLogger, prefix: str, lines: Iterable[str]) -> None:
    for line in lines:
        logger.log(f"{prefix} {line}")


def run_capture_timeout(
    command: Sequence[str],
    logger: SessionLogger,
    timeout: int = COMMAND_TIMEOUT,
) -> tuple[subprocess.CompletedProcess[str] | None, str | None]:
    logger.log(f"command={shell_join(command)}")
    try:
        result = subprocess.run(
            list(command),
            check=False,
            capture_output=True,
            text=True,
            errors="replace",
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout or ""
        stderr = exc.stderr or ""
        if not isinstance(stdout, str):
            stdout = stdout.decode("utf-8", errors="replace")
        if not isinstance(stderr, str):
            stderr = stderr.decode("utf-8", errors="replace")
        logger.log("exit_code=timeout")
        if stdout.strip():
            logger.log("stdout_begin")
            log_lines(logger, "stdout", stdout.splitlines())
            logger.log("stdout_end")
        if stderr.strip():
            logger.log("stderr_begin")
            log_lines(logger, "stderr", stderr.splitlines())
            logger.log("stderr_end")
        return None, f"timed out after {timeout}s"
    except OSError as exc:
        logger.log(f"os_error={exc}")
        return None, str(exc)

    logger.log(f"exit_code={result.returncode}")
    if result.stdout.strip():
        logger.log("stdout_begin")
        log_lines(logger, "stdout", result.stdout.splitlines())
        logger.log("stdout_end")
    if result.stderr.strip():
        logger.log("stderr_begin")
        log_lines(logger, "stderr", result.stderr.splitlines())
        logger.log("stderr_end")
    return result, None


def parse_generic_updates(output: str) -> list[str]:
    return clean_lines(output)


def parse_flatpak_updates(output: str) -> list[str]:
    lines: list[str] = []
    for raw_line in output.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.lower().startswith("name") and ("application" in line.lower() or "version" in line.lower()):
            continue
        parts = [part.strip() for part in raw_line.split("\t")]
        parts = [part for part in parts if part]
        if len(parts) >= 2:
            name = parts[0]
            app_id = parts[1]
            version = parts[2] if len(parts) >= 3 else ""
            lines.append(f"{name} / {app_id}" + (f" / {version}" if version else ""))
            continue
        lines.append(line)
    return lines


def _collect_fwupd_items(node: object, items: list[str]) -> None:
    if isinstance(node, list):
        for value in node:
            _collect_fwupd_items(value, items)
        return

    if not isinstance(node, dict):
        return

    devices = node.get("Devices") or node.get("devices")
    if isinstance(devices, list):
        for device in devices:
            _collect_fwupd_items(device, items)

    releases = node.get("Releases") or node.get("releases") or node.get("Updates") or node.get("updates")
    if isinstance(releases, list) and releases:
        device_name = (
            node.get("Name")
            or node.get("name")
            or node.get("DeviceName")
            or node.get("device_name")
            or node.get("DeviceId")
            or node.get("device_id")
            or "Firmware device"
        )
        for release in releases:
            if not isinstance(release, dict):
                continue
            release_name = (
                release.get("Name")
                or release.get("name")
                or release.get("Title")
                or release.get("title")
                or release.get("Version")
                or release.get("version")
            )
            items.append(f"{device_name} / {release_name}" if release_name else str(device_name))


def parse_fwupd_json(output: str) -> list[str]:
    payload = json.loads(output)
    items: list[str] = []
    _collect_fwupd_items(payload, items)
    return dedupe(items)


def parse_fwupd_plain(output: str) -> list[str]:
    if "No updatable devices" in output:
        return []

    items: list[str] = []
    for raw_line in output.splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.endswith(":"):
            continue
        if stripped.startswith(("See ", "Devices with no available firmware updates")):
            continue
        if stripped.startswith(("├─", "└─", "│", "•")):
            candidate = stripped.lstrip("├─└│• ").strip()
            if not candidate:
                continue
            if re.match(
                r"^(Current version|Vendor|GUID|Device Flags|Checksum|Summary|Branch|Remote ID)\b",
                candidate,
            ):
                continue
            items.append(candidate)
    return dedupe(items)


def human_size(num_bytes: int) -> str:
    value = float(num_bytes)
    units = ["B", "KiB", "MiB", "GiB", "TiB"]
    for unit in units:
        if value < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{int(value)} {unit}"
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{num_bytes} B"


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
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if line:
                return line
    except OSError:
        return None
    return None


def file_has_server_entries(path: Path) -> bool:
    if not path.is_file():
        return False
    try:
        return any(line.strip().startswith("Server =") for line in path.read_text(encoding="utf-8", errors="replace").splitlines())
    except OSError:
        return False


def pacman_conf_has_sync_servers(path: Path) -> bool:
    if not path.is_file():
        return False

    current_section = ""
    sync_sections = {"core", "extra", "multilib"}

    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return False

    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            current_section = line[1:-1].strip().lower()
            continue
        if current_section in sync_sections and line.startswith("Server ="):
            return True
    return False


def pacman_repositories_configured() -> bool:
    if file_has_server_entries(PACMAN_MIRRORLIST_PATH):
        return True
    return pacman_conf_has_sync_servers(PACMAN_CONF_PATH)


def update_count_from_result(
    result: subprocess.CompletedProcess[str],
    parser,
) -> tuple[int | None, list[str], str | None]:
    items = parser(result.stdout)
    if items:
        return len(items), items, None

    stderr_lines = clean_lines(result.stderr)
    if result.returncode == 0:
        return 0, [], None

    if result.returncode in {1, 2} and not stderr_lines and not result.stdout.strip():
        return 0, [], None

    if result.stdout.strip() and not stderr_lines:
        generic_items = clean_lines(result.stdout)
        return len(generic_items), generic_items, None

    error = stderr_lines[0] if stderr_lines else f"check exited with code {result.returncode}"
    return None, [], error


def latest_log_path(prefix: str) -> Path | None:
    newest_path: Path | None = None
    newest_mtime = -1.0

    for directory in log_dir_candidates():
        if not directory.exists():
            continue
        for path in directory.glob(f"{prefix}-*.log"):
            try:
                mtime = path.stat().st_mtime
            except OSError:
                continue
            if mtime > newest_mtime:
                newest_mtime = mtime
                newest_path = path
    return newest_path


def resolve_logs_dir(logger: SessionLogger) -> Path | None:
    if isinstance(logger.path, Path):
        return logger.path.parent
    for candidate in log_dir_candidates():
        if candidate.exists():
            return candidate
    return None


def socket_check(host: str, port: int, timeout: float) -> str | None:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return None
    except OSError as exc:
        return str(exc)


def parse_sddm_active_theme() -> tuple[str | None, list[str]]:
    paths = [Path("/etc/sddm.conf")]
    conf_dir = Path("/etc/sddm.conf.d")
    if conf_dir.is_dir():
        paths.extend(sorted(conf_dir.glob("*.conf")))

    active_theme: str | None = None
    checked_paths: list[str] = []

    for path in paths:
        if not path.is_file():
            continue
        checked_paths.append(str(path))
        current_section = ""
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for raw_line in lines:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("[") and line.endswith("]"):
                current_section = line[1:-1].strip().lower()
                continue
            if current_section == "theme" and line.lower().startswith("current="):
                active_theme = line.split("=", 1)[1].strip()
    return active_theme, checked_paths


def parse_plymouth_active_theme(logger: SessionLogger) -> tuple[str | None, list[str]]:
    details: list[str] = []
    if command_exists("plymouth-set-default-theme"):
        result, error = run_capture_timeout(["plymouth-set-default-theme"], logger, timeout=10)
        if result and result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip().splitlines()[-1].strip(), details
        if error:
            details.append(error)
        elif result and result.stderr.strip():
            details.append(clean_lines(result.stderr)[0])

    config_path = Path("/etc/plymouth/plymouthd.conf")
    if config_path.is_file():
        details.append(str(config_path))
        current_section = ""
        try:
            lines = config_path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            return None, details
        for raw_line in lines:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("[") and line.endswith("]"):
                current_section = line[1:-1].strip().lower()
                continue
            if current_section == "daemon" and line.lower().startswith("theme="):
                return line.split("=", 1)[1].strip(), details

    return None, details


def detect_kernel() -> str:
    try:
        return subprocess.check_output(["uname", "-r"], text=True, errors="replace").strip()
    except (OSError, subprocess.CalledProcessError):
        return "unavailable"


def command_version(command: Sequence[str], timeout: int = 10) -> str:
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
        try:
            result = subprocess.run(
                ["qmake6", "--version"],
                check=False,
                capture_output=True,
                text=True,
                errors="replace",
                timeout=10,
            )
        except (OSError, subprocess.TimeoutExpired):
            return "unavailable"

        for line in (*result.stdout.splitlines(), *result.stderr.splitlines()):
            stripped = line.strip()
            if stripped.lower().startswith("using qt version"):
                return stripped
        for line in (*result.stdout.splitlines(), *result.stderr.splitlines()):
            stripped = line.strip()
            if stripped:
                return stripped

    if command_exists("qtpaths6"):
        return command_version(["qtpaths6", "--qt-version"])

    return "unavailable"


def boot_time() -> datetime | None:
    try:
        uptime_seconds = float(Path("/proc/uptime").read_text(encoding="utf-8", errors="replace").split()[0])
    except (OSError, ValueError, IndexError):
        return None
    return datetime.now(timezone.utc) - timedelta(seconds=uptime_seconds)


def recent_reboot_packages() -> tuple[list[str], bool]:
    boot_started = boot_time()
    if boot_started is None or not PACMAN_LOG_PATH.is_file():
        return [], False

    reasons: list[str] = []
    try:
        lines = PACMAN_LOG_PATH.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return [], False

    for line in lines:
        match = re.match(r"\[(.+?)\]\s+\[ALPM\]\s+upgraded\s+([^\s]+)\s+\(", line)
        if not match:
            continue
        try:
            stamp = datetime.fromisoformat(match.group(1))
        except ValueError:
            continue
        if stamp.tzinfo is None:
            stamp = stamp.replace(tzinfo=timezone.utc)
        if stamp.astimezone(timezone.utc) < boot_started:
            continue
        package_name = match.group(2).lower()
        if package_name.startswith(REBOOT_PACKAGE_PREFIXES):
            reasons.append(package_name)
    return dedupe(reasons), True


def latest_installed_kernel() -> str | None:
    modules_dir = Path("/usr/lib/modules")
    if not modules_dir.is_dir():
        return None

    candidates: list[tuple[float, str]] = []
    for path in modules_dir.iterdir():
        if not path.is_dir():
            continue
        try:
            mtime = path.stat().st_mtime
        except OSError:
            continue
        candidates.append((mtime, path.name))

    if not candidates:
        return None
    return sorted(candidates, reverse=True)[0][1]


def maybe_collect_du(path: Path, logger: SessionLogger) -> int | None:
    if not path.exists():
        return None
    result, error = run_capture_timeout(["du", "-sb", str(path)], logger, timeout=15)
    if error or result is None or result.returncode != 0 or not result.stdout.strip():
        return None
    try:
        return int(result.stdout.split()[0])
    except (ValueError, IndexError):
        return None


def probe_official_updates(state: DoctorState, logger: SessionLogger) -> UpdateSourceStatus:
    source = UpdateSourceStatus(key="official", label="OFFICIAL REPOS", tool_name="pacman")
    state.update_sources[source.key] = source

    if not command_exists("pacman"):
        source.availability_kind = "warn"
        source.availability_message = "pacman not installed"
        source.count_kind = "warn"
        source.count_message = "official repo checks unavailable"
        add_result(state, "UPDATE CHANNELS", "warn", source.availability_message, serious=True)
        add_result(state, "UPDATE CHANNELS", "warn", source.count_message, serious=True)
        return source

    source.available = True
    source.availability_kind = "ok"
    source.availability_message = "official repo checks available"

    if command_exists("checkupdates"):
        check_command = ["checkupdates"]
        source.details.append("checkupdates detected")
        add_result(state, "UPDATE CHANNELS", "ok", "checkupdates detected")
    else:
        check_command = ["pacman", "-Qu"]
        source.details.append("checkupdates not installed; using pacman -Qu fallback")
        add_result(state, "UPDATE CHANNELS", "skip", "checkupdates not installed; pacman -Qu fallback active")

    if state.pacman_lock_detected:
        source.count_kind = "skip"
        source.count_message = "official repo update count skipped: pacman lock detected"
        add_result(state, "UPDATE CHANNELS", "skip", source.count_message, details=[str(PACMAN_LOCK_PATH)])
        return source

    if not pacman_repositories_configured():
        source.count_kind = "warn"
        source.count_message = "official repo update count unavailable: pacman repositories not configured"
        add_result(
            state,
            "UPDATE CHANNELS",
            "warn",
            source.count_message,
            details=[str(PACMAN_CONF_PATH), str(PACMAN_MIRRORLIST_PATH)],
        )
        return source

    result, error = run_capture_timeout(check_command, logger, timeout=25)
    if error or result is None:
        source.count_kind = "warn"
        source.count_message = f"official repo check failed: {error}"
        add_result(state, "UPDATE CHANNELS", "warn", source.count_message)
        return source

    count, items, count_error = update_count_from_result(result, parse_generic_updates)
    if count_error:
        source.count_kind = "warn"
        source.count_message = f"official repo check failed: {count_error}"
        add_result(state, "UPDATE CHANNELS", "warn", source.count_message)
        return source

    source.items = items
    source.count_kind = "ok"
    source.count_message = f"official repo updates: {count}"
    add_result(state, "UPDATE CHANNELS", "ok", source.count_message)
    return source


def probe_optional_updates(
    state: DoctorState,
    logger: SessionLogger,
    *,
    key: str,
    label: str,
    tool_name: str,
    unavailable_message: str,
    check_command: Sequence[str],
    parser,
    blocked_message: str | None = None,
) -> UpdateSourceStatus:
    source = UpdateSourceStatus(key=key, label=label, tool_name=tool_name)
    state.update_sources[source.key] = source

    if not command_exists(tool_name):
        source.availability_kind = "skip"
        source.availability_message = unavailable_message
        source.count_kind = "skip"
        source.count_message = f"{label.lower()} checks skipped"
        add_result(state, "UPDATE CHANNELS", "skip", unavailable_message)
        return source

    source.available = True
    source.availability_kind = "ok"
    source.availability_message = f"{tool_name} detected"
    add_result(state, "UPDATE CHANNELS", "ok", source.availability_message)

    if blocked_message:
        source.count_kind = "skip"
        source.count_message = blocked_message
        add_result(state, "UPDATE CHANNELS", "skip", blocked_message)
        return source

    result, error = run_capture_timeout(check_command, logger, timeout=25)
    if error or result is None:
        source.count_kind = "warn"
        source.count_message = f"{label.lower()} check failed: {error}"
        add_result(state, "UPDATE CHANNELS", "warn", source.count_message)
        return source

    count, items, count_error = update_count_from_result(result, parser)
    if count_error:
        source.count_kind = "warn"
        source.count_message = f"{label.lower()} check failed: {count_error}"
        add_result(state, "UPDATE CHANNELS", "warn", source.count_message)
        return source

    source.items = items
    source.count_kind = "ok"
    source.count_message = f"{label.lower()} updates: {count}"
    add_result(state, "UPDATE CHANNELS", "ok", source.count_message)
    return source


def scan_system_integrity(state: DoctorState, logger: SessionLogger) -> None:
    internet_error = socket_check(INTERNET_TARGET[0], INTERNET_TARGET[1], INTERNET_TIMEOUT)
    if internet_error is None:
        add_result(state, "SYSTEM INTEGRITY", "ok", "internet connection")
    else:
        add_result(
            state,
            "SYSTEM INTEGRITY",
            "warn",
            "no internet connection detected",
            details=[internet_error],
        )

    if command_exists("pacman"):
        add_result(state, "SYSTEM INTEGRITY", "ok", "pacman detected")
    else:
        state.pacman_missing = True
        add_result(state, "SYSTEM INTEGRITY", "warn", "pacman not installed", serious=True)

    if PACMAN_DB_PATH.exists():
        add_result(state, "SYSTEM INTEGRITY", "ok", f"pacman database path present: {PACMAN_DB_PATH}")
    else:
        state.pacman_db_missing = True
        add_result(
            state,
            "SYSTEM INTEGRITY",
            "warn",
            f"pacman database path missing: {PACMAN_DB_PATH}",
            serious=True,
        )

    state.pacman_lock_detected = PACMAN_LOCK_PATH.exists()
    if state.pacman_lock_detected:
        add_result(state, "SYSTEM INTEGRITY", "warn", f"pacman lock detected: {PACMAN_LOCK_PATH}")
    else:
        add_result(state, "SYSTEM INTEGRITY", "ok", "pacman lock not present")

    if pacman_repositories_configured():
        add_result(state, "SYSTEM INTEGRITY", "ok", "pacman repositories configured")
    else:
        add_result(
            state,
            "SYSTEM INTEGRITY",
            "warn",
            "pacman repositories are not configured",
            details=[str(PACMAN_CONF_PATH), str(PACMAN_MIRRORLIST_PATH)],
        )


def scan_update_channels(state: DoctorState, logger: SessionLogger) -> None:
    probe_official_updates(state, logger)
    probe_optional_updates(
        state,
        logger,
        key="aur",
        label="AUR",
        tool_name="yay",
        unavailable_message="AUR support unavailable: yay not installed",
        check_command=["yay", "-Qua"],
        parser=parse_generic_updates,
        blocked_message="AUR update count skipped: pacman lock detected" if state.pacman_lock_detected else None,
    )
    probe_optional_updates(
        state,
        logger,
        key="flatpak",
        label="FLATPAK",
        tool_name="flatpak",
        unavailable_message="Flatpak support unavailable: flatpak not installed",
        check_command=["flatpak", "remote-ls", "--updates", "--columns=name,application,version"],
        parser=parse_flatpak_updates,
    )

    firmware = UpdateSourceStatus(key="firmware", label="FIRMWARE", tool_name="fwupdmgr")
    state.update_sources[firmware.key] = firmware
    if not command_exists("fwupdmgr"):
        firmware.availability_kind = "skip"
        firmware.availability_message = "Firmware support unavailable: fwupd not installed"
        firmware.count_kind = "skip"
        firmware.count_message = "firmware checks skipped"
        add_result(state, "UPDATE CHANNELS", "skip", firmware.availability_message)
        return

    firmware.available = True
    firmware.availability_kind = "ok"
    firmware.availability_message = "fwupdmgr detected"
    add_result(state, "UPDATE CHANNELS", "ok", firmware.availability_message)

    json_result, json_error = run_capture_timeout(["fwupdmgr", "get-updates", "--json"], logger, timeout=25)
    if json_result and json_result.returncode == 0 and json_result.stdout.strip():
        try:
            firmware.items = parse_fwupd_json(json_result.stdout)
            firmware.count_kind = "ok"
            firmware.count_message = f"firmware updates: {len(firmware.items)}"
            add_result(state, "UPDATE CHANNELS", "ok", firmware.count_message)
            return
        except json.JSONDecodeError:
            firmware.details.append("fwupdmgr JSON output could not be parsed; using plain fallback")

    plain_result, plain_error = run_capture_timeout(["fwupdmgr", "get-updates"], logger, timeout=25)
    if plain_error or plain_result is None:
        firmware.count_kind = "warn"
        firmware.count_message = f"firmware check failed: {plain_error or json_error}"
        add_result(state, "UPDATE CHANNELS", "warn", firmware.count_message)
        return

    count, items, error = update_count_from_result(plain_result, parse_fwupd_plain)
    if error:
        firmware.count_kind = "warn"
        firmware.count_message = f"firmware check failed: {error}"
        add_result(state, "UPDATE CHANNELS", "warn", firmware.count_message)
        return

    firmware.items = items
    firmware.count_kind = "ok"
    firmware.count_message = f"firmware updates: {count}"
    add_result(state, "UPDATE CHANNELS", "ok", firmware.count_message)


def scan_failed_services(state: DoctorState, logger: SessionLogger) -> None:
    if not command_exists("systemctl"):
        add_result(state, "SERVICES", "skip", "systemd status unavailable: systemctl not installed")
        return

    result, error = run_capture_timeout(
        ["systemctl", "--failed", "--no-pager", "--plain", "--no-legend", "--type=service"],
        logger,
        timeout=15,
    )
    if error or result is None:
        add_result(state, "SERVICES", "skip", f"failed service scan unavailable: {error}")
        return

    failed_services: list[str] = []
    for raw_line in result.stdout.splitlines():
        line = raw_line.strip()
        if not line or line.startswith(("0 loaded", "Legend", "UNIT ")):
            continue
        if " loaded units listed." in line:
            continue
        service_name = line.split()[0]
        if service_name.endswith(".service"):
            failed_services.append(service_name)

    state.failed_services = dedupe(failed_services)
    if not state.failed_services:
        add_result(state, "SERVICES", "ok", "failed systemd services: 0")
        return

    serious = len(state.failed_services) >= 3 or any(service in CRITICAL_SERVICES for service in state.failed_services)
    add_result(
        state,
        "SERVICES",
        "warn",
        f"failed systemd services: {len(state.failed_services)}",
        details=state.failed_services,
        serious=serious,
    )


def scan_storage(state: DoctorState, logger: SessionLogger) -> None:
    seen_paths: set[Path] = set()
    for label, path in (
        ("root", Path("/")),
        ("home", Path("/home")),
        ("boot", Path("/boot")),
    ):
        if not path.exists() or path in seen_paths:
            continue
        seen_paths.add(path)
        try:
            usage = shutil.disk_usage(path)
        except OSError as exc:
            add_result(state, "STORAGE", "skip", f"{label} disk usage unavailable", details=[str(exc)])
            continue

        percent = int((usage.used / usage.total) * 100) if usage.total else 0
        if percent >= CRITICAL_DISK_PERCENT:
            kind = "warn"
            message = f"{label} disk usage critical: {percent}%"
            serious = True
        elif percent >= WARN_DISK_PERCENT:
            kind = "warn"
            message = f"{label} disk usage high: {percent}%"
            serious = False
        else:
            kind = "ok"
            message = f"{label} disk usage: {percent}%"
            serious = False

        state.disks.append(
            DiskStatus(
                label=label,
                path=path,
                kind=kind,
                message=message,
                percent=percent,
                used_bytes=usage.used,
                total_bytes=usage.total,
                serious=serious,
            )
        )
        add_result(
            state,
            "STORAGE",
            kind,
            message,
            details=[f"{human_size(usage.used)} used of {human_size(usage.total)}"],
            serious=serious,
        )

    if PACMAN_CACHE_PATH.exists():
        cache_bytes = maybe_collect_du(PACMAN_CACHE_PATH, logger)
        if cache_bytes is None:
            add_result(state, "STORAGE", "skip", "pacman cache size unavailable")
        elif cache_bytes >= PACMAN_CACHE_CRITICAL_BYTES:
            add_result(
                state,
                "STORAGE",
                "warn",
                f"pacman cache size critical: {human_size(cache_bytes)}",
                serious=False,
            )
        elif cache_bytes >= PACMAN_CACHE_WARN_BYTES:
            add_result(state, "STORAGE", "warn", f"pacman cache size high: {human_size(cache_bytes)}")
        else:
            add_result(state, "STORAGE", "ok", f"pacman cache size: {human_size(cache_bytes)}")


def scan_reboot(state: DoctorState) -> None:
    reasons: list[str] = []
    confident = False

    if REBOOT_REQUIRED_PATH.exists():
        reasons.append(f"{REBOOT_REQUIRED_PATH} exists")
        confident = True

    running_kernel = detect_kernel()
    installed_kernel = latest_installed_kernel()
    if installed_kernel:
        confident = True
        if running_kernel != installed_kernel:
            reasons.append(f"running kernel {running_kernel} differs from installed {installed_kernel}")

    upgraded_packages, log_available = recent_reboot_packages()
    if log_available:
        confident = True
        if upgraded_packages:
            reasons.append("recent core package upgrades after boot: " + ", ".join(upgraded_packages))

    state.reboot_details = reasons
    if reasons:
        state.reboot_reason = "recommended"
        add_result(state, "SYSTEM INTEGRITY", "warn", "reboot recommended", details=reasons)
    elif confident:
        state.reboot_reason = "not-required"
        add_result(state, "SYSTEM INTEGRITY", "ok", "reboot not required")
    else:
        state.reboot_reason = "unknown"
        add_result(state, "SYSTEM INTEGRITY", "skip", "reboot recommendation unknown")


def scan_version_info(state: DoctorState) -> None:
    os_release = read_key_value_file(Path("/etc/os-release"))
    kesk_release = read_key_value_file(Path("/etc/kesk-release"))
    kesk_version = read_key_value_file(Path("/usr/share/kesk/version"))
    raw_version_line = read_first_line(Path("/usr/share/kesk/version"))

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

    plasma_version = command_version(["plasmashell", "--version"]) if command_exists("plasmashell") else "unavailable"
    frameworks_version = command_version(["kf6-config", "--version"]) if command_exists("kf6-config") else "unavailable"
    qt_version = detect_qt_version()

    state.version_info = [
        ("KeskOS version", version_name),
        ("Build layer", build_id),
        ("Kernel", detect_kernel()),
        ("Desktop session", os.environ.get("DESKTOP_SESSION", "unavailable")),
        ("Current desktop", os.environ.get("XDG_CURRENT_DESKTOP", "unavailable")),
        ("Plasma version", plasma_version),
        ("KDE Frameworks", frameworks_version),
        ("Qt version", qt_version),
    ]

    add_result(state, "BUILD INFO", "ok", f"KeskOS version: {version_name}")
    add_result(state, "BUILD INFO", "ok", f"build layer: {build_id}")
    add_result(state, "BUILD INFO", "ok", f"kernel: {detect_kernel()}")
    if plasma_version != "unavailable":
        add_result(state, "BUILD INFO", "ok", plasma_version)
    else:
        add_result(state, "BUILD INFO", "skip", "Plasma version unavailable")


def scan_sddm(state: DoctorState) -> None:
    matches = [str(path) for path in SDDM_THEME_PATHS if path.exists()]
    state.sddm_theme_matches = matches
    if matches:
        add_result(state, "DESKTOP STACK", "ok", "SDDM Kesk theme found", details=matches)
    else:
        add_result(state, "DESKTOP STACK", "warn", "SDDM Kesk theme missing")

    active_theme, checked_paths = parse_sddm_active_theme()
    state.sddm_active_theme = active_theme
    if active_theme:
        if "kesk" in active_theme.lower():
            add_result(state, "DESKTOP STACK", "ok", f"SDDM active theme: {active_theme}", details=checked_paths)
        else:
            add_result(state, "DESKTOP STACK", "warn", f"SDDM active theme is not KeskOS: {active_theme}", details=checked_paths)
    else:
        add_result(state, "DESKTOP STACK", "skip", "SDDM active theme could not be determined", details=checked_paths)


def scan_plymouth(state: DoctorState, logger: SessionLogger) -> None:
    matches = [str(path) for path in PLYMOUTH_THEME_PATHS if path.exists()]
    state.plymouth_theme_matches = matches
    if matches:
        add_result(state, "DESKTOP STACK", "ok", "Plymouth Kesk theme found", details=matches)
    elif command_exists("plymouth-set-default-theme") or Path("/etc/plymouth").exists():
        add_result(state, "DESKTOP STACK", "warn", "Plymouth Kesk theme missing")
    else:
        add_result(state, "DESKTOP STACK", "skip", "Plymouth not installed")

    active_theme, details = parse_plymouth_active_theme(logger)
    state.plymouth_active_theme = active_theme
    if active_theme:
        if "kesk" in active_theme.lower():
            add_result(state, "DESKTOP STACK", "ok", f"active Plymouth theme: {active_theme}", details=details)
        else:
            add_result(state, "DESKTOP STACK", "warn", f"active Plymouth theme is not KeskOS: {active_theme}", details=details)
    elif matches:
        add_result(state, "DESKTOP STACK", "skip", "active Plymouth theme could not be determined", details=details)


def scan_plasma(state: DoctorState) -> None:
    desktop_session = os.environ.get("DESKTOP_SESSION", "")
    current_desktop = os.environ.get("XDG_CURRENT_DESKTOP", "")
    plasma_detected = "plasma" in desktop_session.lower() or "kde" in current_desktop.lower() or command_exists("plasmashell")

    if plasma_detected:
        details = [f"DESKTOP_SESSION={desktop_session or 'unavailable'}", f"XDG_CURRENT_DESKTOP={current_desktop or 'unavailable'}"]
        add_result(state, "DESKTOP STACK", "ok", "KDE Plasma detected", details=details)
    else:
        add_result(state, "DESKTOP STACK", "skip", "KDE Plasma not detected")

    existing_configs = [str(path) for path in PLASMA_CONFIG_PATHS if path.exists()]
    if existing_configs:
        add_result(state, "DESKTOP STACK", "ok", "Plasma config exists", details=existing_configs)
    else:
        add_result(state, "DESKTOP STACK", "warn", "Plasma config missing")


def scan_launcher_files(state: DoctorState) -> None:
    matches: list[str] = []
    patterns = ("kesk", "kickoff", "launcher")
    for base_path in LAUNCHER_SEARCH_PATHS:
        if not base_path.exists():
            continue
        if base_path.is_dir():
            try:
                entries = sorted(base_path.iterdir(), key=lambda path: path.name.lower())
            except OSError:
                continue
            for entry in entries:
                name = entry.name.lower()
                if any(pattern in name for pattern in patterns):
                    matches.append(str(entry))
    state.launcher_matches = dedupe(matches)

    if state.launcher_matches:
        add_result(state, "DESKTOP STACK", "ok", "Kesk launcher files found", details=state.launcher_matches[:12])
    else:
        add_result(state, "DESKTOP STACK", "warn", "Kesk launcher files missing")


def scan_quickshell(state: DoctorState) -> None:
    if command_exists("quickshell"):
        add_result(state, "DESKTOP STACK", "ok", "Quickshell installed")
    else:
        add_result(state, "DESKTOP STACK", "skip", "Quickshell not installed")

    matches = [str(path) for path in QUICKSHELL_CONFIG_PATHS if path.exists()]
    autostarts = [
        HOME_PATH / ".config" / "autostart" / "keskos-quickshell.desktop",
        HOME_PATH / ".config" / "autostart" / "keskos-display-watch.desktop",
    ]
    matches.extend(str(path) for path in autostarts if path.exists())
    state.quickshell_matches = dedupe(matches)

    if state.quickshell_matches:
        add_result(state, "DESKTOP STACK", "ok", "Kesk HUD config found", details=state.quickshell_matches)
    elif command_exists("quickshell"):
        add_result(state, "DESKTOP STACK", "warn", "Kesk HUD config missing")


def scan_browser_assets(state: DoctorState) -> None:
    browsers: list[str] = []
    seen_commands: set[str] = set()
    for command_name, label in BROWSER_COMMANDS:
        if command_name in seen_commands:
            continue
        seen_commands.add(command_name)
        if command_exists(command_name):
            browsers.append(label)
    state.detected_browsers = dedupe(browsers)

    if state.detected_browsers:
        add_result(state, "DESKTOP STACK", "ok", "detected browsers: " + ", ".join(state.detected_browsers))
    else:
        add_result(state, "DESKTOP STACK", "skip", "supported browsers not detected")

    matches = [str(path) for path in BROWSER_ASSET_PATHS if path.exists()]
    extra_paths = [
        Path("/usr/share/keskos/browser-themes/firefox"),
        Path("/usr/share/keskos/browser-themes/brave"),
    ]
    matches.extend(str(path) for path in extra_paths if path.exists())
    state.browser_asset_matches = dedupe(matches)

    if state.browser_asset_matches:
        add_result(state, "DESKTOP STACK", "ok", "Kesk browser homepage assets found", details=state.browser_asset_matches)
    else:
        add_result(state, "DESKTOP STACK", "warn", "Kesk browser homepage assets missing")


def refresh_state(logger: SessionLogger) -> DoctorState:
    state = DoctorState()
    state.log_path = logger.path
    state.logs_dir = resolve_logs_dir(logger)

    scan_system_integrity(state, logger)
    scan_update_channels(state, logger)
    scan_sddm(state)
    scan_plymouth(state, logger)
    scan_plasma(state)
    scan_launcher_files(state)
    scan_quickshell(state)
    scan_browser_assets(state)
    scan_failed_services(state, logger)
    scan_storage(state, logger)
    scan_version_info(state)
    scan_reboot(state)

    state.latest_upgrade_log = latest_log_path("upgrade")
    state.latest_doctor_log = latest_log_path("doctor")
    logger.log(f"serious_issue={str(state.serious_issue).lower()}")
    logger.log(f"reboot_status={state.reboot_reason}")
    return state


def render_dashboard(console: KeskConsole, state: DoctorState, logger: SessionLogger) -> None:
    console.clear()
    console.header("KESK SYSTEM DOCTOR", "SYSTEM INTEGRITY // DESKTOP STACK // UPDATE CHANNELS")
    console.line()
    for section in state.section_order:
        for line in state.sections[section]:
            console.status(line.kind, line.message)
        console.line()
    console.status("ok", f"session log: {logger.path}")
    console.line()
    console.menu(
        [
            "[1] Run full scan again",
            "[2] Show detailed report",
            "[3] Export debug report",
            "[4] Open logs directory",
            "[5] Exit",
        ]
    )


def render_detailed_report(console: KeskConsole, state: DoctorState) -> None:
    console.clear()
    console.header("KESK SYSTEM DOCTOR", "DETAILED REPORT")

    for section in state.section_order:
        console.section(section)
        for line in state.sections[section]:
            console.status(line.kind, line.message)
            for detail in line.details:
                console.muted(f"  {detail}")

        if section == "UPDATE CHANNELS":
            for key in ("official", "aur", "flatpak", "firmware"):
                source = state.update_sources.get(key)
                if not source or not source.items:
                    continue
                console.muted(f"  {source.label}:")
                for item in source.items:
                    console.line(f"    - {item}")

    if state.version_info:
        console.section("VERSION FIELDS")
        for label, value in state.version_info:
            console.line(f"{label}: {value}")

    if state.logs_dir:
        console.section("LOGS")
        console.line(f"Doctor logs directory: {state.logs_dir}")
        if state.latest_upgrade_log:
            console.line(f"Latest upgrade log: {state.latest_upgrade_log}")
        if state.latest_doctor_log:
            console.line(f"Latest doctor log: {state.latest_doctor_log}")

    console.line()
    console.pause()


def state_payload(state: DoctorState) -> dict[str, object]:
    return {
        "serious_issue": state.serious_issue,
        "pacman_missing": state.pacman_missing,
        "pacman_db_missing": state.pacman_db_missing,
        "pacman_lock_detected": state.pacman_lock_detected,
        "reboot_reason": state.reboot_reason,
        "reboot_details": state.reboot_details,
        "version_info": [{"label": label, "value": value} for label, value in state.version_info],
        "sections": {
            section: [
                {
                    "kind": line.kind,
                    "message": line.message,
                    "details": line.details,
                    "serious": line.serious,
                }
                for line in state.sections.get(section, [])
            ]
            for section in state.section_order
        },
        "section_order": state.section_order,
        "update_sources": {
            key: {
                "key": source.key,
                "label": source.label,
                "tool_name": source.tool_name,
                "available": source.available,
                "availability_kind": source.availability_kind,
                "availability_message": source.availability_message,
                "count_kind": source.count_kind,
                "count_message": source.count_message,
                "items": source.items,
                "details": source.details,
            }
            for key, source in state.update_sources.items()
        },
        "failed_services": state.failed_services,
        "disks": [
            {
                "label": disk.label,
                "path": str(disk.path),
                "kind": disk.kind,
                "message": disk.message,
                "percent": disk.percent,
                "used_bytes": disk.used_bytes,
                "total_bytes": disk.total_bytes,
                "serious": disk.serious,
            }
            for disk in state.disks
        ],
        "detected_browsers": state.detected_browsers,
        "launcher_matches": state.launcher_matches,
        "quickshell_matches": state.quickshell_matches,
        "browser_asset_matches": state.browser_asset_matches,
        "sddm_theme_matches": state.sddm_theme_matches,
        "plymouth_theme_matches": state.plymouth_theme_matches,
        "sddm_active_theme": state.sddm_active_theme,
        "plymouth_active_theme": state.plymouth_active_theme,
        "logs_dir": str(state.logs_dir) if state.logs_dir else None,
        "log_path": str(state.log_path),
        "latest_upgrade_log": str(state.latest_upgrade_log) if state.latest_upgrade_log else None,
        "latest_doctor_log": str(state.latest_doctor_log) if state.latest_doctor_log else None,
        "debug_report_path": str(state.debug_report_path),
    }


def print_json_payload(payload: dict[str, object]) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def build_debug_report(state: DoctorState) -> str:
    lines = [
        "KESK DEBUG REPORT",
        f"Generated: {datetime.now().isoformat()}",
        "",
        "VERSION INFO",
    ]
    for label, value in state.version_info:
        lines.append(f"- {label}: {value}")

    lines.extend(
        [
            "",
            "SUMMARY",
        ]
    )
    for section in state.section_order:
        lines.append(f"[{section}]")
        for line in state.sections[section]:
            prefix = {
                "ok": "[ OK ]",
                "warn": "[ !! ]",
                "work": "[ .. ]",
                "skip": "[ -- ]",
            }.get(line.kind, "[ .. ]")
            lines.append(f"{prefix} {line.message}")
            for detail in line.details:
                lines.append(f"  - {detail}")
        lines.append("")

    lines.append("UPDATE DETAILS")
    for key in ("official", "aur", "flatpak", "firmware"):
        source = state.update_sources.get(key)
        if not source:
            continue
        lines.append(f"- {source.label}: {source.count_message or source.availability_message or 'unavailable'}")
        for item in source.items:
            lines.append(f"  - {item}")

    lines.extend(
        [
            "",
            "FAILED SERVICES",
        ]
    )
    if state.failed_services:
        for service in state.failed_services:
            lines.append(f"- {service}")
    else:
        lines.append("- none")

    lines.extend(
        [
            "",
            "DISK USAGE",
        ]
    )
    if state.disks:
        for disk in state.disks:
            detail = ""
            if disk.used_bytes is not None and disk.total_bytes is not None:
                detail = f" ({human_size(disk.used_bytes)} / {human_size(disk.total_bytes)})"
            percent = f"{disk.percent}%" if disk.percent is not None else "unknown"
            lines.append(f"- {disk.label}: {percent}{detail}")
    else:
        lines.append("- unavailable")

    lines.extend(
        [
            "",
            "THEME AND SHELL",
            f"- SDDM active theme: {state.sddm_active_theme or 'unknown'}",
            f"- Plymouth active theme: {state.plymouth_active_theme or 'unknown'}",
            f"- Quickshell config: {', '.join(state.quickshell_matches) if state.quickshell_matches else 'not found'}",
            f"- Launcher files: {', '.join(state.launcher_matches[:12]) if state.launcher_matches else 'not found'}",
            f"- Browser assets: {', '.join(state.browser_asset_matches) if state.browser_asset_matches else 'not found'}",
            "",
            "LOGS",
            f"- Current doctor log: {state.log_path}",
            f"- Latest doctor log: {state.latest_doctor_log or 'not found'}",
            f"- Latest upgrade log: {state.latest_upgrade_log or 'not found'}",
            "",
            "NOT INCLUDED",
            "- passwords",
            "- SSH keys",
            "- browser cookies",
            "- tokens",
            "- full home directory listings",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def export_debug_report(console: KeskConsole, state: DoctorState, logger: SessionLogger) -> None:
    report_path = state.debug_report_path
    try:
        report_path.write_text(build_debug_report(state), encoding="utf-8")
    except OSError as exc:
        logger.log(f"export_debug_report=failed:{exc}")
        console.status("warn", f"failed to export debug report: {exc}")
        console.pause()
        return

    logger.log(f"export_debug_report={report_path}")
    console.status("ok", f"debug report exported: {report_path}")
    console.pause()


def export_debug_report_noninteractive(state: DoctorState, logger: SessionLogger) -> tuple[int, str]:
    report_path = state.debug_report_path
    try:
        report_path.write_text(build_debug_report(state), encoding="utf-8")
    except OSError as exc:
        logger.log(f"export_debug_report=failed:{exc}")
        return 1, str(exc)

    logger.log(f"export_debug_report={report_path}")
    return 0, str(report_path)


def open_logs_directory(console: KeskConsole, state: DoctorState, logger: SessionLogger) -> None:
    logs_dir = state.logs_dir
    if logs_dir is None:
        logger.log("open_logs_directory=unavailable")
        console.status("warn", "logs directory unavailable")
        console.pause()
        return

    if not logs_dir.exists():
        try:
            logs_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            logger.log(f"open_logs_directory=failed:{exc}")
            console.status("warn", f"could not create logs directory: {exc}")
            console.pause()
            return

    opener: Sequence[str] | None = None
    if os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"):
        if command_exists("xdg-open"):
            opener = ["xdg-open", str(logs_dir)]
        elif command_exists("dolphin"):
            opener = ["dolphin", str(logs_dir)]

    if opener is None:
        logger.log(f"open_logs_directory=printed:{logs_dir}")
        console.status("ok", f"logs directory: {logs_dir}")
        console.pause()
        return

    try:
        subprocess.Popen(
            list(opener),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
        )
    except OSError as exc:
        logger.log(f"open_logs_directory=failed:{exc}")
        console.status("warn", f"could not open logs directory: {exc}")
        console.status("ok", f"logs directory: {logs_dir}")
        console.pause()
        return

    logger.log(f"open_logs_directory=opened:{logs_dir}")
    console.status("ok", f"opened logs directory: {logs_dir}")
    console.pause()


def print_help(console: KeskConsole) -> int:
    console.header("KESK SYSTEM DOCTOR", "READ-ONLY SYSTEM HEALTH CHECKER")
    console.line("Usage: kesk doctor")
    console.line("       kesk doctor --json")
    console.line("       kesk doctor --export [--json]")
    console.line()
    console.line("Checks:")
    console.line("- package manager state and update tools")
    console.line("- SDDM, Plymouth, Plasma, launcher, Quickshell, and browser assets")
    console.line("- failed services, disk usage, network reachability, and reboot recommendation")
    console.line("- KeskOS version, build info, and current logs")
    return 0


def main(args: Sequence[str], _root: Path) -> int:
    console = KeskConsole()
    arg_set = set(args)

    if args and args[0] in {"--help", "-h", "help"}:
        return print_help(console)

    logger = SessionLogger("doctor")
    last_exit_code = 0

    try:
        if "--export" in arg_set:
            state = refresh_state(logger)
            exit_code, payload = export_debug_report_noninteractive(state, logger)
            if "--json" in arg_set:
                print_json_payload({"exit_code": exit_code, "report_path": payload if exit_code == 0 else None, "error": None if exit_code == 0 else payload})
            elif exit_code == 0:
                console.status("ok", f"debug report exported: {payload}")
            else:
                console.status("warn", f"failed to export debug report: {payload}")
            return exit_code if exit_code != 0 else (2 if state.serious_issue else 0)

        if "--json" in arg_set:
            state = refresh_state(logger)
            print_json_payload(state_payload(state))
            return 2 if state.serious_issue else 0

        state = refresh_state(logger)
        last_exit_code = 2 if state.serious_issue else 0

        while True:
            render_dashboard(console, state, logger)
            try:
                choice = console.input("Select action").strip()
            except EOFError:
                logger.log("selected_action=eof_exit")
                return last_exit_code

            if choice == "5":
                logger.log("selected_action=exit")
                return last_exit_code

            if choice == "1":
                logger.log("selected_action=refresh")
                state = refresh_state(logger)
                last_exit_code = 2 if state.serious_issue else 0
                continue

            if choice == "2":
                logger.log("selected_action=detail_report")
                render_detailed_report(console, state)
                continue

            if choice == "3":
                logger.log("selected_action=export_debug_report")
                export_debug_report(console, state, logger)
                continue

            if choice == "4":
                logger.log("selected_action=open_logs_directory")
                open_logs_directory(console, state, logger)
                continue

            console.status("warn", "invalid selection")
            console.pause()
    except KeyboardInterrupt:
        logger.log("final_status=interrupted")
        console.line()
        console.status("warn", "interrupted by user")
        return 130
    except Exception as exc:
        logger.log(f"final_status=error:{exc!r}")
        console.clear()
        console.header("KESK SYSTEM DOCTOR", "ERROR")
        console.status("warn", f"doctor failed: {exc}")
        return 1
    finally:
        logger.close()
