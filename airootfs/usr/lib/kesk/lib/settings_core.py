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
    console.status("ok" if report["plasma_session_detected"] else "warn", f"plasma session detected: {'yes' if report['plasma_session_detected'] else 'no'}")
    console.status("ok" if report["graphical_session_available"] else "warn", f"graphical session available: {'yes' if report['graphical_session_available'] else 'no'}")
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
    console.line()
    console.section("PRIVILEGED")
    console.status("ok" if report["policy_present"] else "warn", f"polkit policy present: {'yes' if report['policy_present'] else 'no'}")
    console.line()
    console.section("NOTIFICATIONS")
    notifications = report["notifications_runtime"]
    console.status("ok", f"runtime notifier: {notifications['runtime_notifier']}")
    console.status("ok" if notifications["running"] else "warn", f"dunst running: {'yes' if notifications['running'] else 'no'}")
    console.status("ok" if notifications["config_writable"] else "warn", f"dunstrc path: {notifications['config_path']}")
    if notifications["dnd_supported"]:
        console.status(
            "ok" if notifications["do_not_disturb"] else "work",
            f"do not disturb: {'enabled' if notifications['do_not_disturb'] else 'disabled'}",
        )
    else:
        console.status("skip", "do not disturb: unavailable")
    console.line()
    console.section("BACKENDS")
    for name, payload in sorted(report["backend_statuses"].items()):
        code = payload["code"]
        kind = {
            "connected": "ok",
            "limited": "work",
            "kde_handoff": "work",
            "intentional_handoff": "work",
            "missing": "skip",
            "requires_admin": "warn",
        }.get(code, "skip")
        console.status(kind, f"{name}: {payload['summary']}")
        if payload["missing_tools"]:
            console.line(f"    missing tools: {', '.join(payload['missing_tools'])}")
        if payload["admin_required"]:
            console.line("    requires admin permission")
    console.line()
    console.section("LIMITATIONS / HANDOFF MATRIX")
    matrix = report["limitations_matrix"]
    console.line("Notifications:")
    console.line(f"- runtime notifier: {matrix['notifications']['runtime_notifier']}")
    console.line(f"- dunst found: {'yes' if matrix['notifications']['dunst_found'] else 'no'}")
    console.line(f"- dunstctl found: {'yes' if matrix['notifications']['dunstctl_found'] else 'no'}")
    console.line(f"- notify-send found: {'yes' if matrix['notifications']['notify_send_found'] else 'no'}")
    console.line(f"- dunst running: {'yes' if matrix['notifications']['dunst_running'] else 'no'}")
    console.line(f"- possible Plasma duplicate risk: {'yes' if matrix['notifications']['possible_plasma_duplicate_risk'] else 'no'}")
    console.line(f"- per-app rules: {matrix['notifications']['per_app_rules']}")
    console.line()
    console.line("Accessibility:")
    console.line(f"- direct backend: {matrix['accessibility']['direct_backend']}")
    console.line(f"- advanced controls: {matrix['accessibility']['advanced_controls']}")
    console.line()
    console.line("Online Accounts:")
    console.line(f"- backend: {matrix['online_accounts']['backend']}")
    console.line()
    console.line("Task Switcher:")
    console.line(f"- backend: {matrix['task_switcher']['backend']}")
    console.line()
    console.line("Display:")
    console.line(f"- backend: {matrix['display']['backend']}")
    console.line(f"- reason: {matrix['display']['reason']}")
    console.line()
    console.line("Boot & Login:")
    console.line(f"- pkexec found: {'yes' if matrix['boot_login']['pkexec_found'] else 'no'}")
    console.line(f"- helper found: {'yes' if matrix['boot_login']['helper_found'] else 'no'}")
    console.line(f"- SDDM assets found: {'yes' if matrix['boot_login']['sddm_assets_found'] else 'no'}")
    console.line(f"- Plymouth found: {'yes' if matrix['boot_login']['plymouth_found'] else 'no'}")
    console.line(f"- bootloader detected: {matrix['boot_login']['bootloader_detected']}")
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
