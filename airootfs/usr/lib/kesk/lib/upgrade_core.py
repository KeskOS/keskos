from __future__ import annotations

from dataclasses import dataclass, field
import json
import os
from pathlib import Path
import re
import shutil
import sys
from typing import Iterable, Sequence

from common import KeskConsole, SessionLogger, branded_header_title, run_capture, shell_join, stream_command

PACMAN_LOCK_PATH = Path(os.environ.get("KESK_PACMAN_LOCK_PATH", "/var/lib/pacman/db.lck"))
REBOOT_REQUIRED_PATH = Path(os.environ.get("KESK_REBOOT_REQUIRED_PATH", "/var/run/reboot-required"))
PACMAN_CONF_PATH = Path(os.environ.get("KESK_PACMAN_CONF_PATH", "/etc/pacman.conf"))
PACMAN_MIRRORLIST_PATH = Path(os.environ.get("KESK_PACMAN_MIRRORLIST_PATH", "/etc/pacman.d/mirrorlist"))


@dataclass
class UpdateSource:
    key: str
    label: str
    tool_label: str
    available: bool = False
    unavailable_reason: str = ""
    detection_note: str = ""
    check_note: str = ""
    blocked_reason: str = ""
    error: str = ""
    count: int = 0
    items: list[str] = field(default_factory=list)
    upgrade_command: list[str] = field(default_factory=list)
    ran_upgrade: bool = False
    upgrade_exit_code: int | None = None

    def can_upgrade(self) -> bool:
        return self.available and not self.blocked_reason and bool(self.upgrade_command)


@dataclass
class UpgradeState:
    pacman_lock_detected: bool
    sources: dict[str, UpdateSource]

    def source(self, key: str) -> UpdateSource:
        return self.sources[key]


def command_exists(name: str) -> bool:
    return shutil.which(name) is not None


def clean_lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


def parse_generic_updates(output: str) -> list[str]:
    return clean_lines(output)


def parse_flatpak_updates(output: str) -> list[str]:
    lines = []
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
            if version:
                lines.append(f"{name} / {app_id} / {version}")
            else:
                lines.append(f"{name} / {app_id}")
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
            if release_name:
                items.append(f"{device_name} / {release_name}")
            else:
                items.append(str(device_name))


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
        if not stripped:
            continue
        if stripped.endswith(":"):
            continue
        if stripped.startswith(("See ", "Devices with no available firmware updates")):
            continue
        if stripped.startswith(("├─", "└─", "│", "•")):
            candidate = stripped.lstrip("├─└│• ").strip()
            if not candidate:
                continue
            if re.match(r"^(Current version|Vendor|GUID|Device Flags|Checksum|Summary|Branch|Remote ID)\b", candidate):
                continue
            items.append(candidate)
    return dedupe(items)


def dedupe(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered


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
        if current_section not in sync_sections:
            continue
        if line.startswith("Server ="):
            return True

    return False


def pacman_repositories_configured() -> bool:
    if file_has_server_entries(PACMAN_MIRRORLIST_PATH):
        return True
    return pacman_conf_has_sync_servers(PACMAN_CONF_PATH)


def completed_to_count(source: UpdateSource, result_stdout: str, result_stderr: str, result_code: int, parser) -> None:
    items = parser(result_stdout)
    if items:
        source.items = items
        source.count = len(items)
        return

    if result_code == 0:
        source.count = 0
        return

    stderr_lines = clean_lines(result_stderr)
    if result_code in {1, 2} and not stderr_lines:
        source.count = 0
        return

    if result_stdout.strip() and not stderr_lines:
        source.items = clean_lines(result_stdout)
        source.count = len(source.items)
        return

    source.error = stderr_lines[0] if stderr_lines else f"check exited with code {result_code}"


def check_official(source: UpdateSource, logger: SessionLogger, pacman_lock_detected: bool) -> None:
    source.available = command_exists("pacman")
    if not source.available:
        source.unavailable_reason = "pacman support unavailable: pacman not installed"
        return

    source.detection_note = "pacman detected"
    if command_exists("checkupdates"):
        source.check_note = "checkupdates detected"
        check_command = ["checkupdates"]
    else:
        source.check_note = "checkupdates unavailable: using pacman -Qu fallback"
        check_command = ["pacman", "-Qu"]

    source.upgrade_command = ["sudo", "pacman", "-Syu"]

    if pacman_lock_detected:
        source.blocked_reason = f"pacman database lock detected: {PACMAN_LOCK_PATH}"
        return

    if not pacman_repositories_configured():
        source.blocked_reason = (
            "pacman repositories are not configured; check /etc/pacman.conf and /etc/pacman.d/mirrorlist"
        )
        return

    result = run_capture(check_command, logger)
    completed_to_count(source, result.stdout, result.stderr, result.returncode, parse_generic_updates)


def check_aur(source: UpdateSource, logger: SessionLogger, pacman_lock_detected: bool) -> None:
    source.available = command_exists("yay")
    if not source.available:
        source.unavailable_reason = "AUR support unavailable: yay not installed"
        return

    source.detection_note = "yay detected"
    source.upgrade_command = ["yay", "-Syu"]

    if pacman_lock_detected:
        source.blocked_reason = "AUR checks skipped while pacman lock is present"
        return

    if not pacman_repositories_configured():
        source.blocked_reason = "AUR upgrades unavailable until pacman repositories are configured"
        return

    result = run_capture(["yay", "-Qua"], logger)
    completed_to_count(source, result.stdout, result.stderr, result.returncode, parse_generic_updates)


def check_flatpak(source: UpdateSource, logger: SessionLogger) -> None:
    source.available = command_exists("flatpak")
    if not source.available:
        source.unavailable_reason = "Flatpak support unavailable: flatpak not installed"
        return

    source.detection_note = "flatpak detected"
    source.upgrade_command = ["flatpak", "update"]
    result = run_capture(
        ["flatpak", "remote-ls", "--updates", "--columns=name,application,version"],
        logger,
    )
    completed_to_count(source, result.stdout, result.stderr, result.returncode, parse_flatpak_updates)


def check_firmware(source: UpdateSource, logger: SessionLogger) -> None:
    source.available = command_exists("fwupdmgr")
    if not source.available:
        source.unavailable_reason = "Firmware support unavailable: fwupd not installed"
        return

    source.detection_note = "fwupdmgr detected"
    source.upgrade_command = ["sudo", "fwupdmgr", "update"]

    json_result = run_capture(["fwupdmgr", "get-updates", "--json"], logger)
    if json_result.returncode == 0 and json_result.stdout.strip():
        try:
            source.items = parse_fwupd_json(json_result.stdout)
            source.count = len(source.items)
            return
        except json.JSONDecodeError:
            source.error = ""

    result = run_capture(["fwupdmgr", "get-updates"], logger)
    completed_to_count(source, result.stdout, result.stderr, result.returncode, parse_fwupd_plain)


def refresh_state(logger: SessionLogger) -> UpgradeState:
    pacman_lock_detected = PACMAN_LOCK_PATH.exists()
    logger.log(f"pacman_lock_detected={str(pacman_lock_detected).lower()}")

    sources = {
        "official": UpdateSource(key="official", label="OFFICIAL REPOS", tool_label="pacman"),
        "aur": UpdateSource(key="aur", label="AUR", tool_label="yay"),
        "flatpak": UpdateSource(key="flatpak", label="FLATPAK", tool_label="flatpak"),
        "firmware": UpdateSource(key="firmware", label="FIRMWARE", tool_label="fwupdmgr"),
    }

    check_official(sources["official"], logger, pacman_lock_detected)
    check_aur(sources["aur"], logger, pacman_lock_detected)
    check_flatpak(sources["flatpak"], logger)
    check_firmware(sources["firmware"], logger)

    for source in sources.values():
        logger.log(f"{source.key}_available={str(source.available).lower()}")
        logger.log(f"{source.key}_count={source.count}")
        if source.blocked_reason:
            logger.log(f"{source.key}_blocked={source.blocked_reason}")
        if source.error:
            logger.log(f"{source.key}_error={source.error}")

    return UpgradeState(pacman_lock_detected=pacman_lock_detected, sources=sources)


def render_source_status(console: KeskConsole, source: UpdateSource) -> None:
    if source.available:
        console.status("ok", source.detection_note)
    else:
        console.status("warn", source.unavailable_reason)
        return

    if source.check_note:
        prefix = "warn" if "fallback" in source.check_note else "ok"
        console.status(prefix, source.check_note)

    if source.blocked_reason:
        kind = "warn" if "lock" in source.blocked_reason else "skip"
        console.status(kind, source.blocked_reason)
        return

    if source.error:
        console.status("warn", f"{source.label.lower()} check failed: {source.error}")
        return

    console.status("ok", f"{source.label.lower()} updates: {source.count}")


def render_dashboard(console: KeskConsole, state: UpgradeState, logger: SessionLogger) -> None:
    console.clear()
    console.header(branded_header_title("Upgrade Console"), "OFFICIAL REPOS // AUR // FLATPAK // FWUPD")
    console.line()
    for key in ("official", "aur", "flatpak", "firmware"):
        render_source_status(console, state.source(key))
    console.line()
    console.status("ok", f"session log: {logger.path}")
    console.line()
    console.menu(
        [
            "[1] Upgrade everything",
            "[2] Upgrade official packages only",
            "[3] Upgrade AUR packages only",
            "[4] Upgrade Flatpak packages only",
            "[5] Upgrade firmware only",
            "[6] View package list",
            "[7] Refresh checks",
            "[8] Exit",
        ]
    )


def render_package_list(console: KeskConsole, state: UpgradeState) -> None:
    console.clear()
    console.header(branded_header_title("Package List"), "CURRENTLY DETECTED UPDATE CANDIDATES")

    for key in ("official", "aur", "flatpak", "firmware"):
        source = state.source(key)
        console.section(source.label)
        if not source.available:
            console.status("warn", source.unavailable_reason)
            continue
        if source.blocked_reason:
            console.status("skip", source.blocked_reason)
            continue
        if source.error:
            console.status("warn", source.error)
            continue
        if not source.items:
            console.status("ok", "no updates detected")
            continue
        for item in source.items:
            console.line(f"- {item}")
    console.line()
    console.pause()


def source_payload(source: UpdateSource, *, include_items: bool) -> dict[str, object]:
    payload: dict[str, object] = {
        "key": source.key,
        "label": source.label,
        "tool_label": source.tool_label,
        "available": source.available,
        "unavailable_reason": source.unavailable_reason,
        "detection_note": source.detection_note,
        "check_note": source.check_note,
        "blocked_reason": source.blocked_reason,
        "error": source.error,
        "count": source.count,
        "can_upgrade": source.can_upgrade(),
        "upgrade_command": source.upgrade_command,
    }
    if include_items:
        payload["items"] = source.items
    return payload


def state_payload(state: UpgradeState, *, include_items: bool) -> dict[str, object]:
    return {
        "pacman_lock_detected": state.pacman_lock_detected,
        "pacman_repositories_configured": pacman_repositories_configured(),
        "reboot_recommended": reboot_recommended(state),
        "sources": {
            key: source_payload(source, include_items=include_items)
            for key, source in state.sources.items()
        },
    }


def print_json_payload(payload: dict[str, object]) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def describe_selection(selected: Sequence[UpdateSource]) -> list[str]:
    descriptions = []
    for source in selected:
        if source.error:
            descriptions.append(f"{source.label}: status unknown, upgrade still available")
            continue
        descriptions.append(f"{source.label}: {source.count} update(s) queued")
    return descriptions


def choose_sources(choice: str, state: UpgradeState) -> tuple[list[UpdateSource], int]:
    mapping = {
        "1": ["official", "aur", "flatpak", "firmware"],
        "2": ["official"],
        "3": ["aur"],
        "4": ["flatpak"],
        "5": ["firmware"],
    }
    keys = mapping.get(choice, [])

    selected: list[UpdateSource] = []
    blocked_due_to_lock = False
    for key in keys:
        source = state.source(key)
        if source.can_upgrade():
            selected.append(source)
            continue
        if state.pacman_lock_detected and key in {"official", "aur"}:
            blocked_due_to_lock = True

    if not selected and blocked_due_to_lock:
        return [], 3

    return selected, 0


def reboot_recommended(state: UpgradeState) -> bool:
    if REBOOT_REQUIRED_PATH.exists():
        return True

    if state.source("firmware").ran_upgrade and state.source("firmware").upgrade_exit_code == 0 and state.source("firmware").count > 0:
        return True

    watched_prefixes = (
        "linux",
        "systemd",
        "mesa",
        "lib32-mesa",
        "nvidia",
        "linux-firmware",
    )

    for key in ("official", "aur"):
        source = state.source(key)
        if not source.ran_upgrade or source.upgrade_exit_code != 0:
            continue
        for item in source.items:
            package_name = item.split()[0].lower()
            if package_name.startswith(watched_prefixes):
                return True
    return False


def perform_upgrade(
    console: KeskConsole,
    logger: SessionLogger,
    state: UpgradeState,
    selected: Sequence[UpdateSource],
    *,
    prompt_for_confirmation: bool = True,
) -> int:
    console.clear()
    console.header(branded_header_title("Upgrade Console"), "EXECUTION PLAN")
    for description in describe_selection(selected):
        console.status("ok", description)
    console.line()

    if prompt_for_confirmation:
        if not console.confirm("Continue with selected upgrade?", default=False):
            logger.log("selected_action=cancelled")
            console.status("skip", "upgrade cancelled by user")
            console.pause()
            return 0

    logger.log("selected_action=" + ",".join(source.key for source in selected))
    overall_code = 0

    console.clear()
    console.header(branded_header_title("Upgrade Console"), "LIVE COMMAND OUTPUT")
    for source in selected:
        console.section(f"RUNNING {source.label}")
        console.muted(shell_join(source.upgrade_command))
        source.ran_upgrade = True
        exit_code = stream_command(source.upgrade_command, logger, console)
        source.upgrade_exit_code = exit_code
        if exit_code == 0:
            console.status("ok", f"{source.label.lower()} upgrade finished successfully")
        else:
            console.status("warn", f"{source.label.lower()} upgrade failed with exit code {exit_code}")
            overall_code = 2
        console.line()

    console.section("FINAL STATUS")
    for source in selected:
        if source.upgrade_exit_code == 0:
            console.status("ok", f"{source.label.lower()} complete")
        else:
            console.status("warn", f"{source.label.lower()} failed")

    if reboot_recommended(state):
        console.status("warn", "reboot recommended")
    else:
        console.status("ok", "reboot not required")

    logger.log(f"final_status={'success' if overall_code == 0 else 'failed'}")
    console.line()
    console.pause("Press Enter to return to the menu")
    return overall_code


def print_help(console: KeskConsole) -> int:
    console.header(branded_header_title("Upgrade Console"), "INTERACTIVE UPDATE MANAGER")
    console.line("Usage: kesk upgrade")
    console.line("       kesk upgrade --check --json")
    console.line("       kesk upgrade --list --json")
    console.line("       kesk upgrade --all|--official|--aur|--flatpak|--firmware [--yes]")
    console.line()
    console.line("Checks and upgrades:")
    console.line("- pacman official repositories")
    console.line("- yay / AUR when yay is installed")
    console.line("- Flatpak when flatpak is installed")
    console.line("- fwupd firmware updates when fwupdmgr is installed")
    console.line("- `--yes` only skips the Kesk confirmation prompt; package managers still ask normally")
    return 0


def choose_sources_from_keys(keys: Sequence[str], state: UpgradeState) -> tuple[list[UpdateSource], int]:
    selected: list[UpdateSource] = []
    blocked_due_to_lock = False
    for key in keys:
        source = state.source(key)
        if source.can_upgrade():
            selected.append(source)
            continue
        if state.pacman_lock_detected and key in {"official", "aur"}:
            blocked_due_to_lock = True

    if not selected and blocked_due_to_lock:
        return [], 3
    return selected, 0


def run_json_mode(logger: SessionLogger, *, include_items: bool) -> int:
    state = refresh_state(logger)
    print_json_payload(state_payload(state, include_items=include_items))
    return 0


def run_direct_action(
    console: KeskConsole,
    logger: SessionLogger,
    action_flag: str,
    *,
    auto_confirm: bool,
) -> int:
    mapping = {
        "--all": ["official", "aur", "flatpak", "firmware"],
        "--official": ["official"],
        "--aur": ["aur"],
        "--flatpak": ["flatpak"],
        "--firmware": ["firmware"],
    }
    state = refresh_state(logger)
    selected, selection_code = choose_sources_from_keys(mapping[action_flag], state)
    if not selected:
        if selection_code == 3:
            console.header(branded_header_title("Upgrade Console"), "SAFETY CHECK")
            console.status("warn", f"pacman lock detected at {PACMAN_LOCK_PATH}")
            return 3
        console.header(branded_header_title("Upgrade Console"), "NO RUNNABLE SOURCES")
        console.status("warn", "no runnable update source is available for that selection")
        return 1

    return perform_upgrade(
        console,
        logger,
        state,
        selected,
        prompt_for_confirmation=not auto_confirm,
    )


def main(args: Sequence[str], _root: Path) -> int:
    console = KeskConsole()
    arg_set = set(args)

    if args and args[0] in {"--help", "-h", "help"}:
        return print_help(console)

    json_mode = "--json" in arg_set
    auto_confirm = "--yes" in arg_set
    action_flags = [flag for flag in ("--all", "--official", "--aur", "--flatpak", "--firmware") if flag in arg_set]

    if json_mode and "--list" in arg_set:
        logger = SessionLogger("upgrade")
        try:
            return run_json_mode(logger, include_items=True)
        finally:
            logger.close()

    if json_mode and "--check" in arg_set:
        logger = SessionLogger("upgrade")
        try:
            return run_json_mode(logger, include_items=False)
        finally:
            logger.close()

    if os.geteuid() == 0:
        console.header(branded_header_title("Upgrade Console"), "SAFETY CHECK")
        console.status("warn", "run `kesk upgrade` as a regular user so yay and sudo behave safely")
        return 1

    logger = SessionLogger("upgrade")
    last_exit_code = 0

    try:
        if action_flags:
            return run_direct_action(console, logger, action_flags[0], auto_confirm=auto_confirm)

        state = refresh_state(logger)

        if (
            state.pacman_lock_detected
            and not state.source("flatpak").can_upgrade()
            and not state.source("firmware").can_upgrade()
        ):
            render_dashboard(console, state, logger)
            console.line()
            console.status("warn", "no upgrade path is available until the pacman lock clears")
            logger.log("final_status=pacman_lock_blocked")
            return 3

        while True:
            render_dashboard(console, state, logger)
            try:
                choice = console.input("Select action").strip()
            except EOFError:
                logger.log("selected_action=eof_exit")
                return last_exit_code

            if choice == "8":
                logger.log("selected_action=exit")
                return last_exit_code

            if choice == "6":
                logger.log("selected_action=view_package_list")
                render_package_list(console, state)
                continue

            if choice == "7":
                logger.log("selected_action=refresh")
                console.status("work", "refreshing update checks")
                state = refresh_state(logger)
                last_exit_code = 0
                continue

            if choice not in {"1", "2", "3", "4", "5"}:
                console.status("warn", "invalid selection")
                console.pause()
                continue

            selected, selection_code = choose_sources(choice, state)
            if not selected:
                last_exit_code = selection_code
                if selection_code == 3:
                    console.status("warn", f"pacman lock detected at {PACMAN_LOCK_PATH}")
                else:
                    console.status("warn", "no runnable update source is available for that selection")
                console.pause()
                continue

            last_exit_code = perform_upgrade(console, logger, state, selected)
            state = refresh_state(logger)
    except KeyboardInterrupt:
        logger.log("final_status=interrupted")
        console.line()
        console.status("warn", "interrupted by user")
        return 130
    finally:
        logger.close()
