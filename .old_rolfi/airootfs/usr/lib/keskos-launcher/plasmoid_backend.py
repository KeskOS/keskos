#!/usr/bin/env python3
from __future__ import annotations

import configparser
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


DESKTOP_DIRS = [
    Path("/usr/share/applications"),
    Path.home() / ".local/share/applications",
]

CATEGORY_ORDER = [
    ("favorites", "Favorites"),
    ("all", "All Applications"),
    ("development", "Development"),
    ("internet", "Internet"),
    ("multimedia", "Multimedia"),
    ("system", "System"),
    ("utilities", "Utilities"),
    ("lost", "Lost & Found"),
    ("power", "Power / Session"),
]

CATEGORY_RULES = {
    "development": {
        "Building",
        "Debugger",
        "Development",
        "IDE",
        "RevisionControl",
    },
    "internet": {
        "Chat",
        "Email",
        "Feed",
        "InstantMessaging",
        "IRCClient",
        "Network",
        "RemoteAccess",
        "Telephony",
        "WebBrowser",
    },
    "multimedia": {
        "Audio",
        "AudioVideo",
        "DiscBurning",
        "Graphics",
        "Midi",
        "Music",
        "Photography",
        "Player",
        "Recorder",
        "Video",
    },
    "system": {
        "DesktopSettings",
        "HardwareSettings",
        "Monitor",
        "PackageManager",
        "Security",
        "Settings",
        "System",
    },
    "utilities": {
        "Archiving",
        "Calculator",
        "Clock",
        "Compression",
        "ConsoleOnly",
        "FileManager",
        "FileTools",
        "Office",
        "PDA",
        "Qt",
        "TerminalEmulator",
        "TextEditor",
        "Utility",
    },
}

FAVORITE_CANDIDATES = [
    "org.kde.konsole.desktop",
    "konsole.desktop",
    "org.kde.dolphin.desktop",
    "dolphin.desktop",
    "systemsettings.desktop",
    "kdesystemsettings.desktop",
    "librewolf.desktop",
    "zen-browser.desktop",
    "zen.desktop",
    "brave-browser.desktop",
    "brave.desktop",
    "firefox.desktop",
]

FIELD_CODE_RE = re.compile(r"%(?:[fFuUdDnNickKmMv])")


@dataclass
class AppEntry:
    desktop_id: str
    path: str
    name: str
    generic_name: str
    comment: str
    icon: str
    exec_line: str
    categories: list[str]
    menu_categories: list[str]
    favorite: bool
    favorite_rank: int

    def as_dict(self) -> dict:
        return {
            "desktopId": self.desktop_id,
            "path": self.path,
            "name": self.name,
            "genericName": self.generic_name,
            "comment": self.comment,
            "icon": self.icon,
            "exec": self.exec_line,
            "categories": self.categories,
            "menuCategories": self.menu_categories,
            "favorite": self.favorite,
            "favoriteRank": self.favorite_rank,
        }


def split_semicolon(value: str) -> list[str]:
    return [item.strip() for item in value.split(";") if item.strip()]


def bool_value(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


def visible_in_plasma(entry: configparser.SectionProxy) -> bool:
    only_show_in = set(split_semicolon(entry.get("OnlyShowIn", "")))
    not_show_in = set(split_semicolon(entry.get("NotShowIn", "")))

    plasma_tokens = {"KDE", "PLASMA", "X-KDE"}

    if only_show_in and not any(token in plasma_tokens or token.startswith("X-KDE") for token in only_show_in):
        return False

    if any(token in plasma_tokens or token.startswith("X-KDE") for token in not_show_in):
        return False

    return True


def desktop_id_for(path: Path, roots: list[Path]) -> str:
    for root in roots:
        try:
            relpath = path.relative_to(root)
        except ValueError:
            continue
        return str(relpath).replace("/", "-")
    return path.name


def classify_categories(categories: list[str]) -> list[str]:
    matches: list[str] = []
    category_set = set(categories)

    for key, _label in CATEGORY_ORDER:
        if key in {"favorites", "all", "power", "lost"}:
            continue
        if category_set.intersection(CATEGORY_RULES.get(key, set())):
            matches.append(key)

    if not matches:
        matches.append("lost")

    return matches


def sanitize_exec(exec_line: str) -> str:
    cleaned = exec_line.replace("%%", "%")
    cleaned = FIELD_CODE_RE.sub("", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def load_applications() -> list[AppEntry]:
    roots = [directory for directory in DESKTOP_DIRS if directory.is_dir()]
    entries: list[AppEntry] = []
    seen: set[str] = set()
    favorite_rank = {desktop_id: index for index, desktop_id in enumerate(FAVORITE_CANDIDATES)}

    for root in roots:
        for desktop_file in sorted(root.rglob("*.desktop")):
            parser = configparser.ConfigParser(interpolation=None, strict=False)
            try:
                parser.read(desktop_file, encoding="utf-8")
            except (OSError, configparser.Error, UnicodeDecodeError):
                continue

            if not parser.has_section("Desktop Entry"):
                continue

            entry = parser["Desktop Entry"]
            if entry.get("Type", "").strip() != "Application":
                continue
            if bool_value(entry.get("Hidden", "")) or bool_value(entry.get("NoDisplay", "")):
                continue
            if not visible_in_plasma(entry):
                continue

            name = entry.get("Name", "").strip()
            if not name:
                continue

            desktop_id = desktop_id_for(desktop_file, roots)
            if desktop_id in seen:
                continue
            seen.add(desktop_id)

            categories = split_semicolon(entry.get("Categories", ""))
            menu_categories = classify_categories(categories)
            entry_favorite_rank = favorite_rank.get(desktop_id, len(FAVORITE_CANDIDATES) + 50)

            entries.append(
                AppEntry(
                    desktop_id=desktop_id,
                    path=str(desktop_file),
                    name=name,
                    generic_name=entry.get("GenericName", "").strip(),
                    comment=entry.get("Comment", "").strip(),
                    icon=entry.get("Icon", "").strip(),
                    exec_line=entry.get("Exec", "").strip(),
                    categories=categories,
                    menu_categories=menu_categories,
                    favorite=desktop_id in favorite_rank,
                    favorite_rank=entry_favorite_rank,
                )
            )

    entries.sort(key=lambda item: (item.favorite_rank, item.name.lower(), item.desktop_id.lower()))
    return entries


def pick_favorites(apps: list[AppEntry]) -> list[str]:
    known = {app.desktop_id for app in apps}
    ordered: list[str] = []
    for candidate in FAVORITE_CANDIDATES:
        if candidate in known and candidate not in ordered:
            ordered.append(candidate)
    return ordered


def category_payload() -> list[dict]:
    return [{"key": key, "label": label} for key, label in CATEGORY_ORDER]


def power_payload() -> list[dict]:
    return [
        {"id": "lock", "name": "Lock Session", "icon": "system-lock-screen", "comment": "Lock the current session"},
        {"id": "logout", "name": "Log Out", "icon": "system-log-out", "comment": "Log out of the current session"},
        {"id": "suspend", "name": "Sleep", "icon": "system-suspend", "comment": "Suspend the current system"},
        {"id": "restart", "name": "Restart", "icon": "system-reboot", "comment": "Reboot the current system"},
        {"id": "shutdown", "name": "Shut Down", "icon": "system-shutdown", "comment": "Power off the current system"},
    ]


def dump_payload() -> dict:
    apps = load_applications()
    return {
        "statusLine": "APPLICATION INDEX ONLINE",
        "categories": category_payload(),
        "favorites": pick_favorites(apps),
        "apps": [app.as_dict() for app in apps],
        "power": power_payload(),
    }


def run_command(argv: list[str]) -> bool:
    try:
        completed = subprocess.run(argv, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError:
        return False
    return completed.returncode == 0


def spawn_command(argv: list[str]) -> bool:
    try:
        subprocess.Popen(argv, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    except OSError:
        return False
    return True


def launch_entry(desktop_id: str) -> int:
    entry = next((app for app in load_applications() if app.desktop_id == desktop_id), None)
    if entry is None:
        print(f"Unknown desktop id: {desktop_id}", file=sys.stderr)
        return 1

    if shutil.which("gio") and run_command(["gio", "launch", entry.path]):
        return 0

    gtk_launch_id = desktop_id[:-8] if desktop_id.endswith(".desktop") else desktop_id
    if shutil.which("gtk-launch") and run_command(["gtk-launch", gtk_launch_id]):
        return 0

    exec_line = sanitize_exec(entry.exec_line)
    if exec_line:
        try:
            argv = shlex.split(exec_line)
        except ValueError:
            argv = []
        if argv and spawn_command(argv):
            return 0

    print(f"Could not launch desktop id: {desktop_id}", file=sys.stderr)
    return 1


def lock_commands() -> list[list[str]]:
    commands: list[list[str]] = []
    if shutil.which("loginctl"):
        commands.append(["loginctl", "lock-session"])
    if shutil.which("qdbus6"):
        commands.append(["qdbus6", "org.freedesktop.ScreenSaver", "/ScreenSaver", "Lock"])
    if shutil.which("qdbus"):
        commands.append(["qdbus", "org.freedesktop.ScreenSaver", "/ScreenSaver", "Lock"])
    return commands


def logout_commands() -> list[list[str]]:
    commands: list[list[str]] = []
    if shutil.which("qdbus6"):
        commands.extend(
            [
                ["qdbus6", "org.kde.Shutdown", "/Shutdown", "org.kde.Shutdown.logout"],
                ["qdbus6", "org.kde.ksmserver", "/KSMServer", "logout", "0", "0", "0"],
            ]
        )
    if shutil.which("qdbus"):
        commands.extend(
            [
                ["qdbus", "org.kde.Shutdown", "/Shutdown", "org.kde.Shutdown.logout"],
                ["qdbus", "org.kde.ksmserver", "/KSMServer", "logout", "0", "0", "0"],
            ]
        )
    return commands


def restart_commands() -> list[list[str]]:
    commands: list[list[str]] = []
    if shutil.which("qdbus6"):
        commands.extend(
            [
                ["qdbus6", "org.kde.Shutdown", "/Shutdown", "org.kde.Shutdown.logoutAndReboot"],
                ["qdbus6", "org.freedesktop.login1", "/org/freedesktop/login1", "org.freedesktop.login1.Manager.Reboot", "true"],
            ]
        )
    if shutil.which("qdbus"):
        commands.append(["qdbus", "org.kde.Shutdown", "/Shutdown", "org.kde.Shutdown.logoutAndReboot"])
    if shutil.which("loginctl"):
        commands.append(["loginctl", "reboot"])
    if shutil.which("systemctl"):
        commands.append(["systemctl", "reboot"])
    return commands


def shutdown_commands() -> list[list[str]]:
    commands: list[list[str]] = []
    if shutil.which("qdbus6"):
        commands.extend(
            [
                ["qdbus6", "org.kde.Shutdown", "/Shutdown", "org.kde.Shutdown.logoutAndShutdown"],
                ["qdbus6", "org.freedesktop.login1", "/org/freedesktop/login1", "org.freedesktop.login1.Manager.PowerOff", "true"],
            ]
        )
    if shutil.which("qdbus"):
        commands.append(["qdbus", "org.kde.Shutdown", "/Shutdown", "org.kde.Shutdown.logoutAndShutdown"])
    if shutil.which("loginctl"):
        commands.append(["loginctl", "poweroff"])
    if shutil.which("systemctl"):
        commands.append(["systemctl", "poweroff"])
    return commands


def suspend_commands() -> list[list[str]]:
    commands: list[list[str]] = []
    if shutil.which("loginctl"):
        commands.append(["loginctl", "suspend"])
    if shutil.which("systemctl"):
        commands.append(["systemctl", "suspend"])
    return commands


def perform_power_action(action: str) -> int:
    command_map = {
        "lock": lock_commands,
        "logout": logout_commands,
        "restart": restart_commands,
        "shutdown": shutdown_commands,
        "suspend": suspend_commands,
    }

    resolver = command_map.get(action)
    if resolver is None:
        print(f"Unknown power action: {action}", file=sys.stderr)
        return 1

    for argv in resolver():
        if run_command(argv):
            return 0

    print(f"Power action failed: {action}", file=sys.stderr)
    return 1


def usage() -> int:
    print("Usage: plasmoid_backend.py dump|launch <desktop-id>|power <action>", file=sys.stderr)
    return 1


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        return usage()

    command = argv[1]
    if command == "dump":
        print(json.dumps(dump_payload(), ensure_ascii=False))
        return 0
    if command == "launch" and len(argv) >= 3:
        return launch_entry(argv[2])
    if command == "power" and len(argv) >= 3:
        return perform_power_action(argv[2])

    return usage()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
