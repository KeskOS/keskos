from __future__ import annotations

import configparser
from dataclasses import dataclass
from pathlib import Path
import os
import shutil
import subprocess
import sys
from typing import Sequence

from common import SessionLogger, shell_join
from settings_core import ControlPaths, about_rows


DOC_LINKS: tuple[tuple[str, str], ...] = (
    ("Docs", "https://docs.keskos.org"),
    ("Website", "https://keskos.org"),
    ("Downloads", "https://downloads.keskos.org"),
    ("GitHub", "https://github.com/memegeko/keskos"),
)


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
    config_path: Path
    docs_local_path: Path | None


@dataclass
class GuiPrefs:
    width: int = 1100
    height: int = 720
    last_page: str = "dashboard"
    dashboard_checks: bool = True


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
    backups_dir = home / ".local" / "state" / "kesk" / "backups"
    config_path = home / ".config" / "kesk" / "settings.conf"

    logs_dir.mkdir(parents=True, exist_ok=True)
    backups_dir.mkdir(parents=True, exist_ok=True)
    config_path.parent.mkdir(parents=True, exist_ok=True)

    return RuntimePaths(
        root=root,
        usr_root=usr_root,
        staged_root=staged_root,
        home=home,
        router_path=router_path,
        gui_path=gui_path,
        logs_dir=logs_dir,
        backups_dir=backups_dir,
        config_path=config_path,
        docs_local_path=docs_local_path,
    )


def tool_command(paths: RuntimePaths, tool_name: str, *extra_args: str) -> list[str]:
    if paths.router_path.is_file():
        return python_command(paths.router_path, tool_name, *extra_args)
    return ["kesk", tool_name, *extra_args]


def control_paths(paths: RuntimePaths) -> ControlPaths:
    return ControlPaths(logs_dir=paths.logs_dir, backups_dir=paths.backups_dir)


def about_info(paths: RuntimePaths) -> list[tuple[str, str]]:
    return about_rows(paths.root, control_paths(paths))


def load_prefs(path: Path) -> GuiPrefs:
    parser = configparser.ConfigParser()
    if path.is_file():
        parser.read(path, encoding="utf-8")

    prefs = GuiPrefs()
    prefs.width = parser.getint("window", "width", fallback=prefs.width)
    prefs.height = parser.getint("window", "height", fallback=prefs.height)
    prefs.last_page = parser.get("window", "last_page", fallback=prefs.last_page)
    prefs.dashboard_checks = parser.getboolean("general", "dashboard_checks", fallback=prefs.dashboard_checks)
    return prefs


def save_prefs(path: Path, prefs: GuiPrefs) -> None:
    parser = configparser.ConfigParser()
    parser["window"] = {
        "width": str(prefs.width),
        "height": str(prefs.height),
        "last_page": prefs.last_page,
    }
    parser["general"] = {
        "dashboard_checks": "true" if prefs.dashboard_checks else "false",
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


def latest_log(paths: RuntimePaths, prefix: str) -> Path | None:
    newest: Path | None = None
    newest_mtime = -1.0
    if not paths.logs_dir.exists():
        return None

    for candidate in paths.logs_dir.glob(f"{prefix}-*.log"):
        try:
            mtime = candidate.stat().st_mtime
        except OSError:
            continue
        if mtime > newest_mtime:
            newest = candidate
            newest_mtime = mtime
    return newest


def list_log_files(paths: RuntimePaths, prefix: str | None = None) -> list[Path]:
    if not paths.logs_dir.exists():
        return []
    pattern = f"{prefix}-*.log" if prefix else "*.log"
    return sorted(paths.logs_dir.glob(pattern), key=lambda path: path.stat().st_mtime if path.exists() else 0, reverse=True)


def list_backup_dirs(paths: RuntimePaths) -> list[Path]:
    if not paths.backups_dir.exists():
        return []
    return sorted([path for path in paths.backups_dir.iterdir() if path.is_dir()], key=lambda path: path.stat().st_mtime, reverse=True)


def read_text_preview(path: Path, limit: int = 200_000) -> str:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return f"Could not read {path}: {exc}"
    if len(text) <= limit:
        return text
    return text[-limit:]
