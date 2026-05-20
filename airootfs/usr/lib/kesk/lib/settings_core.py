from __future__ import annotations

import configparser
import os
from pathlib import Path
import shutil
import subprocess
from typing import Sequence

from common import KeskConsole


OFFICIAL_COLOR_SCHEME = "KeskOSDark"
OFFICIAL_LAUNCHER = "kesk-settings.desktop"
UPSTREAM_LAUNCHER_OVERRIDE = "systemsettings.desktop"
EXPERIMENTAL_LAUNCHER = "keskos-settings.desktop"


def has_graphical_session() -> bool:
    return bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))


def command_path(name: str) -> str | None:
    return shutil.which(name)


def read_ini_value(path: Path, section: str, option: str) -> str | None:
    if not path.is_file():
        return None

    parser = configparser.ConfigParser(interpolation=None)
    parser.optionxform = str
    try:
        with path.open(encoding="utf-8", errors="replace") as handle:
            parser.read_file(handle)
    except (OSError, configparser.Error):
        return None

    if not parser.has_section(section):
        return None
    if not parser.has_option(section, option):
        return None
    return parser.get(section, option).strip()


def resolve_usr_root(root: Path) -> Path:
    return root.parents[1]


def resolve_source_root(root: Path) -> Path | None:
    candidates = [Path.cwd(), root, *root.parents]
    seen: set[Path] = set()

    for candidate in candidates:
        candidate = candidate.resolve()
        if candidate in seen:
            continue
        seen.add(candidate)
        if (candidate / "configs").is_dir() and (candidate / "desktop").is_dir():
            return candidate
    return None


def resolve_experimental_gui(root: Path) -> Path:
    return resolve_usr_root(root) / "bin" / "kesk-settings"


def launch_program(command: Sequence[str]) -> int:
    if os.name == "nt":
        return subprocess.call(list(command))
    os.execv(command[0], list(command))
    return 1


def first_existing_path(paths: Sequence[Path]) -> Path:
    for path in paths:
        if path.exists():
            return path
    return paths[0]


def show_help(console: KeskConsole, error: str | None = None) -> int:
    console.clear()
    console.header("KESK SETTINGS", "REAL KDE SYSTEM SETTINGS LAUNCHER")
    console.line()
    if error:
        console.status("warn", error)
        console.line()
    console.line("Usage:")
    console.line("kesk settings")
    console.line("kesk settings <kcm-module>")
    console.line("kesk settings --dry-run")
    console.line("kesk settings --experimental")
    console.line()
    console.line("What it does:")
    console.line("- Opens the real KDE System Settings application (`systemsettings`)")
    console.line("- Keeps KDE KCM pages intact instead of replacing them with a custom dashboard")
    console.line("- Passes an optional KCM module name through to System Settings")
    console.line("- Keeps the old custom Kesk Settings GUI hidden behind `--experimental`")
    console.line()
    console.line("Useful KDE commands:")
    console.line("- `kcmshell6 --list`")
    console.line("- `kcmshell6 <module-name>`")
    return 0 if error is None else 1


def show_requires_graphics(console: KeskConsole, label: str) -> int:
    console.clear()
    console.header("KESK SETTINGS", "GRAPHICAL SESSION REQUIRED")
    console.line()
    console.status("warn", f"{label} requires a graphical KDE session.")
    console.line("Run this from KDE Plasma on X11 or Wayland.")
    console.line("Use `kesk settings --dry-run` to inspect the installed launcher and theme wiring.")
    return 1


def print_dry_run(console: KeskConsole, root: Path) -> int:
    usr_root = resolve_usr_root(root)
    source_root = resolve_source_root(root)
    home = Path.home()
    kdeglobals = home / ".config" / "kdeglobals"
    kcminputrc = home / ".config" / "kcminputrc"
    launchers_dir = usr_root / "share" / "applications"
    local_launchers_dir = usr_root / "local" / "share" / "applications"
    color_dir = usr_root / "share" / "color-schemes"

    official_color_paths = [color_dir / f"{OFFICIAL_COLOR_SCHEME}.colors"]
    legacy_color_paths = [color_dir / "KESKOS.colors"]
    official_launcher_paths = [launchers_dir / OFFICIAL_LAUNCHER]
    upstream_override_paths = [local_launchers_dir / UPSTREAM_LAUNCHER_OVERRIDE, launchers_dir / UPSTREAM_LAUNCHER_OVERRIDE]
    experimental_launcher_paths = [launchers_dir / EXPERIMENTAL_LAUNCHER]

    if source_root is not None:
        official_color_paths.append(source_root / "configs" / "kde" / f"{OFFICIAL_COLOR_SCHEME}.colors")
        legacy_color_paths.append(source_root / "configs" / "kde" / "keskos.colors")
        official_launcher_paths.append(source_root / "desktop" / OFFICIAL_LAUNCHER)
        upstream_override_paths.append(source_root / "desktop" / UPSTREAM_LAUNCHER_OVERRIDE)
        experimental_launcher_paths.append(source_root / "desktop" / EXPERIMENTAL_LAUNCHER)

    console.clear()
    console.header("KESK SETTINGS", "SYSTEM SETTINGS DRY RUN")
    console.line()
    console.status("ok" if has_graphical_session() else "warn", f"graphical session available: {'yes' if has_graphical_session() else 'no'}")
    console.status("ok" if os.environ.get("XDG_CURRENT_DESKTOP") else "warn", f"desktop: {os.environ.get('XDG_CURRENT_DESKTOP') or 'unset'}")
    console.status("ok" if os.environ.get("XDG_SESSION_TYPE") else "warn", f"session type: {os.environ.get('XDG_SESSION_TYPE') or 'unset'}")
    console.line()
    console.section("TOOLS")
    for tool in ("systemsettings", "kcmshell6", "plasma-apply-colorscheme", "kwriteconfig6"):
        path = command_path(tool)
        console.status("ok" if path else "warn", f"{tool}: {path or 'missing'}")
    console.line()
    console.section("THEME ASSETS")
    for label, path in (
        ("Official color scheme", first_existing_path(official_color_paths)),
        ("Legacy color alias", first_existing_path(legacy_color_paths)),
        ("Official launcher", first_existing_path(official_launcher_paths)),
        ("Upstream launcher override", first_existing_path(upstream_override_paths)),
        ("Experimental launcher", first_existing_path(experimental_launcher_paths)),
        ("Experimental GUI", resolve_experimental_gui(root)),
    ):
        console.status("ok" if path.exists() else "warn", f"{label}: {path}")
    console.line()
    console.section("ACTIVE USER SETTINGS")
    console.line(f"ColorScheme       {read_ini_value(kdeglobals, 'General', 'ColorScheme') or 'unset'}")
    console.line(f"widgetStyle       {read_ini_value(kdeglobals, 'KDE', 'widgetStyle') or 'unset'}")
    console.line(f"LookAndFeel       {read_ini_value(kdeglobals, 'KDE', 'LookAndFeelPackage') or 'unset'}")
    console.line(f"Icon theme        {read_ini_value(kdeglobals, 'Icons', 'Theme') or 'unset'}")
    console.line(f"Cursor theme      {read_ini_value(kcminputrc, 'Mouse', 'cursorTheme') or 'unset'}")
    console.line(f"Cursor size       {read_ini_value(kcminputrc, 'Mouse', 'cursorSize') or 'unset'}")
    console.line()
    console.section("KCM WORKFLOW")
    console.line("List modules with `kcmshell6 --list`.")
    console.line("Open a standalone module with `kcmshell6 <module-name>`.")
    console.line("Open the full settings app with `systemsettings` or the `Kesk Settings` launcher.")
    return 0


def launch_systemsettings(console: KeskConsole, args: Sequence[str]) -> int:
    systemsettings = command_path("systemsettings")
    kcmshell6 = command_path("kcmshell6")

    if not has_graphical_session():
        return show_requires_graphics(console, "KDE System Settings")

    if args and args[0] == "--module":
        if len(args) < 2:
            return show_help(console, "Missing KCM module name after --module.")
        args = [args[1], *args[2:]]

    if systemsettings:
        return launch_program([systemsettings, *args])

    if args and kcmshell6:
        return launch_program([kcmshell6, *args])

    return show_help(console, "systemsettings is missing from the current system.")


def launch_experimental(console: KeskConsole, root: Path, args: Sequence[str]) -> int:
    if not has_graphical_session():
        return show_requires_graphics(console, "Experimental Kesk Settings")

    gui_path = resolve_experimental_gui(root)
    if not gui_path.exists():
        return show_help(console, f"Experimental GUI not found: {gui_path}")

    return launch_program([str(gui_path), *args])


def main(args: Sequence[str], root: Path) -> int:
    console = KeskConsole()
    if args and args[0] in {"--help", "-h", "help"}:
        return show_help(console)
    if args and args[0] == "--dry-run":
        return print_dry_run(console, root)
    if args and args[0] == "--experimental":
        return launch_experimental(console, root, args[1:])
    return launch_systemsettings(console, args)
