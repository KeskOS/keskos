from __future__ import annotations

from dataclasses import dataclass
import getpass
import os
from pathlib import Path
import shutil
import signal
import socket
import subprocess
import sys
from typing import Sequence

from common import KeskConsole, SessionLogger, shell_join


DOC_LINKS: tuple[tuple[str, str], ...] = (
    ("Docs", "https://docs.keskos.org"),
    ("Website", "https://keskos.org"),
    ("Downloads", "https://downloads.keskos.org"),
    ("GitHub", "https://github.com/memegeko/keskos"),
)


@dataclass
class ControlPaths:
    logs_dir: Path
    backups_dir: Path


@dataclass
class MenuNotice:
    kind: str
    message: str


def command_exists(name: str) -> bool:
    return shutil.which(name) is not None


def ensure_directory(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


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


def about_rows(root: Path, paths: ControlPaths) -> list[tuple[str, str]]:
    version_name, build_id = collect_release_info(root)
    desktop_session = os.environ.get("DESKTOP_SESSION", "unavailable")
    current_desktop = os.environ.get("XDG_CURRENT_DESKTOP", "unavailable")
    current_shell = os.environ.get("SHELL", "unavailable")
    plasma_version = first_nonempty_line(["plasmashell", "--version"]) if command_exists("plasmashell") else "unavailable"
    qt_version = detect_qt_version()
    kernel = first_nonempty_line(["uname", "-r"])

    return [
        ("KeskOS version", version_name),
        ("Build layer", build_id),
        ("Kernel", kernel),
        ("Desktop session", desktop_session),
        ("Current desktop", current_desktop),
        ("Plasma version", plasma_version),
        ("Qt version", qt_version),
        ("Active user", getpass.getuser()),
        ("Hostname", socket.gethostname()),
        ("Uptime", detect_uptime()),
        ("Package count", detect_package_count()),
        ("Current shell", current_shell),
        ("Logs directory", str(paths.logs_dir)),
        ("Backups directory", str(paths.backups_dir)),
    ]


def python_command(path: Path, *extra_args: str) -> list[str]:
    if os.access(path, os.X_OK):
        return [str(path), *extra_args]
    return [sys.executable, str(path), *extra_args]


def resolve_kesk_router(root: Path) -> Path | None:
    candidates = [
        root.parents[1] / "bin" / "kesk",
        Path("/usr/bin/kesk"),
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def resolve_tool_command(root: Path, tool_name: str) -> list[str] | None:
    router_path = resolve_kesk_router(root)
    if router_path is not None:
        return python_command(router_path, tool_name)

    command_path = root / "commands" / tool_name
    if command_path.is_file():
        return python_command(command_path)

    if command_exists("kesk"):
        return ["kesk", tool_name]

    return None


def tool_ready(root: Path, tool_name: str) -> bool:
    return resolve_tool_command(root, tool_name) is not None


def open_target(logger: SessionLogger, target: str, label: str) -> tuple[str, str]:
    if not command_exists("xdg-open"):
        logger.log(f"open_target={label}:xdg-open-missing")
        return "skip", f"{label.lower()} path: {target}"

    logger.log(f"command={shell_join(['xdg-open', target])}")
    try:
        result = subprocess.run(
            ["xdg-open", target],
            check=False,
            capture_output=True,
            text=True,
            errors="replace",
            timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        logger.log(f"open_target={label}:error:{exc!r}")
        return "warn", f"{label.lower()} open failed: {target}"

    logger.log(f"exit_code={result.returncode}")
    if result.stdout.strip():
        for line in result.stdout.splitlines():
            logger.log(f"stdout {line}")
    if result.stderr.strip():
        for line in result.stderr.splitlines():
            logger.log(f"stderr {line}")

    if result.returncode == 0:
        return "ok", f"{label.lower()} opened"
    return "warn", f"{label.lower()} open failed: {target}"


def launch_child_tool(root: Path, tool_name: str, logger: SessionLogger) -> int:
    command = resolve_tool_command(root, tool_name)
    if command is None:
        logger.log(f"launch_tool={tool_name}:missing")
        return 1

    logger.log(f"launch_tool={tool_name}")
    logger.log(f"command={shell_join(command)}")

    process = subprocess.Popen(command)
    previous_handler = signal.getsignal(signal.SIGINT)
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    try:
        exit_code = process.wait()
    finally:
        signal.signal(signal.SIGINT, previous_handler)

    logger.log(f"child_exit_code={exit_code}")
    return exit_code


def render_menu(console: KeskConsole, logger: SessionLogger, root: Path, notice: MenuNotice | None) -> None:
    upgrade_ready = tool_ready(root, "upgrade")
    doctor_ready = tool_ready(root, "doctor")
    repair_ready = tool_ready(root, "repair")

    console.clear()
    console.header("KESK CONTROL CENTER", "SYSTEM TOOLS // DESKTOP STACK // MAINTENANCE CONSOLE")
    console.line()
    console.status("ok" if upgrade_ready else "warn", "system upgrade tool ready" if upgrade_ready else "system upgrade tool missing")
    console.status("ok" if doctor_ready else "warn", "system doctor tool ready" if doctor_ready else "system doctor tool missing")
    console.status("ok" if repair_ready else "warn", "repair console ready" if repair_ready else "repair console missing")
    console.line()
    console.status("ok", f"session log: {logger.path}")
    if notice is not None:
        console.status(notice.kind, notice.message)
    console.line()
    console.menu(
        [
            "[1] System Upgrade",
            "[2] System Doctor",
            "[3] Repair Console",
            "[4] About KeskOS",
            "[5] Open Logs Directory",
            "[6] Open Backups Directory",
            "[7] Open Documentation",
            "[8] Exit",
        ]
    )


def render_about(console: KeskConsole, root: Path, paths: ControlPaths) -> None:
    console.clear()
    console.header("KESK CONTROL CENTER", "ABOUT KESKOS")
    console.line()
    for label, value in about_rows(root, paths):
        console.line(f"{label:<18} {value}")
    console.line()
    console.pause("Press Enter to return to the menu")


def open_logs_directory(console: KeskConsole, logger: SessionLogger, paths: ControlPaths) -> None:
    console.clear()
    console.header("KESK CONTROL CENTER", "OPEN LOGS DIRECTORY")
    console.line()
    kind, message = open_target(logger, str(paths.logs_dir), "Logs directory")
    console.status(kind, message)
    if kind != "ok":
        console.line(str(paths.logs_dir))
    console.line()
    console.pause("Press Enter to return to the menu")


def open_backups_directory(console: KeskConsole, logger: SessionLogger, paths: ControlPaths) -> None:
    console.clear()
    console.header("KESK CONTROL CENTER", "OPEN BACKUPS DIRECTORY")
    console.line()
    kind, message = open_target(logger, str(paths.backups_dir), "Backups directory")
    console.status(kind, message)
    if kind != "ok":
        console.line(str(paths.backups_dir))
    console.line()
    console.pause("Press Enter to return to the menu")


def open_documentation(console: KeskConsole, logger: SessionLogger) -> None:
    if not command_exists("xdg-open"):
        console.clear()
        console.header("KESK CONTROL CENTER", "DOCUMENTATION LINKS")
        console.line()
        console.status("skip", "xdg-open not installed; listing links instead")
        console.line()
        for label, link in DOC_LINKS:
            console.line(f"{label:<10} {link}")
        console.line()
        console.pause("Press Enter to return to the menu")
        return

    while True:
        console.clear()
        console.header("KESK CONTROL CENTER", "DOCUMENTATION LINKS")
        console.line()
        for index, (label, link) in enumerate(DOC_LINKS, start=1):
            console.line(f"[{index}] {label} - {link}")
        console.line("[5] Back")
        console.line()

        choice = console.input("Select destination").strip()
        if choice == "5":
            logger.log("selected_action=documentation_back")
            return

        mapping = {str(index): (label, link) for index, (label, link) in enumerate(DOC_LINKS, start=1)}
        if choice not in mapping:
            console.status("warn", "invalid selection")
            console.pause()
            continue

        label, link = mapping[choice]
        logger.log(f"selected_action=open_documentation:{label.lower()}")
        kind, message = open_target(logger, link, label)
        console.line()
        console.status(kind, message)
        if kind != "ok":
            console.line(link)
        console.line()
        console.pause("Press Enter to return to documentation links")


def print_help(console: KeskConsole) -> int:
    console.header("KESK CONTROL CENTER", "CENTRAL LAUNCHER FOR KESK TOOLS")
    console.line("Usage: kesk settings")
    console.line()
    console.line("In graphical sessions, `kesk settings` launches the Qt-based Kesk Settings GUI.")
    console.line("Use `kesk settings --tui` or run without a display to open this terminal fallback.")
    console.line()
    console.line("Launches:")
    console.line("- kesk upgrade")
    console.line("- kesk doctor")
    console.line("- kesk repair")
    console.line()
    console.line("Also shows basic KeskOS build info and opens logs, backups, and docs links.")
    console.line("This tool does not change system settings directly.")
    return 0


def build_paths(logger: SessionLogger) -> ControlPaths:
    preferred_logs_dir = Path.home() / ".local" / "state" / "kesk" / "logs"
    preferred_backups_dir = Path.home() / ".local" / "state" / "kesk" / "backups"

    try:
        ensure_directory(preferred_logs_dir)
        logs_dir = preferred_logs_dir
    except OSError:
        if isinstance(logger.path, Path):
            logs_dir = logger.path.parent
        else:
            logs_dir = preferred_logs_dir

    try:
        backups_dir = ensure_directory(preferred_backups_dir)
    except OSError:
        backups_dir = preferred_backups_dir

    return ControlPaths(logs_dir=logs_dir, backups_dir=backups_dir)


def launch_selected_tool(
    console: KeskConsole,
    logger: SessionLogger,
    root: Path,
    tool_name: str,
    label: str,
) -> MenuNotice:
    console.clear()
    console.header("KESK CONTROL CENTER", f"LAUNCHING {label}")
    console.line()
    console.status("work", f"launching {label.lower()}")
    exit_code = launch_child_tool(root, tool_name, logger)
    if exit_code == 0:
        return MenuNotice("ok", f"{label.lower()} exited cleanly")
    return MenuNotice("warn", f"{label.lower()} returned exit code {exit_code}")


def main(args: Sequence[str], root: Path) -> int:
    console = KeskConsole()
    if args and args[0] in {"--help", "-h", "help"}:
        return print_help(console)

    logger = SessionLogger("settings")
    paths = build_paths(logger)
    notice: MenuNotice | None = None
    overall_exit_code = 0

    try:
        while True:
            render_menu(console, logger, root, notice)
            notice = None

            try:
                choice = console.input("Select action").strip()
            except EOFError:
                logger.log("selected_action=eof_exit")
                return overall_exit_code

            if choice == "8":
                logger.log("selected_action=exit")
                logger.log(f"final_status=completed:{overall_exit_code}")
                return overall_exit_code

            if choice == "1":
                logger.log("selected_action=launch_upgrade")
                notice = launch_selected_tool(console, logger, root, "upgrade", "SYSTEM UPGRADE")
                if notice.kind == "warn":
                    overall_exit_code = 2
                continue

            if choice == "2":
                logger.log("selected_action=launch_doctor")
                notice = launch_selected_tool(console, logger, root, "doctor", "SYSTEM DOCTOR")
                if notice.kind == "warn":
                    overall_exit_code = 2
                continue

            if choice == "3":
                logger.log("selected_action=launch_repair")
                notice = launch_selected_tool(console, logger, root, "repair", "REPAIR CONSOLE")
                if notice.kind == "warn":
                    overall_exit_code = 2
                continue

            if choice == "4":
                logger.log("selected_action=about")
                render_about(console, root, paths)
                continue

            if choice == "5":
                logger.log("selected_action=open_logs_directory")
                open_logs_directory(console, logger, paths)
                continue

            if choice == "6":
                logger.log("selected_action=open_backups_directory")
                open_backups_directory(console, logger, paths)
                continue

            if choice == "7":
                logger.log("selected_action=open_documentation")
                open_documentation(console, logger)
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
        console.header("KESK CONTROL CENTER", "ERROR")
        console.status("warn", f"settings failed: {exc}")
        return 1
    finally:
        logger.close()
