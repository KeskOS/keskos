from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
from typing import Sequence

from common import APP_VERSION, KeskConsole, branded_header_title, branding_version_rows, load_branding


HELP_ROWS = (
    ("kesk help", "Show the command router help."),
    ("kesk version", "Show the current KeskOS release branding."),
    ("kesk upgrade", "Update KeskOS packages."),
    ("kesk doctor", "Check system health."),
    ("kesk repair", "Repair KeskOS desktop and theme stack."),
    ("kesk settings", "Open KDE System Settings with KeskOS branding."),
    ("kesk welcome", "Open Kesk Welcome manually."),
    ("kesk welcome-rerun", "Open Kesk Welcome even when the first-run marker exists."),
    ("kesk refresh-branding", "Refresh KeskOS branding metadata and os-release."),
)


def show_help(console: KeskConsole, error: str | None = None) -> int:
    console.clear()
    console.header(branded_header_title("Command Router"), "BASE COMMAND ROUTER")
    if error:
        console.status("warn", error)
        console.line()
    console.table("AVAILABLE COMMANDS", HELP_ROWS)
    console.line()
    console.muted("Unknown commands fall back to this help screen.")
    return 0 if error is None else 1


def show_version(console: KeskConsole) -> int:
    branding = load_branding()
    console.line(branding.brand_line)
    for label, value in branding_version_rows()[1:]:
        console.line(f"{label}: {value}")
    console.line(f"Tool version: {APP_VERSION}")
    return 0


def exec_command(command_path: Path, extra_args: Sequence[str]) -> int:
    if os.name == "nt" or not os.access(command_path, os.X_OK):
        return subprocess.call([sys.executable, str(command_path), *extra_args])
    os.execv(str(command_path), [str(command_path), *extra_args])
    return 1


def main(args: Sequence[str], root: Path) -> int:
    console = KeskConsole()
    upgrade_path = root / "commands" / "upgrade"
    doctor_path = root / "commands" / "doctor"
    repair_path = root / "commands" / "repair"
    settings_path = root / "commands" / "settings"
    welcome_path = root / "commands" / "welcome"
    refresh_branding_path = root / "commands" / "refresh-branding"

    if not args:
        return show_help(console)

    command = args[0]
    extra_args = list(args[1:])

    if command in {"help", "--help", "-h"}:
        if extra_args and extra_args[0] == "upgrade" and upgrade_path.exists():
            return exec_command(upgrade_path, ["--help"])
        if extra_args and extra_args[0] == "doctor" and doctor_path.exists():
            return exec_command(doctor_path, ["--help"])
        if extra_args and extra_args[0] == "repair" and repair_path.exists():
            return exec_command(repair_path, ["--help"])
        if extra_args and extra_args[0] == "settings" and settings_path.exists():
            return exec_command(settings_path, ["--help"])
        if extra_args and extra_args[0] == "welcome" and welcome_path.exists():
            return exec_command(welcome_path, ["--help"])
        if extra_args and extra_args[0] == "refresh-branding" and refresh_branding_path.exists():
            return exec_command(refresh_branding_path, ["--help"])
        return show_help(console)

    if command in {"version", "--version", "-V"}:
        return show_version(console)

    if command == "upgrade":
        if not upgrade_path.exists():
            return show_help(console, "upgrade command is missing from /usr/lib/kesk/commands.")
        return exec_command(upgrade_path, extra_args)

    if command == "doctor":
        if not doctor_path.exists():
            return show_help(console, "doctor command is missing from /usr/lib/kesk/commands.")
        return exec_command(doctor_path, extra_args)

    if command == "repair":
        if not repair_path.exists():
            return show_help(console, "repair command is missing from /usr/lib/kesk/commands.")
        return exec_command(repair_path, extra_args)

    if command == "settings":
        if not settings_path.exists():
            return show_help(console, "settings command is missing from /usr/lib/kesk/commands.")
        return exec_command(settings_path, extra_args)

    if command == "welcome":
        if not welcome_path.exists():
            return show_help(console, "welcome command is missing from /usr/lib/kesk/commands.")
        return exec_command(welcome_path, extra_args)

    if command == "welcome-rerun":
        if not welcome_path.exists():
            return show_help(console, "welcome command is missing from /usr/lib/kesk/commands.")
        return exec_command(welcome_path, ["--rerun", *extra_args])

    if command == "refresh-branding":
        if not refresh_branding_path.exists():
            return show_help(console, "refresh-branding command is missing from /usr/lib/kesk/commands.")
        return exec_command(refresh_branding_path, extra_args)

    return show_help(console, f"unknown command: {command}")
