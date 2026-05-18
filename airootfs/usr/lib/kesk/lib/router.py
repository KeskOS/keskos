from __future__ import annotations

import os
from pathlib import Path
from typing import Sequence

from common import APP_VERSION, KeskConsole


HELP_ROWS = (
    ("kesk help", "Show the command router help."),
    ("kesk version", "Show the current Kesk tool version."),
    ("kesk upgrade", "Update KeskOS packages."),
    ("kesk doctor", "Check system health."),
    ("kesk repair", "Repair KeskOS desktop and theme stack."),
    ("kesk settings", "Open the KeskOS control center."),
)


def show_help(console: KeskConsole, error: str | None = None) -> int:
    console.clear()
    console.header("KESK SYSTEM TOOLS", "BASE COMMAND ROUTER")
    if error:
        console.status("warn", error)
        console.line()
    console.table("AVAILABLE COMMANDS", HELP_ROWS)
    console.line()
    console.muted("Unknown commands fall back to this help screen.")
    return 0 if error is None else 1


def show_version(console: KeskConsole) -> int:
    console.line(f"kesk {APP_VERSION}")
    return 0


def exec_command(command_path: Path, extra_args: Sequence[str]) -> int:
    os.execv(str(command_path), [str(command_path), *extra_args])
    return 1


def main(args: Sequence[str], root: Path) -> int:
    console = KeskConsole()
    upgrade_path = root / "commands" / "upgrade"
    doctor_path = root / "commands" / "doctor"
    repair_path = root / "commands" / "repair"
    settings_path = root / "commands" / "settings"
    gui_settings_path = root.parents[1] / "bin" / "kesk-settings"

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
        if extra_args and extra_args[0] == "--tui":
            return exec_command(settings_path, extra_args[1:])
        if extra_args and extra_args[0] == "--gui":
            if gui_settings_path.exists():
                return exec_command(gui_settings_path, extra_args[1:])
            return show_help(console, "kesk-settings is missing from /usr/bin.")
        if (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")) and gui_settings_path.exists():
            return exec_command(gui_settings_path, extra_args)
        return exec_command(settings_path, extra_args)

    return show_help(console, f"unknown command: {command}")
