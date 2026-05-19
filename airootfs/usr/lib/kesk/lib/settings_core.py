from __future__ import annotations

import os
from pathlib import Path
from typing import Sequence

from common import KeskConsole, SessionLogger
from gui.settings.backend import SettingsBackend, resolve_runtime_paths


def has_graphical_session() -> bool:
    return bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))


def print_help(console: KeskConsole, error: str | None = None) -> int:
    console.clear()
    console.header("KESK SETTINGS", "GRAPHICAL KDE + KESKOS SETTINGS APPLICATION")
    console.line()
    if error:
        console.status("warn", error)
        console.line()
    console.line("Usage:")
    console.line("kesk settings")
    console.line("kesk settings --dry-run")
    console.line()
    console.line("What it does:")
    console.line("- Opens the graphical Kesk Settings app in a KDE graphical session")
    console.line("- Changes KDE Plasma user settings where implemented")
    console.line("- Stores KeskOS-specific preferences in ~/.config/kesk/settings.json")
    console.line("- Creates settings backups in ~/.local/state/kesk/settings-backups/")
    console.line()
    console.line("What it does not include:")
    console.line("- Repair tools")
    console.line("- Upgrade dashboards")
    console.line("- Docker or developer shortcuts")
    console.line("- Server or package-manager launchers")
    return 0 if error is None else 1


def print_requires_graphics(console: KeskConsole) -> int:
    console.clear()
    console.header("KESK SETTINGS", "GRAPHICAL SESSION REQUIRED")
    console.line()
    console.status("warn", "Kesk Settings requires a graphical session.")
    console.line("Run this from KDE Plasma on X11 or Wayland.")
    console.line("Use `kesk settings --dry-run` for backend detection details.")
    return 1


def print_dry_run(console: KeskConsole, backend: SettingsBackend) -> int:
    report = backend.dry_run_report()
    console.clear()
    console.header("KESK SETTINGS", "BACKEND DRY RUN")
    console.line()
    console.status("ok", f"session type: {report['session_type']}")
    console.status("ok", f"plasma version: {report['plasma_version']}")
    console.status("ok", f"qt version: {report['qt_version']}")
    console.line()
    console.section("SESSION")
    console.line(f"DISPLAY         {report['display'] or 'unset'}")
    console.line(f"WAYLAND_DISPLAY {report['wayland_display'] or 'unset'}")
    console.line()
    console.section("TOOLS")
    for name, present in sorted(report["tools"].items()):
        console.status("ok" if present else "skip", f"{name}: {'found' if present else 'missing'}")
    console.line()
    console.section("CONFIG PATHS")
    for name, path in report["config_paths"].items():
        writable = report["writable"].get(name, False)
        console.status("ok" if writable else "warn", f"{name}: {path}")
    return 0


def main(args: Sequence[str], root: Path) -> int:
    console = KeskConsole()
    if args and args[0] in {"--help", "-h", "help"}:
        return print_help(console)

    logger = SessionLogger("settings")
    backend = SettingsBackend(resolve_runtime_paths(root), logger)
    try:
        if args and args[0] == "--dry-run":
            return print_dry_run(console, backend)
        if args:
            return print_help(console, f"Unknown settings option: {' '.join(args)}")
        if not has_graphical_session():
            return print_requires_graphics(console)
        return print_help(console, "The graphical settings launcher should be started through `kesk settings` from the router or the desktop launcher.")
    finally:
        logger.close()
