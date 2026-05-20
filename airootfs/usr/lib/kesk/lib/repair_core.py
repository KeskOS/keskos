from __future__ import annotations

import configparser
from dataclasses import dataclass, field
from datetime import datetime
import filecmp
import json
import os
from pathlib import Path
import pwd
import shutil
import subprocess
import tempfile
from typing import Iterable, Sequence

from common import KeskConsole, SessionLogger, shell_join, stream_command


STARTPAGE_URL = "file:///usr/share/keskos/startpage/index.html"
SDDM_THEME_NAME = "keskos"
BACKUP_TIME_FORMAT = "%Y%m%d-%H%M%S"
THEME_KEYWORDS = ("keskos", "kesk-os", "kesk", "amber", "terminal", "split")
PLASMA_THEME_NAMES = ("keskos-shell", "keskos", "kesk-os", "kesk")
LOOK_AND_FEEL_NAMES = ("com.keskos.desktop", "keskos", "kesk-os", "kesk")
COLOR_SCHEME_NAMES = ("KeskOSDark", "KESKOS", "keskosdark", "keskos", "kesk-os", "kesk")
ICON_THEME_NAMES = ("keskos", "kesk-os", "kesk", "breeze-dark", "Papirus-Dark", "Papirus", "breeze", "Breeze", "hicolor")
CURSOR_THEME_NAMES = ("keskos", "kesk-os", "kesk", "breeze_cursors", "breeze", "Bibata-Modern-Ice", "Bibata-Original-Ice", "Breeze_Snow", "Breeze", "default")
GTK_THEME_NAMES = ("keskos", "kesk-os", "kesk", "amber", "split")
KONSOLE_PROFILE_NAMES = ("KeskOS", "keskos", "terminal")
KVANTUM_THEME_NAMES = ("keskos", "kesk-os", "kesk", "amber", "split")
WINDOW_DECORATION_NAMES = ("kwin4_decoration_qml_keskos_split", "KeskOS-SPLIT", "keskos-split", "split")
FONT_NAME = "JetBrainsMono Nerd Font"
FONT_SETTING = f"{FONT_NAME},10,-1,5,50,0,0,0,0,0"
SMALL_FONT_SETTING = f"{FONT_NAME},8,-1,5,50,0,0,0,0,0"
GTK_FONT_SETTING = f"{FONT_NAME} 10"


@dataclass
class ExecutedCommand:
    command: str
    exit_code: int


@dataclass
class ActionRecord:
    key: str
    label: str
    started_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: str = ""
    exit_code: int = 0
    status: str = "pending"
    notes: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    backups: list[str] = field(default_factory=list)
    changed_files: list[str] = field(default_factory=list)
    commands: list[ExecutedCommand] = field(default_factory=list)


@dataclass
class ThemeAsset:
    name: str
    path: Path


@dataclass
class ThemeStatus:
    detected: dict[str, list[ThemeAsset]] = field(default_factory=dict)
    active: dict[str, str] = field(default_factory=dict)
    missing_assets: list[str] = field(default_factory=list)


@dataclass
class RepairContext:
    console: KeskConsole
    logger: SessionLogger
    root: Path
    usr_root: Path
    fs_root: Path
    user: str
    home: Path
    session_stamp: str
    user_backup_root: Path
    system_backup_root: Path
    report_path: Path
    source_root: Path | None = None
    kwriteconfig_bin: str | None = None
    kbuildsycoca_bin: str | None = None
    qdbus_bin: str | None = None
    lookandfeeltool_bin: str | None = None
    plasma_apply_colorscheme_bin: str | None = None
    configure_user_bin: Path | None = None
    reset_panel_bin: Path | None = None
    launcher_switch_bin: Path | None = None
    fix_launcher_bin: Path | None = None
    quickshell_wrapper_bin: Path | None = None
    action_records: list[ActionRecord] = field(default_factory=list)
    backup_registry: set[str] = field(default_factory=set)
    changed_registry: set[str] = field(default_factory=set)
    created_registry: set[str] = field(default_factory=set)
    theme_status_cache: ThemeStatus | None = None
    theme_status_logged: bool = False


def command_exists(name: str) -> bool:
    return shutil.which(name) is not None


def graphical_session_available() -> bool:
    return bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))


def resolve_user() -> str:
    if os.geteuid() == 0 and os.environ.get("SUDO_USER") and os.environ["SUDO_USER"] != "root":
        return os.environ["SUDO_USER"]
    return pwd.getpwuid(os.getuid()).pw_name


def resolve_home(user: str) -> Path:
    if os.geteuid() != 0 and os.environ.get("HOME"):
        return Path(os.environ["HOME"]).expanduser()
    return Path(pwd.getpwnam(user).pw_dir)


def resolve_source_root(root: Path, home: Path) -> Path | None:
    candidates: list[Path] = []

    if os.environ.get("KESKOS_SOURCE_ROOT"):
        candidates.append(Path(os.environ["KESKOS_SOURCE_ROOT"]).expanduser())

    cwd = Path.cwd()
    candidates.append(cwd)

    for ancestor in (root, *root.parents):
        candidates.append(ancestor)

    candidates.extend(
        [
            home / ".local" / "share" / "keskos" / "source",
            Path("/usr/local/share/keskos/source"),
            Path("/usr/share/keskos/source"),
        ]
    )

    seen: set[Path] = set()
    for candidate in candidates:
        candidate = candidate.resolve()
        if candidate in seen:
            continue
        seen.add(candidate)
        if (candidate / "configs").is_dir():
            return candidate
    return None


def resolve_helper(root: Path, name: str, *, prefer_local_bin: bool = False) -> Path | None:
    candidates: list[Path] = []
    usr_root = root.parents[1]

    if prefer_local_bin:
        candidates.extend(
            [
                usr_root / "local" / "bin" / name,
                Path.home() / ".local" / "bin" / name,
                Path("/usr/local/bin") / name,
                usr_root / "bin" / name,
                Path("/usr/bin") / name,
            ]
        )
    else:
        candidates.extend(
            [
                usr_root / "bin" / name,
                Path.home() / ".local" / "bin" / name,
                Path("/usr/bin") / name,
                Path("/usr/local/bin") / name,
            ]
        )

    for candidate in candidates:
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return candidate
    return None


def choose_binary(*names: str) -> str | None:
    for name in names:
        if command_exists(name):
            return name
    return None


def first_existing_path(candidates: Iterable[Path]) -> Path | None:
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def directories_match(source_dir: Path, target_dir: Path) -> bool:
    if not source_dir.is_dir() or not target_dir.is_dir():
        return False

    comparison = filecmp.dircmp(source_dir, target_dir)
    if comparison.left_only or comparison.right_only or comparison.funny_files:
        return False

    for filename in comparison.common_files:
        if not filecmp.cmp(source_dir / filename, target_dir / filename, shallow=False):
            return False

    return all(directories_match(source_dir / dirname, target_dir / dirname) for dirname in comparison.common_dirs)


def file_matches(source_path: Path, target_path: Path) -> bool:
    return source_path.is_file() and target_path.is_file() and filecmp.cmp(source_path, target_path, shallow=False)


def relative_backup_path(home: Path, source_path: Path) -> Path:
    if source_path.is_absolute():
        try:
            return source_path.relative_to(home)
        except ValueError:
            return source_path.relative_to("/")
    return source_path


def add_backup_record(record: ActionRecord, source_path: Path, backup_path: Path) -> None:
    record.backups.append(f"{source_path} -> {backup_path}")


def add_changed_record(ctx: RepairContext, record: ActionRecord, path: Path) -> None:
    changed = str(path)
    if changed in ctx.changed_registry:
        return
    ctx.changed_registry.add(changed)
    record.changed_files.append(changed)


def ensure_user_backup(ctx: RepairContext, record: ActionRecord, source_path: Path) -> None:
    if not source_path.exists():
        return
    if str(source_path) in ctx.created_registry:
        return
    source_key = f"user:{source_path}"
    if source_key in ctx.backup_registry:
        return

    backup_path = ctx.user_backup_root / relative_backup_path(ctx.home, source_path)
    backup_path.parent.mkdir(parents=True, exist_ok=True)
    if source_path.is_dir():
        shutil.copytree(source_path, backup_path, dirs_exist_ok=True)
    else:
        shutil.copy2(source_path, backup_path)

    ctx.backup_registry.add(source_key)
    add_backup_record(record, source_path, backup_path)


def capture_command(
    ctx: RepairContext,
    record: ActionRecord,
    command: Sequence[str],
    *,
    timeout: int = 60,
    allow_failure: bool = False,
) -> subprocess.CompletedProcess[str]:
    ctx.logger.log(f"command={shell_join(command)}")
    try:
        result = subprocess.run(
            list(command),
            check=False,
            capture_output=True,
            text=True,
            errors="replace",
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        result = subprocess.CompletedProcess(list(command), 124, "", f"timed out after {timeout}s")
    except OSError as exc:
        result = subprocess.CompletedProcess(list(command), 127, "", str(exc))

    record.commands.append(ExecutedCommand(shell_join(command), result.returncode))
    ctx.logger.log(f"exit_code={result.returncode}")
    if result.stdout.strip():
        ctx.logger.log("stdout_begin")
        for line in result.stdout.splitlines():
            ctx.logger.log(f"stdout {line}")
        ctx.logger.log("stdout_end")
    if result.stderr.strip():
        ctx.logger.log("stderr_begin")
        for line in result.stderr.splitlines():
            ctx.logger.log(f"stderr {line}")
        ctx.logger.log("stderr_end")

    if result.returncode != 0 and not allow_failure:
        first_error = result.stderr.strip().splitlines()[0] if result.stderr.strip() else f"command failed: {shell_join(command)}"
        record.warnings.append(first_error)

    return result


def stream_logged_command(
    ctx: RepairContext,
    record: ActionRecord,
    command: Sequence[str],
    *,
    allow_failure: bool = False,
) -> int:
    ctx.console.muted(shell_join(command))
    exit_code = stream_command(command, ctx.logger, ctx.console)
    record.commands.append(ExecutedCommand(shell_join(command), exit_code))
    if exit_code != 0 and not allow_failure:
        record.warnings.append(f"command failed with exit code {exit_code}: {shell_join(command)}")
    return exit_code


def ensure_system_access(ctx: RepairContext, record: ActionRecord) -> int:
    if os.geteuid() == 0:
        return 0
    if not command_exists("sudo"):
        record.warnings.append("sudo is required for this action")
        return 3

    ctx.console.status("work", "requesting system privileges")
    exit_code = stream_logged_command(ctx, record, ["sudo", "-v"])
    return 0 if exit_code == 0 else 3


def ensure_system_backup_root(ctx: RepairContext, record: ActionRecord) -> int:
    exit_code = ensure_system_access(ctx, record)
    if exit_code != 0:
        return exit_code

    command = ["install", "-d", "-m", "755", str(ctx.system_backup_root)]
    if os.geteuid() != 0:
        command.insert(0, "sudo")

    result = capture_command(ctx, record, command, allow_failure=False)
    return 0 if result.returncode == 0 else 3


def backup_system_path(ctx: RepairContext, record: ActionRecord, source_path: Path) -> int:
    if not source_path.exists():
        return 0

    source_key = f"system:{source_path}"
    if source_key in ctx.backup_registry:
        return 0

    exit_code = ensure_system_backup_root(ctx, record)
    if exit_code != 0:
        return exit_code

    backup_path = ctx.system_backup_root / source_path.relative_to("/")
    parent_command = ["install", "-d", "-m", "755", str(backup_path.parent)]
    copy_command = ["cp", "-a", str(source_path), str(backup_path)]
    if os.geteuid() != 0:
        parent_command.insert(0, "sudo")
        copy_command.insert(0, "sudo")

    parent_result = capture_command(ctx, record, parent_command)
    if parent_result.returncode != 0:
        return 3

    copy_result = capture_command(ctx, record, copy_command)
    if copy_result.returncode != 0:
        return 3

    ctx.backup_registry.add(source_key)
    add_backup_record(record, source_path, backup_path)
    return 0


def write_text_file(path: Path, content: str, mode: int = 0o644) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    path.chmod(mode)


def copy_user_file(ctx: RepairContext, record: ActionRecord, source_path: Path, target_path: Path, *, mode: int = 0o644) -> bool:
    if not source_path.is_file():
        record.warnings.append(f"missing source file: {source_path}")
        return False

    if file_matches(source_path, target_path):
        record.notes.append(f"already current: {target_path}")
        return True

    target_existed = target_path.exists()
    if target_existed:
        ensure_user_backup(ctx, record, target_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_path, target_path)
    target_path.chmod(mode)
    if not target_existed:
        ctx.created_registry.add(str(target_path))
    add_changed_record(ctx, record, target_path)
    return True


def sync_user_directory(ctx: RepairContext, record: ActionRecord, source_dir: Path, target_dir: Path) -> bool:
    if not source_dir.is_dir():
        record.warnings.append(f"missing source directory: {source_dir}")
        return False

    if directories_match(source_dir, target_dir):
        record.notes.append(f"already current: {target_dir}")
        return True

    target_existed = target_dir.exists()
    if target_existed:
        ensure_user_backup(ctx, record, target_dir)
    if target_dir.exists():
        shutil.rmtree(target_dir)
    target_dir.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source_dir, target_dir)
    if not target_existed:
        ctx.created_registry.add(str(target_dir))
    add_changed_record(ctx, record, target_dir)
    return True


def write_user_text(ctx: RepairContext, record: ActionRecord, target_path: Path, content: str, *, mode: int = 0o644) -> bool:
    current = None
    target_existed = target_path.exists()
    if target_path.exists():
        current = target_path.read_text(encoding="utf-8", errors="replace")
    if current == content:
        record.notes.append(f"already current: {target_path}")
        return True

    if target_existed:
        ensure_user_backup(ctx, record, target_path)
    write_text_file(target_path, content, mode=mode)
    if not target_existed:
        ctx.created_registry.add(str(target_path))
    add_changed_record(ctx, record, target_path)
    return True


def read_ini_value(target_path: Path, section: str, key: str) -> str | None:
    if not target_path.is_file():
        return None

    parser = configparser.RawConfigParser()
    parser.optionxform = str
    try:
        parser.read(target_path, encoding="utf-8")
    except (configparser.Error, OSError):
        return None
    return parser.get(section, key, fallback=None)


def update_ini_settings(
    ctx: RepairContext,
    record: ActionRecord,
    target_path: Path,
    section: str,
    updates: dict[str, str],
) -> bool:
    parser = configparser.RawConfigParser()
    parser.optionxform = str
    target_existed = target_path.exists()
    if target_path.exists():
        parser.read(target_path, encoding="utf-8")
    if not parser.has_section(section):
        parser.add_section(section)

    changed = False
    for key, value in updates.items():
        if parser.get(section, key, fallback=None) != value:
            parser.set(section, key, value)
            changed = True

    if not changed and target_path.exists():
        record.notes.append(f"already current: {target_path}")
        return True

    if target_existed:
        ensure_user_backup(ctx, record, target_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    with target_path.open("w", encoding="utf-8") as handle:
        parser.write(handle)
    if not target_existed:
        ctx.created_registry.add(str(target_path))
    add_changed_record(ctx, record, target_path)
    return True


def kwriteconfig(
    ctx: RepairContext,
    record: ActionRecord,
    target_path: Path,
    groups: Sequence[str],
    key: str,
    value: str,
) -> bool:
    target_existed = target_path.exists()
    section_name = "][".join(groups)
    if read_ini_value(target_path, section_name, key) == value:
        record.notes.append(f"already current: {target_path}")
        return True

    if ctx.kwriteconfig_bin:
        if target_existed:
            ensure_user_backup(ctx, record, target_path)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        command = [ctx.kwriteconfig_bin, "--file", str(target_path)]
        for group in groups:
            command.extend(["--group", group])
        command.extend(["--key", key, value])

        result = capture_command(ctx, record, command)
        if result.returncode == 0:
            if not target_existed:
                ctx.created_registry.add(str(target_path))
            add_changed_record(ctx, record, target_path)
            return True
        return False

    parser = configparser.RawConfigParser()
    parser.optionxform = str
    if target_existed:
        try:
            parser.read(target_path, encoding="utf-8")
        except (configparser.Error, OSError):
            parser = configparser.RawConfigParser()
            parser.optionxform = str

    if not parser.has_section(section_name):
        parser.add_section(section_name)
    parser.set(section_name, key, value)

    if target_existed:
        ensure_user_backup(ctx, record, target_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    with target_path.open("w", encoding="utf-8") as handle:
        parser.write(handle)
    if not target_existed:
        ctx.created_registry.add(str(target_path))
    add_changed_record(ctx, record, target_path)
    return True


def score_name(name: str, exact_names: Sequence[str]) -> tuple[int, str]:
    lowered = name.lower()
    exact_map = {candidate.lower(): index for index, candidate in enumerate(exact_names)}
    if lowered in exact_map:
        return exact_map[lowered], lowered
    if any(keyword in lowered for keyword in THEME_KEYWORDS):
        return len(exact_map) + 1, lowered
    return len(exact_map) + 10, lowered


def find_matching_assets(
    roots: Iterable[Path],
    *,
    exact_names: Sequence[str],
    mode: str,
    suffixes: Sequence[str] = (),
    require_subpath: str | None = None,
) -> list[ThemeAsset]:
    assets: list[ThemeAsset] = []
    seen: set[tuple[str, str]] = set()
    exact_lower = {name.lower() for name in exact_names}

    for root in roots:
        if not root.is_dir():
            continue
        for entry in sorted(root.iterdir(), key=lambda candidate: candidate.name.lower()):
            if mode == "dir":
                if not entry.is_dir():
                    continue
                if require_subpath and not (entry / require_subpath).exists():
                    continue
                display_name = entry.name
            else:
                if not entry.is_file():
                    continue
                if suffixes and entry.suffix not in suffixes:
                    continue
                if entry.suffix == ".colors":
                    display_name = read_ini_value(entry, "General", "ColorScheme") or read_ini_value(entry, "General", "Name") or entry.stem
                elif entry.suffix == ".profile":
                    display_name = read_ini_value(entry, "General", "Name") or entry.stem
                else:
                    display_name = entry.stem

            lowered = display_name.lower()
            if lowered not in exact_lower and not any(keyword in lowered for keyword in THEME_KEYWORDS):
                continue

            identity = (display_name.lower(), str(entry))
            if identity in seen:
                continue
            seen.add(identity)
            assets.append(ThemeAsset(display_name, entry))

    assets.sort(key=lambda asset: (*score_name(asset.name, exact_names), str(asset.path)))
    return assets


def active_sddm_theme() -> str | None:
    paths = [Path("/etc/sddm.conf")]
    conf_dir = Path("/etc/sddm.conf.d")
    if conf_dir.is_dir():
        paths.extend(sorted(conf_dir.glob("*.conf")))

    active_theme: str | None = None
    for path in paths:
        if not path.is_file():
            continue
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
    return active_theme


def active_plymouth_theme() -> str | None:
    if command_exists("plymouth-set-default-theme"):
        try:
            result = subprocess.run(
                ["plymouth-set-default-theme"],
                check=False,
                capture_output=True,
                text=True,
                errors="replace",
                timeout=10,
            )
        except (OSError, subprocess.TimeoutExpired):
            result = None
        if result and result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip().splitlines()[-1].strip()

    config_path = Path("/etc/plymouth/plymouthd.conf")
    current_section = ""
    if not config_path.is_file():
        return None
    try:
        lines = config_path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return None
    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            current_section = line[1:-1].strip().lower()
            continue
        if current_section == "daemon" and line.lower().startswith("theme="):
            return line.split("=", 1)[1].strip()
    return None


def preferred_asset_name(status: ThemeStatus, key: str) -> str | None:
    assets = status.detected.get(key, [])
    return assets[0].name if assets else None


def preferred_asset_path(status: ThemeStatus, key: str) -> Path | None:
    assets = status.detected.get(key, [])
    return assets[0].path if assets else None


def is_kesk_look_and_feel(name: str | None) -> bool:
    if not name:
        return False
    lowered = name.strip().lower()
    return lowered in {candidate.lower() for candidate in LOOK_AND_FEEL_NAMES} or "kesk" in lowered


def log_theme_status(ctx: RepairContext, status: ThemeStatus) -> None:
    ctx.logger.log("theme_status_begin")
    for key, value in status.active.items():
        ctx.logger.log(f"theme_active[{key}]={value}")
    for key, assets in status.detected.items():
        if not assets:
            ctx.logger.log(f"theme_detected[{key}]=none")
            continue
        for asset in assets:
            ctx.logger.log(f"theme_detected[{key}]={asset.name}::{asset.path}")
    for label in status.missing_assets:
        ctx.logger.log(f"theme_missing={label}")
    ctx.logger.log("theme_status_end")
    ctx.theme_status_logged = True


def collect_theme_status(ctx: RepairContext, *, refresh: bool = False, log: bool = False) -> ThemeStatus:
    if ctx.theme_status_cache is not None and not refresh:
        status = ctx.theme_status_cache
    else:
        user_share = ctx.home / ".local" / "share"
        detected = {
            "look_and_feel": find_matching_assets(
                [ctx.usr_root / "share" / "plasma" / "look-and-feel", user_share / "plasma" / "look-and-feel", *( [ctx.source_root / "configs" / "look-and-feel"] if ctx.source_root else [] )],
                exact_names=LOOK_AND_FEEL_NAMES,
                mode="dir",
            ),
            "plasma_theme": find_matching_assets(
                [ctx.usr_root / "share" / "plasma" / "desktoptheme", user_share / "plasma" / "desktoptheme", *( [ctx.source_root / "configs" / "plasma" / "desktoptheme"] if ctx.source_root else [] )],
                exact_names=PLASMA_THEME_NAMES,
                mode="dir",
            ),
            "color_scheme": find_matching_assets(
                [ctx.usr_root / "share" / "color-schemes", user_share / "color-schemes", *( [ctx.source_root / "configs" / "kde"] if ctx.source_root else [] )],
                exact_names=COLOR_SCHEME_NAMES,
                mode="file",
                suffixes=(".colors",),
            ),
            "window_decoration": find_matching_assets(
                [ctx.usr_root / "share" / "kwin" / "decorations", *( [ctx.source_root / "configs" / "kwin" / "decorations"] if ctx.source_root else [] ), *( [ctx.source_root / "configs" / "aurorae" / "themes"] if ctx.source_root else [] )],
                exact_names=WINDOW_DECORATION_NAMES,
                mode="dir",
            ),
            "icon_theme": find_matching_assets(
                [ctx.usr_root / "share" / "icons", user_share / "icons", ctx.home / ".icons"],
                exact_names=ICON_THEME_NAMES,
                mode="dir",
            ),
            "cursor_theme": find_matching_assets(
                [ctx.usr_root / "share" / "icons", user_share / "icons", ctx.home / ".icons"],
                exact_names=CURSOR_THEME_NAMES,
                mode="dir",
                require_subpath="cursors",
            ),
            "konsole_profile": find_matching_assets(
                [ctx.usr_root / "share" / "konsole", user_share / "konsole", *( [ctx.source_root / "configs" / "konsole"] if ctx.source_root else [] )],
                exact_names=KONSOLE_PROFILE_NAMES,
                mode="file",
                suffixes=(".profile",),
            ),
            "gtk_theme": find_matching_assets(
                [ctx.usr_root / "share" / "themes", user_share / "themes", ctx.home / ".themes"],
                exact_names=GTK_THEME_NAMES,
                mode="dir",
            ),
            "kvantum_theme": find_matching_assets(
                [ctx.usr_root / "share" / "Kvantum", ctx.home / ".config" / "Kvantum"],
                exact_names=KVANTUM_THEME_NAMES,
                mode="dir",
            ),
            "sddm_theme": find_matching_assets(
                [ctx.usr_root / "share" / "sddm" / "themes", *( [ctx.source_root / "configs" / "sddm"] if ctx.source_root else [] )],
                exact_names=(SDDM_THEME_NAME, "kesk-os", "kesk"),
                mode="dir",
            ),
            "plymouth_theme": find_matching_assets(
                [ctx.usr_root / "share" / "plymouth" / "themes", *( [ctx.source_root / "configs" / "plymouth"] if ctx.source_root else [] )],
                exact_names=("keskos", "kesk-os", "kesk"),
                mode="dir",
            ),
        }

        active = {
            "look_and_feel": read_ini_value(ctx.home / ".config" / "kdeglobals", "KDE", "LookAndFeelPackage") or "unavailable",
            "plasma_theme": read_ini_value(ctx.home / ".config" / "plasmarc", "Theme", "name") or "unavailable",
            "color_scheme": read_ini_value(ctx.home / ".config" / "kdeglobals", "General", "ColorScheme") or "unavailable",
            "window_decoration": read_ini_value(ctx.home / ".config" / "kwinrc", "org.kde.kdecoration2", "theme") or "unavailable",
            "icon_theme": read_ini_value(ctx.home / ".config" / "kdeglobals", "Icons", "Theme") or "unavailable",
            "cursor_theme": (
                read_ini_value(ctx.home / ".config" / "kcminputrc", "Mouse", "cursorTheme")
                or read_ini_value(ctx.home / ".config" / "gtk-3.0" / "settings.ini", "Settings", "gtk-cursor-theme-name")
                or read_ini_value(ctx.home / ".config" / "gtk-4.0" / "settings.ini", "Settings", "gtk-cursor-theme-name")
                or "unavailable"
            ),
            "konsole_profile": read_ini_value(ctx.home / ".config" / "konsolerc", "Desktop Entry", "DefaultProfile") or "unavailable",
            "gtk_theme": (
                read_ini_value(ctx.home / ".config" / "gtk-3.0" / "settings.ini", "Settings", "gtk-theme-name")
                or read_ini_value(ctx.home / ".config" / "gtk-4.0" / "settings.ini", "Settings", "gtk-theme-name")
                or "unavailable"
            ),
            "gtk_icon_theme": (
                read_ini_value(ctx.home / ".config" / "gtk-3.0" / "settings.ini", "Settings", "gtk-icon-theme-name")
                or read_ini_value(ctx.home / ".config" / "gtk-4.0" / "settings.ini", "Settings", "gtk-icon-theme-name")
                or "unavailable"
            ),
            "gtk_cursor_theme": (
                read_ini_value(ctx.home / ".config" / "gtk-3.0" / "settings.ini", "Settings", "gtk-cursor-theme-name")
                or read_ini_value(ctx.home / ".config" / "gtk-4.0" / "settings.ini", "Settings", "gtk-cursor-theme-name")
                or "unavailable"
            ),
            "kvantum_theme": read_ini_value(ctx.home / ".config" / "Kvantum" / "kvantum.kvconfig", "General", "theme") or "unavailable",
            "sddm_theme": active_sddm_theme() or "unavailable",
            "plymouth_theme": active_plymouth_theme() or "unavailable",
        }

        label_map = {
            "look_and_feel": "look-and-feel package",
            "plasma_theme": "Plasma theme",
            "color_scheme": "color scheme",
            "window_decoration": "window decoration",
            "icon_theme": "icon theme",
            "cursor_theme": "cursor theme",
            "konsole_profile": "Konsole profile",
            "gtk_theme": "GTK theme",
            "kvantum_theme": "Kvantum theme",
            "sddm_theme": "SDDM theme",
            "plymouth_theme": "Plymouth theme",
        }
        missing_assets = [label for key, label in label_map.items() if not detected.get(key)]

        status = ThemeStatus(detected=detected, active=active, missing_assets=missing_assets)
        ctx.theme_status_cache = status

    if log and (refresh or not ctx.theme_status_logged):
        log_theme_status(ctx, status)
    return status


def konsole_profile_source_candidates(ctx: RepairContext) -> list[Path]:
    candidates = [ctx.usr_root / "share" / "konsole" / "KeskOS.profile"]
    if ctx.source_root:
        candidates.append(ctx.source_root / "configs" / "konsole" / "KeskOS.profile")
    return candidates


def konsole_colors_source_candidates(ctx: RepairContext) -> list[Path]:
    candidates = [ctx.usr_root / "share" / "konsole" / "KeskOS.colorscheme"]
    if ctx.source_root:
        candidates.append(ctx.source_root / "configs" / "konsole" / "KeskOS.colorscheme")
    return candidates


def quickshell_config_source_candidates(ctx: RepairContext) -> list[Path]:
    candidates = [
        ctx.usr_root / "local" / "share" / "keskos" / "source" / "configs" / "quickshell" / "keskos",
        Path("/usr/local/share/keskos/source/configs/quickshell/keskos"),
    ]
    if ctx.source_root:
        candidates.append(ctx.source_root / "configs" / "quickshell" / "keskos")
    return candidates


def browser_asset_source_candidates(ctx: RepairContext) -> list[Path]:
    candidates = [ctx.usr_root / "share" / "keskos" / "startpage", ctx.usr_root / "share" / "keskos" / "browser-home"]
    if ctx.source_root:
        candidates.extend([ctx.source_root / "browser-home"])
    return candidates


def firefox_theme_source_root(ctx: RepairContext) -> Path | None:
    candidates = [
        ctx.usr_root / "share" / "keskos" / "browser-themes" / "firefox",
        ctx.fs_root / "usr" / "share" / "keskos" / "browser-themes" / "firefox",
    ]
    if ctx.source_root:
        candidates.extend(
            [
                ctx.source_root / "airootfs" / "usr" / "share" / "keskos" / "browser-themes" / "firefox",
                ctx.source_root / "airootfs" / "usr" / "share" / "keskos" / "first-run" / "browser-theme",
            ]
        )
    return first_existing_path(candidates)


def firefox_userchrome_source(ctx: RepairContext) -> Path | None:
    root = firefox_theme_source_root(ctx)
    if root is None:
        return None
    return first_existing_path([root / "userChrome.css", root / "firefox-userChrome.css"])


def firefox_usercontent_source(ctx: RepairContext) -> Path | None:
    root = firefox_theme_source_root(ctx)
    if root is None:
        return None
    return first_existing_path([root / "userContent.css", root / "firefox-userContent.css"])


def brave_policy_source(ctx: RepairContext) -> Path | None:
    candidates = [ctx.usr_root / "share" / "keskos" / "browser-themes" / "brave" / "policies.json"]
    if ctx.source_root:
        candidates.append(ctx.source_root / "airootfs" / "usr" / "share" / "keskos" / "browser-themes" / "brave" / "policies.json")
    return first_existing_path(candidates)


def sddm_theme_source_dir(ctx: RepairContext) -> Path | None:
    status = collect_theme_status(ctx, refresh=True)
    return preferred_asset_path(status, "sddm_theme")


def launcher_source_dir(ctx: RepairContext, name: str) -> Path | None:
    candidates = [ctx.usr_root / "share" / "plasma" / "plasmoids" / name]
    if ctx.source_root:
        candidates.append(ctx.source_root / "configs" / "plasmoids" / name)
    return first_existing_path(candidates)


def find_firefox_profiles(config_root: Path) -> list[Path]:
    profiles: list[Path] = []
    profiles_ini = config_root / "profiles.ini"
    if profiles_ini.exists():
        current_path = ""
        is_relative = True
        for line in profiles_ini.read_text(encoding="utf-8", errors="ignore").splitlines():
            if line.startswith("Path="):
                current_path = line.split("=", 1)[1].strip()
            elif line.startswith("IsRelative="):
                is_relative = line.split("=", 1)[1].strip() != "0"
            elif line.startswith("[") and current_path:
                profile_path = config_root / current_path if is_relative else Path(current_path)
                if profile_path.is_dir():
                    profiles.append(profile_path)
                current_path = ""
        if current_path:
            profile_path = config_root / current_path if is_relative else Path(current_path)
            if profile_path.is_dir():
                profiles.append(profile_path)

    if profiles:
        return profiles
    return [path for path in config_root.glob("*.default*") if path.is_dir()]


def restart_quickshell_if_safe(ctx: RepairContext, record: ActionRecord) -> None:
    if not graphical_session_available():
        record.notes.append("graphical session not detected; quickshell restart skipped")
        return
    if not ctx.quickshell_wrapper_bin:
        record.warnings.append("keskos-shell helper not found; quickshell restart skipped")
        return

    capture_command(ctx, record, ["pkill", "-x", "quickshell"], allow_failure=True)
    result = capture_command(ctx, record, [str(ctx.quickshell_wrapper_bin)], allow_failure=True, timeout=30)
    if result.returncode == 0:
        ctx.console.status("ok", "quickshell restarted")
    else:
        ctx.console.status("warn", "quickshell restart reported an error")


def ensure_required_dirs(ctx: RepairContext, record: ActionRecord) -> int:
    for path in (
        ctx.home / ".config",
        ctx.home / ".config" / "keskos",
        ctx.home / ".config" / "autostart",
        ctx.home / ".config" / "gtk-3.0",
        ctx.home / ".config" / "gtk-4.0",
        ctx.home / ".config" / "Kvantum",
        ctx.home / ".local" / "share" / "konsole",
        ctx.home / ".local" / "state" / "keskos",
        ctx.home / ".local" / "state" / "kesk",
        ctx.home / ".local" / "state" / "kesk" / "logs",
        ctx.home / ".local" / "state" / "kesk" / "backups",
    ):
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
            ctx.created_registry.add(str(path))
            add_changed_record(ctx, record, path)
            ctx.console.status("ok", f"created directory: {path}")
        else:
            ctx.console.status("ok", f"directory present: {path}")
    return 0


def reapply_kde_theme(ctx: RepairContext, record: ActionRecord) -> int:
    status = collect_theme_status(ctx, refresh=True, log=True)
    color_scheme = preferred_asset_name(status, "color_scheme")
    look_and_feel = preferred_asset_name(status, "look_and_feel")
    plasma_theme = preferred_asset_name(status, "plasma_theme")
    decoration_theme = preferred_asset_name(status, "window_decoration")

    updates_ok = True
    updates_ok &= kwriteconfig(ctx, record, ctx.home / ".config" / "kdeglobals", ["General"], "font", FONT_SETTING)
    updates_ok &= kwriteconfig(ctx, record, ctx.home / ".config" / "kdeglobals", ["General"], "fixed", FONT_SETTING)
    updates_ok &= kwriteconfig(ctx, record, ctx.home / ".config" / "kdeglobals", ["General"], "smallestReadableFont", SMALL_FONT_SETTING)
    updates_ok &= kwriteconfig(ctx, record, ctx.home / ".config" / "kdeglobals", ["General"], "menuFont", FONT_SETTING)
    updates_ok &= kwriteconfig(ctx, record, ctx.home / ".config" / "kdeglobals", ["General"], "toolBarFont", FONT_SETTING)
    updates_ok &= kwriteconfig(ctx, record, ctx.home / ".config" / "kdeglobals", ["KDE"], "SingleClick", "false")
    updates_ok &= kwriteconfig(ctx, record, ctx.home / ".config" / "kdeglobals", ["KDE"], "widgetStyle", "Breeze")

    if color_scheme:
        updates_ok &= kwriteconfig(ctx, record, ctx.home / ".config" / "kdeglobals", ["General"], "ColorScheme", color_scheme)
        ctx.console.status("ok", f"Plasma color scheme asset found: {preferred_asset_path(status, 'color_scheme')}")
    else:
        ctx.console.status("skip", "Plasma color scheme asset not found")
        record.notes.append("Plasma color scheme asset not found")

    if look_and_feel:
        updates_ok &= kwriteconfig(ctx, record, ctx.home / ".config" / "kdeglobals", ["KDE"], "LookAndFeelPackage", look_and_feel)
        ctx.console.status("ok", f"look-and-feel package found: {preferred_asset_path(status, 'look_and_feel')}")
    else:
        ctx.console.status("skip", "look-and-feel package not found")
        record.notes.append("look-and-feel package not found")

    if plasma_theme:
        updates_ok &= kwriteconfig(ctx, record, ctx.home / ".config" / "plasmarc", ["Theme"], "name", plasma_theme)
        ctx.console.status("ok", f"Plasma theme asset found: {preferred_asset_path(status, 'plasma_theme')}")
    else:
        ctx.console.status("skip", "Plasma desktop theme not found")
        record.notes.append("Plasma desktop theme not found")

    if decoration_theme:
        updates_ok &= kwriteconfig(ctx, record, ctx.home / ".config" / "kwinrc", ["org.kde.kdecoration2"], "library", "org.kde.kwin.aurorae")
        updates_ok &= kwriteconfig(ctx, record, ctx.home / ".config" / "kwinrc", ["org.kde.kdecoration2"], "theme", decoration_theme)
        updates_ok &= kwriteconfig(ctx, record, ctx.home / ".config" / "kwinrc", ["org.kde.kdecoration2"], "BorderSize", "Normal")
        updates_ok &= kwriteconfig(ctx, record, ctx.home / ".config" / "kwinrc", ["org.kde.kdecoration2"], "BorderSizeAuto", "false")
        updates_ok &= kwriteconfig(ctx, record, ctx.home / ".config" / "kwinrc", ["Windows"], "BorderlessMaximizedWindows", "false")
        ctx.console.status("ok", f"window decoration asset found: {preferred_asset_path(status, 'window_decoration')}")
    else:
        ctx.console.status("skip", "window decoration asset not found")
        record.notes.append("window decoration asset not found")

    lockscreen_background = ctx.usr_root / "share" / "plasma" / "shells" / "org.kde.plasma.desktop" / "contents" / "lockscreen" / "assets" / "background.png"
    if lockscreen_background.exists():
        updates_ok &= kwriteconfig(ctx, record, ctx.home / ".config" / "kscreenlockerrc", ["Greeter"], "WallpaperPlugin", "org.kde.image")
        updates_ok &= kwriteconfig(ctx, record, ctx.home / ".config" / "kscreenlockerrc", ["Greeter", "Wallpaper", "org.kde.image", "General"], "Image", f"file://{lockscreen_background}")
        updates_ok &= kwriteconfig(ctx, record, ctx.home / ".config" / "kscreenlockerrc", ["Greeter", "Wallpaper", "org.kde.image", "General"], "FillMode", "2")
        updates_ok &= kwriteconfig(ctx, record, ctx.home / ".config" / "ksplashrc", ["KSplash"], "Engine", "KSplashQML")
        if look_and_feel:
            updates_ok &= kwriteconfig(ctx, record, ctx.home / ".config" / "ksplashrc", ["KSplash"], "Theme", look_and_feel)

    if graphical_session_available():
        if ctx.lookandfeeltool_bin and look_and_feel and not is_kesk_look_and_feel(look_and_feel):
            capture_command(ctx, record, [ctx.lookandfeeltool_bin, "-a", look_and_feel], allow_failure=True)
        elif look_and_feel and is_kesk_look_and_feel(look_and_feel):
            record.notes.append("Skipped lookandfeeltool for the KeskOS look-and-feel package to preserve the managed panel and wallpaper.")
            ctx.console.status("ok", "Preserved managed panel and wallpaper while reapplying the KeskOS look-and-feel package")
        if ctx.plasma_apply_colorscheme_bin and color_scheme:
            capture_command(ctx, record, [ctx.plasma_apply_colorscheme_bin, color_scheme], allow_failure=True)
        if ctx.qdbus_bin:
            capture_command(ctx, record, [ctx.qdbus_bin, "org.kde.KWin", "/KWin", "reconfigure"], allow_failure=True)

    ctx.theme_status_cache = None
    ctx.console.status("ok" if updates_ok else "warn", "Plasma theme and color settings reapplied" if updates_ok else "Plasma theme repair completed with warnings")
    return 0 if updates_ok else 2


def reapply_icon_theme(ctx: RepairContext, record: ActionRecord) -> int:
    status = collect_theme_status(ctx, refresh=True)
    icon_theme = preferred_asset_name(status, "icon_theme")
    if not icon_theme:
        ctx.console.status("skip", "no suitable icon theme found")
        record.notes.append("no suitable icon theme found")
        return 0

    kwriteconfig(ctx, record, ctx.home / ".config" / "kdeglobals", ["Icons"], "Theme", icon_theme)

    update_ini_settings(ctx, record, ctx.home / ".config" / "gtk-3.0" / "settings.ini", "Settings", {"gtk-icon-theme-name": icon_theme})
    update_ini_settings(ctx, record, ctx.home / ".config" / "gtk-4.0" / "settings.ini", "Settings", {"gtk-icon-theme-name": icon_theme})
    ctx.theme_status_cache = None
    ctx.console.status("ok", f"icon theme set to {icon_theme}")
    return 0


def reapply_cursor_theme(ctx: RepairContext, record: ActionRecord) -> int:
    status = collect_theme_status(ctx, refresh=True)
    cursor_theme = preferred_asset_name(status, "cursor_theme")
    if not cursor_theme:
        ctx.console.status("skip", "no suitable cursor theme found")
        record.notes.append("no suitable cursor theme found")
        return 0

    kwriteconfig(ctx, record, ctx.home / ".config" / "kcminputrc", ["Mouse"], "cursorTheme", cursor_theme)
    kwriteconfig(ctx, record, ctx.home / ".config" / "kcminputrc", ["Mouse"], "cursorSize", "24")

    update_ini_settings(ctx, record, ctx.home / ".config" / "gtk-3.0" / "settings.ini", "Settings", {"gtk-cursor-theme-name": cursor_theme, "gtk-cursor-theme-size": "24"})
    update_ini_settings(ctx, record, ctx.home / ".config" / "gtk-4.0" / "settings.ini", "Settings", {"gtk-cursor-theme-name": cursor_theme, "gtk-cursor-theme-size": "24"})
    ctx.theme_status_cache = None
    ctx.console.status("ok", f"cursor theme set to {cursor_theme}")
    return 0


def reapply_konsole_profile(ctx: RepairContext, record: ActionRecord) -> int:
    profile_source = first_existing_path(konsole_profile_source_candidates(ctx))
    color_source = first_existing_path(konsole_colors_source_candidates(ctx))
    if not profile_source or not color_source:
        ctx.console.status("skip", "official Konsole profile assets missing")
        record.notes.append("official Konsole profile assets missing")
        return 0

    target_dir = ctx.home / ".local" / "share" / "konsole"
    target_dir.mkdir(parents=True, exist_ok=True)
    copy_user_file(ctx, record, profile_source, target_dir / "KeskOS.profile")
    copy_user_file(ctx, record, color_source, target_dir / "KeskOS.colorscheme")

    if ctx.kwriteconfig_bin:
        kwriteconfig(ctx, record, ctx.home / ".config" / "konsolerc", ["Desktop Entry"], "DefaultProfile", "KeskOS.profile")
    else:
        write_user_text(ctx, record, ctx.home / ".config" / "konsolerc", "[Desktop Entry]\nDefaultProfile=KeskOS.profile\n")

    ctx.console.status("ok", "Konsole profile restored")
    return 0


def reapply_dolphin_config(ctx: RepairContext, record: ActionRecord) -> int:
    candidates: list[Path] = [ctx.usr_root / "share" / "keskos" / "dolphin" / "dolphinrc"]
    if ctx.source_root:
        candidates.extend(
            [
                ctx.source_root / "configs" / "dolphin" / "dolphinrc",
                ctx.source_root / "airootfs" / "etc" / "skel" / ".config" / "dolphinrc",
            ]
        )

    source_path = first_existing_path(candidates)
    if source_path is None:
        ctx.console.status("skip", "no official Dolphin template staged; Dolphin repair skipped")
        record.notes.append("no official Dolphin template staged")
        return 0

    copy_user_file(ctx, record, source_path, ctx.home / ".config" / "dolphinrc")
    ctx.console.status("ok", "Dolphin config restored")
    return 0


def reapply_gtk_kvantum_styling(ctx: RepairContext, record: ActionRecord) -> int:
    status = collect_theme_status(ctx, refresh=True, log=True)
    gtk_theme = preferred_asset_name(status, "gtk_theme")
    icon_theme = preferred_asset_name(status, "icon_theme")
    cursor_theme = preferred_asset_name(status, "cursor_theme")
    kvantum_theme = preferred_asset_name(status, "kvantum_theme")

    applied_any = False
    gtk_updates: dict[str, str] = {"gtk-font-name": GTK_FONT_SETTING}
    if gtk_theme:
        gtk_updates["gtk-theme-name"] = gtk_theme
    if icon_theme:
        gtk_updates["gtk-icon-theme-name"] = icon_theme
    if cursor_theme:
        gtk_updates["gtk-cursor-theme-name"] = cursor_theme
        gtk_updates["gtk-cursor-theme-size"] = "24"

    if gtk_theme or icon_theme or cursor_theme:
        update_ini_settings(ctx, record, ctx.home / ".config" / "gtk-3.0" / "settings.ini", "Settings", gtk_updates)
        update_ini_settings(ctx, record, ctx.home / ".config" / "gtk-4.0" / "settings.ini", "Settings", gtk_updates)
        applied_any = True
        if gtk_theme:
            ctx.console.status("ok", f"GTK theme set to {gtk_theme}")
        else:
            ctx.console.status("skip", "GTK theme asset not found; icon and cursor styling still refreshed")
    else:
        ctx.console.status("skip", "GTK styling assets not found")
        record.notes.append("GTK styling assets not found")

    if kvantum_theme:
        update_ini_settings(ctx, record, ctx.home / ".config" / "Kvantum" / "kvantum.kvconfig", "General", {"theme": kvantum_theme})
        applied_any = True
        ctx.console.status("ok", f"Kvantum theme set to {kvantum_theme}")
    else:
        ctx.console.status("skip", "Kvantum theme not found")
        record.notes.append("Kvantum theme not found")

    ctx.theme_status_cache = None
    if not applied_any:
        return 0
    return 0


def repair_quickshell_hud(ctx: RepairContext, record: ActionRecord) -> int:
    if not command_exists("quickshell"):
        ctx.console.status("skip", "Quickshell not installed, HUD repair skipped")
        record.notes.append("Quickshell not installed")
        return 0

    source_dir = first_existing_path(quickshell_config_source_candidates(ctx))
    if source_dir is None:
        ctx.console.status("skip", "official Quickshell config missing")
        record.notes.append("official Quickshell config missing")
        return 0

    sync_user_directory(ctx, record, source_dir, ctx.home / ".config" / "quickshell" / "keskos")

    for entry_name in ("keskos-quickshell.desktop", "keskos-display-watch.desktop"):
        entry_source = first_existing_path(
            [
                ctx.fs_root / "etc" / "skel" / ".config" / "autostart" / entry_name,
                ctx.home / ".local" / "share" / "keskos" / "source" / "airootfs" / "etc" / "skel" / ".config" / "autostart" / entry_name,
                *( [ctx.source_root / "airootfs" / "etc" / "skel" / ".config" / "autostart" / entry_name] if ctx.source_root else [] ),
            ]
        )
        if entry_source:
            copy_user_file(ctx, record, entry_source, ctx.home / ".config" / "autostart" / entry_name)

    restart_quickshell_if_safe(ctx, record)
    ctx.theme_status_cache = None
    ctx.console.status("ok", "Quickshell HUD config restored")
    return 0


def reapply_browser_homepage(ctx: RepairContext, record: ActionRecord) -> int:
    asset_dir = first_existing_path(browser_asset_source_candidates(ctx))
    if asset_dir is None or not (asset_dir / "index.html").exists():
        ctx.console.status("warn", "browser homepage assets missing")
        record.warnings.append("browser homepage assets missing")
        return 2

    system_startpage = Path("/usr/share/keskos/startpage")
    if not system_startpage.exists() and ctx.source_root:
        exit_code = ensure_system_access(ctx, record)
        if exit_code == 0:
            backup_system_path(ctx, record, Path("/usr/share/keskos/startpage"))
            command = ["rsync", "-a", "--delete", f"{asset_dir}/", f"{system_startpage}/"]
            if os.geteuid() != 0:
                command.insert(0, "sudo")
            capture_command(ctx, record, ["sudo", "install", "-d", "-m", "755", str(system_startpage)] if os.geteuid() != 0 else ["install", "-d", "-m", "755", str(system_startpage)], allow_failure=True)
            capture_command(ctx, record, command, allow_failure=True)

    firefox_userchrome = firefox_userchrome_source(ctx)
    firefox_usercontent = firefox_usercontent_source(ctx)
    brave_policy = brave_policy_source(ctx)
    overall_exit = 0

    firefox_families = [
        ("LibreWolf", ctx.home / ".librewolf"),
        ("Zen Browser", ctx.home / ".zen"),
        ("Firefox", ctx.home / ".mozilla" / "firefox"),
    ]

    for label, config_root in firefox_families:
        if not config_root.exists() or firefox_userchrome is None or firefox_usercontent is None:
            continue
        profiles = find_firefox_profiles(config_root)
        if not profiles:
            record.notes.append(f"{label} profile not found yet")
            continue
        ensure_user_backup(ctx, record, config_root / "profiles.ini")
        for profile in profiles:
            chrome_dir = profile / "chrome"
            chrome_dir.mkdir(parents=True, exist_ok=True)
            copy_user_file(ctx, record, firefox_userchrome, chrome_dir / "userChrome.css")
            copy_user_file(ctx, record, firefox_usercontent, chrome_dir / "userContent.css")
            prefs = [
                'user_pref("toolkit.legacyUserProfileCustomizations.stylesheets", true);',
                f'user_pref("browser.startup.homepage", "{STARTPAGE_URL}");',
                'user_pref("browser.startup.page", 1);',
                'user_pref("browser.newtabpage.enabled", false);',
                'user_pref("browser.aboutConfig.showWarning", false);',
                'user_pref("browser.shell.checkDefaultBrowser", false);',
            ]
            write_user_text(ctx, record, profile / "user.js", "\n".join(prefs) + "\n")
        ctx.console.status("ok", f"{label} homepage repaired for {len(profiles)} profile(s)")

    brave_preferences = ctx.home / ".config" / "BraveSoftware" / "Brave-Browser" / "Default" / "Preferences"
    if brave_preferences.exists():
        try:
            data = json.loads(brave_preferences.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            data = {}
            overall_exit = 2
            record.warnings.append("Brave Preferences could not be parsed")
        if data is not None:
            ensure_user_backup(ctx, record, brave_preferences)
            data.setdefault("browser", {})["show_home_button"] = True
            data["homepage"] = STARTPAGE_URL
            data["homepage_is_newtabpage"] = False
            data.setdefault("session", {})["restore_on_startup"] = 4
            data["session"]["startup_urls"] = [STARTPAGE_URL]
            brave_preferences.write_text(json.dumps(data, indent=2), encoding="utf-8")
            add_changed_record(ctx, record, brave_preferences)
            ctx.console.status("ok", "Brave homepage repaired")
            if brave_policy:
                record.notes.append(f"Brave policy asset available: {brave_policy}")

    if overall_exit == 0:
        ctx.console.status("ok", "browser homepage repair completed")
    else:
        ctx.console.status("warn", "browser homepage repair completed with warnings")
    return overall_exit


def rebuild_caches(ctx: RepairContext, record: ActionRecord) -> int:
    overall_exit = 0

    if ctx.kbuildsycoca_bin:
        result = capture_command(ctx, record, [ctx.kbuildsycoca_bin], timeout=120, allow_failure=True)
        if result.returncode == 0:
            ctx.console.status("ok", "KDE service cache rebuilt")
        else:
            overall_exit = 2
            ctx.console.status("warn", "KDE service cache rebuild reported an error")
    else:
        ctx.console.status("skip", "kbuildsycoca not installed")

    if command_exists("fc-cache"):
        result = capture_command(ctx, record, ["fc-cache", "-f"], timeout=180, allow_failure=True)
        if result.returncode == 0:
            ctx.console.status("ok", "font cache rebuilt")
        else:
            overall_exit = 2
            ctx.console.status("warn", "font cache rebuild reported an error")
    else:
        ctx.console.status("skip", "fc-cache not installed")

    gtk_update = choose_binary("gtk-update-icon-cache")
    if gtk_update:
        icon_roots = [ctx.home / ".local" / "share" / "icons", ctx.home / ".icons"]
        for root_dir in icon_roots:
            if not root_dir.is_dir():
                continue
            for theme_dir in root_dir.iterdir():
                if theme_dir.is_dir() and (theme_dir / "index.theme").exists():
                    capture_command(ctx, record, [gtk_update, "-f", "-t", str(theme_dir)], allow_failure=True)
        ctx.console.status("ok", "user icon caches refreshed where available")
    else:
        ctx.console.status("skip", "gtk-update-icon-cache not installed")

    return overall_exit


def reset_kde_panels(ctx: RepairContext, record: ActionRecord) -> int:
    if ctx.reset_panel_bin is None:
        ctx.console.status("warn", "keskos-reset-panel helper missing")
        record.warnings.append("keskos-reset-panel helper missing")
        return 2

    for path in (
        ctx.home / ".config" / "plasma-org.kde.plasma.desktop-appletsrc",
        ctx.home / ".config" / "plasmashellrc",
        ctx.home / ".config" / "kglobalshortcutsrc",
        ctx.home / ".config" / "kwinrc",
        ctx.home / ".config" / "keskos" / "launcher-mode",
    ):
        ensure_user_backup(ctx, record, path)

    command = [str(ctx.reset_panel_bin)]
    env_prefix = []
    if ctx.source_root:
        env_prefix.append(f"SOURCE_ROOT={ctx.source_root}")
    if ctx.source_root:
        command = ["env", *env_prefix, *command]

    exit_code = stream_logged_command(ctx, record, command)
    if exit_code == 0:
        for path in (
            ctx.home / ".config" / "plasma-org.kde.plasma.desktop-appletsrc",
            ctx.home / ".config" / "plasmashellrc",
            ctx.home / ".config" / "kglobalshortcutsrc",
            ctx.home / ".config" / "kwinrc",
        ):
            add_changed_record(ctx, record, path)
        ctx.console.status("ok", "KeskOS Plasma panels restored")
        return 0

    ctx.console.status("warn", "panel reset failed")
    return 2


def reset_kesk_launcher(ctx: RepairContext, record: ActionRecord) -> int:
    simplekickoff_source = launcher_source_dir(ctx, "org.kde.plasma.simplekickoff")
    workspace_source = launcher_source_dir(ctx, "com.keskos.workspaceswitcher")
    user_plasmoid_root = ctx.home / ".local" / "share" / "plasma" / "plasmoids"

    if simplekickoff_source and not (Path("/usr/share/plasma/plasmoids/org.kde.plasma.simplekickoff").exists()):
        sync_user_directory(ctx, record, simplekickoff_source, user_plasmoid_root / "org.kde.plasma.simplekickoff")
    if workspace_source and not (Path("/usr/share/plasma/plasmoids/com.keskos.workspaceswitcher").exists()):
        sync_user_directory(ctx, record, workspace_source, user_plasmoid_root / "com.keskos.workspaceswitcher")

    helper = ctx.fix_launcher_bin or ctx.launcher_switch_bin
    if helper is None:
        ctx.console.status("warn", "launcher repair helper missing")
        record.warnings.append("launcher repair helper missing")
        return 2

    for path in (
        ctx.home / ".config" / "kglobalshortcutsrc",
        ctx.home / ".config" / "kwinrc",
        ctx.home / ".config" / "plasma-org.kde.plasma.desktop-appletsrc",
        ctx.home / ".config" / "plasmashellrc",
        ctx.home / ".config" / "plasmarc",
        ctx.home / ".config" / "keskos" / "launcher-mode",
    ):
        ensure_user_backup(ctx, record, path)

    if helper.name == "keskos-fix-launcher":
        command = [str(helper)]
    else:
        command = [str(helper), "keskos"]

    if ctx.source_root:
        command = ["env", f"SOURCE_ROOT={ctx.source_root}", *command]

    exit_code = stream_logged_command(ctx, record, command)
    if exit_code == 0:
        ctx.console.status("ok", "Kesk launcher restored")
        return 0

    ctx.console.status("warn", "launcher reset failed")
    return 2


def reapply_sddm_theme(ctx: RepairContext, record: ActionRecord) -> int:
    source_dir = sddm_theme_source_dir(ctx)
    if source_dir is None:
        ctx.console.status("skip", "official SDDM theme missing")
        record.notes.append("official SDDM theme missing")
        return 0

    theme_name = source_dir.name

    exit_code = ensure_system_access(ctx, record)
    if exit_code != 0:
        ctx.console.status("warn", "system permissions are required for SDDM repair")
        return 3

    backup_system_path(ctx, record, Path("/etc/sddm.conf"))
    for conf_path in sorted(Path("/etc/sddm.conf.d").glob("*.conf")) if Path("/etc/sddm.conf.d").is_dir() else []:
        backup_system_path(ctx, record, conf_path)

    if source_dir != Path("/usr/share/sddm/themes") / theme_name:
        backup_system_path(ctx, record, Path("/usr/share/sddm/themes") / theme_name)
        install_command = ["install", "-d", "-m", "755", f"/usr/share/sddm/themes/{theme_name}"]
        if os.geteuid() != 0:
            install_command.insert(0, "sudo")
        capture_command(ctx, record, install_command, allow_failure=True)
        rsync_command = ["rsync", "-a", "--delete", f"{source_dir}/", f"/usr/share/sddm/themes/{theme_name}/"]
        if os.geteuid() != 0:
            rsync_command.insert(0, "sudo")
        sync_result = capture_command(ctx, record, rsync_command, timeout=180, allow_failure=True)
        if sync_result.returncode == 0:
            record.notes.append(f"restored packaged SDDM theme directory: {theme_name}")

    temp_file = Path(tempfile.mkstemp(prefix="kesk-sddm-", suffix=".conf")[1])
    temp_file.write_text(f"[Theme]\nCurrent={theme_name}\n", encoding="utf-8")
    install_command = ["install", "-D", "-m", "644", str(temp_file), "/etc/sddm.conf.d/kesk-theme.conf"]
    if os.geteuid() != 0:
        install_command.insert(0, "sudo")
    result = capture_command(ctx, record, install_command)
    temp_file.unlink(missing_ok=True)

    if result.returncode == 0:
        ctx.theme_status_cache = None
        ctx.console.status("ok", f"SDDM theme restored to {theme_name}")
        return 0

    ctx.console.status("warn", "SDDM theme repair failed")
    return 3


def reapply_plymouth_theme(ctx: RepairContext, record: ActionRecord) -> int:
    status = collect_theme_status(ctx, refresh=True)
    theme_dir = preferred_asset_path(status, "plymouth_theme")
    theme_name = preferred_asset_name(status, "plymouth_theme")
    if theme_dir is None:
        ctx.console.status("skip", "no official Plymouth theme is staged; Plymouth repair skipped")
        record.notes.append("no official Plymouth theme is staged")
        return 0

    if not command_exists("plymouth-set-default-theme"):
        ctx.console.status("warn", "plymouth-set-default-theme is not installed")
        record.warnings.append("plymouth-set-default-theme is not installed")
        return 2

    exit_code = ensure_system_access(ctx, record)
    if exit_code != 0:
        ctx.console.status("warn", "system permissions are required for Plymouth repair")
        return 3

    backup_system_path(ctx, record, Path("/etc/plymouth/plymouthd.conf"))

    command = ["plymouth-set-default-theme", theme_name or theme_dir.name, "-R"]
    if os.geteuid() != 0:
        command.insert(0, "sudo")
    result = stream_logged_command(ctx, record, command, allow_failure=True)
    if result != 0 and command_exists("mkinitcpio"):
        fallback = ["plymouth-set-default-theme", theme_name or theme_dir.name]
        if os.geteuid() != 0:
            fallback.insert(0, "sudo")
        if capture_command(ctx, record, fallback, allow_failure=True).returncode == 0:
            mkinitcpio_command = ["mkinitcpio", "-P"]
            if os.geteuid() != 0:
                mkinitcpio_command.insert(0, "sudo")
            capture_command(ctx, record, mkinitcpio_command, timeout=600, allow_failure=True)
            result = 0

    if result == 0:
        ctx.theme_status_cache = None
        ctx.console.status("ok", f"Plymouth theme restored to {theme_name or theme_dir.name}")
        return 0

    ctx.console.status("warn", "Plymouth repair failed")
    return 3


def refresh_runtime(ctx: RepairContext, record: ActionRecord) -> None:
    if ctx.kbuildsycoca_bin:
        capture_command(ctx, record, [ctx.kbuildsycoca_bin], timeout=120, allow_failure=True)
    if ctx.qdbus_bin and graphical_session_available():
        capture_command(ctx, record, [ctx.qdbus_bin, "org.kde.KWin", "/KWin", "reconfigure"], allow_failure=True)


def show_current_theme_status(ctx: RepairContext, record: ActionRecord) -> int:
    status = collect_theme_status(ctx, refresh=True, log=True)
    ctx.console.line()
    ctx.console.section("ACTIVE CONFIG")
    active_rows = [
        ("Look-and-feel", status.active.get("look_and_feel", "unavailable")),
        ("Plasma theme", status.active.get("plasma_theme", "unavailable")),
        ("Color scheme", status.active.get("color_scheme", "unavailable")),
        ("Window decoration", status.active.get("window_decoration", "unavailable")),
        ("Icon theme", status.active.get("icon_theme", "unavailable")),
        ("Cursor theme", status.active.get("cursor_theme", "unavailable")),
        ("Konsole profile", status.active.get("konsole_profile", "unavailable")),
        ("GTK theme", status.active.get("gtk_theme", "unavailable")),
        ("GTK icon theme", status.active.get("gtk_icon_theme", "unavailable")),
        ("GTK cursor theme", status.active.get("gtk_cursor_theme", "unavailable")),
        ("Kvantum theme", status.active.get("kvantum_theme", "unavailable")),
        ("SDDM theme", status.active.get("sddm_theme", "unavailable")),
        ("Plymouth theme", status.active.get("plymouth_theme", "unavailable")),
    ]
    for label, value in active_rows:
        ctx.console.line(f"{label:<18} {value}")

    ctx.console.section("DETECTED ASSETS")
    asset_rows = [
        ("Look-and-feel", "look_and_feel"),
        ("Plasma theme", "plasma_theme"),
        ("Color schemes", "color_scheme"),
        ("Window decoration", "window_decoration"),
        ("Icon themes", "icon_theme"),
        ("Cursor themes", "cursor_theme"),
        ("Konsole profiles", "konsole_profile"),
        ("GTK themes", "gtk_theme"),
        ("Kvantum themes", "kvantum_theme"),
        ("SDDM themes", "sddm_theme"),
        ("Plymouth themes", "plymouth_theme"),
    ]
    for label, key in asset_rows:
        assets = status.detected.get(key, [])
        if not assets:
            ctx.console.status("skip", f"{label.lower()} not found")
            continue
        ctx.console.status("ok", f"{label.lower()} found: {assets[0].name}")
        for asset in assets[:3]:
            ctx.console.muted(f"  {asset.path}")

    if status.missing_assets:
        ctx.console.section("MISSING ASSETS")
        for label in status.missing_assets:
            ctx.console.status("skip", f"{label} not detected")

    record.notes.append("displayed current theme status")
    return 0


def run_full_visual_identity_repair(ctx: RepairContext, record: ActionRecord) -> int:
    exit_codes = [
        ensure_required_dirs(ctx, record),
        reapply_kde_theme(ctx, record),
        reapply_icon_theme(ctx, record),
        reapply_cursor_theme(ctx, record),
        reapply_konsole_profile(ctx, record),
        reapply_dolphin_config(ctx, record),
        reapply_gtk_kvantum_styling(ctx, record),
        rebuild_caches(ctx, record),
    ]

    ctx.console.line()
    if ctx.console.confirm("Apply SDDM login theme too? This affects the login screen and may require sudo.", default=False):
        exit_codes.append(reapply_sddm_theme(ctx, record))
    else:
        ctx.console.status("skip", "SDDM login theme skipped by user")
        record.notes.append("SDDM login theme skipped by user")

    if ctx.console.confirm("Apply Plymouth boot theme too? This affects the boot splash and will rebuild initramfs.", default=False):
        exit_codes.append(reapply_plymouth_theme(ctx, record))
    else:
        ctx.console.status("skip", "Plymouth boot theme skipped by user")
        record.notes.append("Plymouth boot theme skipped by user")

    refresh_runtime(ctx, record)
    if 3 in exit_codes:
        return 3
    if any(code == 2 for code in exit_codes):
        return 2
    return 0


def run_safe_repair(ctx: RepairContext, record: ActionRecord) -> int:
    exit_codes = [
        ensure_required_dirs(ctx, record),
        reapply_kde_theme(ctx, record),
        reapply_icon_theme(ctx, record),
        reapply_cursor_theme(ctx, record),
        reapply_konsole_profile(ctx, record),
        reapply_dolphin_config(ctx, record),
        reapply_gtk_kvantum_styling(ctx, record),
        rebuild_caches(ctx, record),
    ]
    ctx.console.status("skip", "Plasma panel reset skipped in safe repair")
    ctx.console.status("skip", "SDDM login theme skipped in safe repair")
    ctx.console.status("skip", "Plymouth boot theme skipped in safe repair")
    ctx.console.status("skip", "Quickshell HUD skipped in safe repair")
    record.notes.extend(
        [
            "Plasma panel reset skipped in safe repair",
            "SDDM login theme skipped in safe repair",
            "Plymouth boot theme skipped in safe repair",
            "Quickshell HUD skipped in safe repair",
        ]
    )
    refresh_runtime(ctx, record)
    if 3 in exit_codes:
        return 3
    if any(code == 2 for code in exit_codes):
        return 2
    return 0


def finalize_record(record: ActionRecord, exit_code: int) -> int:
    record.exit_code = exit_code
    record.completed_at = datetime.now().isoformat()
    if exit_code == 0:
        record.status = "completed"
    elif exit_code == 3:
        record.status = "permission-required"
    else:
        record.status = "failed"
    return exit_code


def action_header(console: KeskConsole, subtitle: str) -> None:
    console.clear()
    console.header("KESK REPAIR CONSOLE", subtitle)


def render_menu(console: KeskConsole, logger: SessionLogger) -> None:
    console.clear()
    console.header("KESK REPAIR CONSOLE", "RESTORE DESKTOP STACK // THEME CHAIN // BOOT IDENTITY")
    console.line()
    console.status("ok", f"session log: {logger.path}")
    console.line()
    console.menu(
        [
            "[1] Run safe repair",
            "[2] Reset KDE Plasma panels",
            "[3] Reset Kesk launcher",
            "[4] Reapply full KeskOS visual identity",
            "[5] Reapply Plasma theme/colors",
            "[6] Reapply icon theme",
            "[7] Reapply cursor theme",
            "[8] Reapply Konsole profile",
            "[9] Reapply Dolphin config",
            "[10] Reapply GTK/Kvantum styling",
            "[11] Reapply SDDM login theme",
            "[12] Reapply Plymouth boot theme",
            "[13] Repair Quickshell HUD",
            "[14] Rebuild icon/font cache",
            "[15] Show current theme status",
            "[16] Export repair report",
            "[17] Exit",
        ]
    )


def build_report(ctx: RepairContext) -> str:
    theme_status = collect_theme_status(ctx, refresh=True)
    lines = [
        "KESK REPAIR REPORT",
        f"Generated: {datetime.now().isoformat()}",
        f"User: {ctx.user}",
        f"Home: {ctx.home}",
        f"Source root: {ctx.source_root or 'not found'}",
        f"Current log: {ctx.logger.path}",
        "",
        "THEME STATUS",
        f"- look-and-feel: {theme_status.active.get('look_and_feel', 'unavailable')}",
        f"- Plasma theme: {theme_status.active.get('plasma_theme', 'unavailable')}",
        f"- color scheme: {theme_status.active.get('color_scheme', 'unavailable')}",
        f"- window decoration: {theme_status.active.get('window_decoration', 'unavailable')}",
        f"- icon theme: {theme_status.active.get('icon_theme', 'unavailable')}",
        f"- cursor theme: {theme_status.active.get('cursor_theme', 'unavailable')}",
        f"- Konsole profile: {theme_status.active.get('konsole_profile', 'unavailable')}",
        f"- GTK theme: {theme_status.active.get('gtk_theme', 'unavailable')}",
        f"- GTK icon theme: {theme_status.active.get('gtk_icon_theme', 'unavailable')}",
        f"- GTK cursor theme: {theme_status.active.get('gtk_cursor_theme', 'unavailable')}",
        f"- Kvantum theme: {theme_status.active.get('kvantum_theme', 'unavailable')}",
        f"- SDDM theme: {theme_status.active.get('sddm_theme', 'unavailable')}",
        f"- Plymouth theme: {theme_status.active.get('plymouth_theme', 'unavailable')}",
        "",
        "DETECTED THEME ASSETS",
    ]

    asset_labels = {
        "look_and_feel": "look-and-feel packages",
        "plasma_theme": "Plasma themes",
        "color_scheme": "color schemes",
        "window_decoration": "window decorations",
        "icon_theme": "icon themes",
        "cursor_theme": "cursor themes",
        "konsole_profile": "Konsole profiles",
        "gtk_theme": "GTK themes",
        "kvantum_theme": "Kvantum themes",
        "sddm_theme": "SDDM themes",
        "plymouth_theme": "Plymouth themes",
    }
    for key, label in asset_labels.items():
        assets = theme_status.detected.get(key, [])
        if not assets:
            lines.append(f"- {label}: none")
            continue
        joined = ", ".join(f"{asset.name} ({asset.path})" for asset in assets[:3])
        lines.append(f"- {label}: {joined}")

    if theme_status.missing_assets:
        lines.extend(["", "MISSING THEME ASSETS"])
        lines.extend(f"- {label}" for label in theme_status.missing_assets)

    lines.extend(["", "ACTION SUMMARY"])

    if not ctx.action_records:
        lines.append("- no repair actions were executed")
    else:
        for record in ctx.action_records:
            lines.append(f"- {record.label}: {record.status} (exit {record.exit_code})")

    lines.extend(["", "BACKUPS"])
    backup_entries = [entry for record in ctx.action_records for entry in record.backups]
    lines.extend(f"- {entry}" for entry in backup_entries) if backup_entries else lines.append("- none")

    lines.extend(["", "FILES CHANGED"])
    changed_entries = [entry for record in ctx.action_records for entry in record.changed_files]
    lines.extend(f"- {entry}" for entry in changed_entries) if changed_entries else lines.append("- none")

    lines.extend(["", "COMMANDS"])
    command_entries = [command for record in ctx.action_records for command in record.commands]
    if command_entries:
        for item in command_entries:
            lines.append(f"- [{item.exit_code}] {item.command}")
    else:
        lines.append("- none")

    lines.extend(["", "WARNINGS, SKIPPED ITEMS, AND NOTES"])
    warning_lines = [warning for record in ctx.action_records for warning in (*record.warnings, *record.notes)]
    lines.extend(f"- {item}" for item in warning_lines) if warning_lines else lines.append("- none")

    lines.extend(
        [
            "",
            "BACKUP LOCATIONS",
            f"- user backups: {ctx.user_backup_root}",
            f"- system backups: {ctx.system_backup_root}",
            "",
            "NOT INCLUDED",
            "- passwords",
            "- SSH keys",
            "- browser cookies",
            "- tokens",
            "- unrelated user data",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def theme_status_payload(status: ThemeStatus) -> dict[str, object]:
    return {
        "active": status.active,
        "detected": {
            key: [{"name": asset.name, "path": str(asset.path)} for asset in assets]
            for key, assets in status.detected.items()
        },
        "missing_assets": status.missing_assets,
    }


def context_status_payload(ctx: RepairContext) -> dict[str, object]:
    status = collect_theme_status(ctx, refresh=True, log=True)
    return {
        "theme_status": theme_status_payload(status),
        "paths": {
            "home": str(ctx.home),
            "user_backup_root": str(ctx.user_backup_root),
            "system_backup_root": str(ctx.system_backup_root),
            "report_path": str(ctx.report_path),
            "log_path": str(ctx.logger.path),
            "source_root": str(ctx.source_root) if ctx.source_root else None,
        },
        "helpers": {
            "kwriteconfig": ctx.kwriteconfig_bin,
            "kbuildsycoca": ctx.kbuildsycoca_bin,
            "qdbus": ctx.qdbus_bin,
            "lookandfeeltool": ctx.lookandfeeltool_bin,
            "plasma_apply_colorscheme": ctx.plasma_apply_colorscheme_bin,
            "configure_user": str(ctx.configure_user_bin) if ctx.configure_user_bin else None,
            "reset_panel": str(ctx.reset_panel_bin) if ctx.reset_panel_bin else None,
            "launcher_switch": str(ctx.launcher_switch_bin) if ctx.launcher_switch_bin else None,
            "fix_launcher": str(ctx.fix_launcher_bin) if ctx.fix_launcher_bin else None,
            "quickshell_wrapper": str(ctx.quickshell_wrapper_bin) if ctx.quickshell_wrapper_bin else None,
        },
    }


def print_json_payload(payload: dict[str, object]) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def export_report(ctx: RepairContext, record: ActionRecord) -> int:
    record.status = "completed"
    record.exit_code = 0
    record.completed_at = datetime.now().isoformat()
    try:
        ctx.report_path.write_text(build_report(ctx), encoding="utf-8")
    except OSError as exc:
        ctx.console.status("warn", f"failed to export repair report: {exc}")
        record.warnings.append(str(exc))
        return 2

    add_changed_record(ctx, record, ctx.report_path)
    ctx.console.status("ok", f"repair report exported: {ctx.report_path}")
    return 0


def export_report_noninteractive(ctx: RepairContext, record: ActionRecord) -> int:
    record.status = "completed"
    record.exit_code = 0
    record.completed_at = datetime.now().isoformat()
    try:
        ctx.report_path.write_text(build_report(ctx), encoding="utf-8")
    except OSError as exc:
        record.warnings.append(str(exc))
        return 2

    add_changed_record(ctx, record, ctx.report_path)
    return 0


def perform_action(
    ctx: RepairContext,
    key: str,
    label: str,
    subtitle: str,
    prompt: str,
    callback,
    *,
    confirm: bool = True,
) -> int:
    record = ActionRecord(key=key, label=label)
    ctx.action_records.append(record)

    action_header(ctx.console, subtitle)
    if confirm and not ctx.console.confirm(prompt, default=False):
        record.status = "cancelled"
        record.completed_at = datetime.now().isoformat()
        ctx.logger.log(f"selected_action={key}:cancelled")
        ctx.console.status("skip", "repair action cancelled")
        ctx.console.pause("Press Enter to return to the menu")
        return 0

    ctx.logger.log(f"selected_action={key}")
    exit_code = callback(ctx, record)
    finalize_record(record, exit_code)

    ctx.console.line()
    if exit_code == 0:
        ctx.console.status("ok", f"{label.lower()} completed")
    elif exit_code == 3:
        ctx.console.status("warn", f"{label.lower()} needs system permissions")
    else:
        ctx.console.status("warn", f"{label.lower()} completed with errors")
    ctx.console.pause("Press Enter to return to the menu")
    return exit_code


def print_help(console: KeskConsole) -> int:
    console.header("KESK REPAIR CONSOLE", "SAFE BRANDED DESKTOP REPAIR")
    console.line("Usage: kesk repair")
    console.line("       kesk repair --status --json")
    console.line("       kesk repair --safe|--panels|--launcher|--visual-identity|--plasma|--icons|--cursor")
    console.line("                    --konsole|--dolphin|--gtk-kvantum|--sddm|--plymouth|--quickshell|--cache")
    console.line("                    [--yes]")
    console.line()
    console.line("Repairs:")
    console.line("- Plasma panels, launcher, and the full KeskOS visual identity")
    console.line("- Plasma theme/colors, icon theme, cursor theme, Konsole, Dolphin, and GTK/Kvantum styling")
    console.line("- SDDM, Plymouth, and Quickshell HUD recovery with confirmations where required")
    console.line("- read-only theme status plus targeted backups before changing user or system config files")
    console.line("- theme repair lives here; there is no separate `kesk theme` command")
    console.line("- `--yes` only skips the Kesk repair confirmation prompt; system tools may still ask normally")
    return 0


def build_context(console: KeskConsole, logger: SessionLogger, root: Path) -> RepairContext:
    user = resolve_user()
    home = resolve_home(user)
    session_stamp = datetime.now().strftime(BACKUP_TIME_FORMAT)
    usr_root = root.parents[1]
    fs_root = root.parents[2] if len(root.parents) > 2 else Path("/")

    ctx = RepairContext(
        console=console,
        logger=logger,
        root=root,
        usr_root=usr_root,
        fs_root=fs_root,
        user=user,
        home=home,
        session_stamp=session_stamp,
        user_backup_root=home / ".local" / "state" / "kesk" / "backups" / session_stamp / "repair",
        system_backup_root=Path("/var/lib/kesk/backups") / session_stamp / "repair",
        report_path=home / "kesk-repair-report.txt",
    )
    ctx.source_root = resolve_source_root(root, home)
    ctx.kwriteconfig_bin = choose_binary("kwriteconfig6", "kwriteconfig5")
    ctx.kbuildsycoca_bin = choose_binary("kbuildsycoca6", "kbuildsycoca5")
    ctx.qdbus_bin = choose_binary("qdbus6", "qdbus")
    ctx.lookandfeeltool_bin = choose_binary("lookandfeeltool")
    ctx.plasma_apply_colorscheme_bin = choose_binary("plasma-apply-colorscheme")
    ctx.configure_user_bin = resolve_helper(root, "keskos-configure-user", prefer_local_bin=True)
    ctx.reset_panel_bin = resolve_helper(root, "keskos-reset-panel")
    ctx.launcher_switch_bin = resolve_helper(root, "keskos-launcher-switch")
    ctx.fix_launcher_bin = resolve_helper(root, "keskos-fix-launcher")
    ctx.quickshell_wrapper_bin = resolve_helper(root, "keskos-shell", prefer_local_bin=True)
    return ctx


def direct_action_specs():
    return {
        "--safe": (
            "safe-repair",
            "SAFE REPAIR",
            "SAFE REPAIR",
            "Run safe repair now?",
            run_safe_repair,
        ),
        "--panels": (
            "reset-panels",
            "RESET KDE PLASMA PANELS",
            "RESET PLASMA PANELS",
            "Reset the Plasma panel layout? This changes desktop layout.",
            reset_kde_panels,
        ),
        "--launcher": (
            "reset-launcher",
            "RESET KESK LAUNCHER",
            "RESTORE KESK LAUNCHER",
            "Restore the Kesk launcher and launcher wiring?",
            reset_kesk_launcher,
        ),
        "--visual-identity": (
            "visual-identity",
            "REAPPLY FULL KESKOS VISUAL IDENTITY",
            "FULL VISUAL IDENTITY REPAIR",
            "Reapply the full KeskOS visual identity now?",
            run_full_visual_identity_repair,
        ),
        "--plasma": (
            "plasma-theme",
            "REAPPLY PLASMA THEME/COLORS",
            "REAPPLY PLASMA THEME/COLORS",
            "Reapply the Plasma theme and color chain?",
            reapply_kde_theme,
        ),
        "--icons": (
            "icon-theme",
            "REAPPLY ICON THEME",
            "REAPPLY ICON THEME",
            "Reapply the icon theme fallback chain?",
            reapply_icon_theme,
        ),
        "--cursor": (
            "cursor-theme",
            "REAPPLY CURSOR THEME",
            "REAPPLY CURSOR THEME",
            "Reapply the cursor theme fallback chain?",
            reapply_cursor_theme,
        ),
        "--konsole": (
            "konsole",
            "REAPPLY KONSOLE PROFILE",
            "RESTORE KONSOLE PROFILE",
            "Restore the KeskOS Konsole profile?",
            reapply_konsole_profile,
        ),
        "--dolphin": (
            "dolphin",
            "REAPPLY DOLPHIN CONFIG",
            "RESTORE DOLPHIN CONFIG",
            "Restore Dolphin defaults if an official template exists?",
            reapply_dolphin_config,
        ),
        "--gtk-kvantum": (
            "gtk-kvantum",
            "REAPPLY GTK/KVANTUM STYLING",
            "REAPPLY GTK/KVANTUM STYLING",
            "Reapply GTK and Kvantum styling where assets exist?",
            reapply_gtk_kvantum_styling,
        ),
        "--sddm": (
            "sddm",
            "REAPPLY SDDM LOGIN THEME",
            "RESTORE SDDM LOGIN THEME",
            "Restore the KeskOS SDDM login theme? This affects the login screen and may require sudo.",
            reapply_sddm_theme,
        ),
        "--plymouth": (
            "plymouth",
            "REAPPLY PLYMOUTH BOOT THEME",
            "RESTORE PLYMOUTH BOOT THEME",
            "Restore the KeskOS Plymouth splash? This affects the boot splash and will rebuild initramfs.",
            reapply_plymouth_theme,
        ),
        "--quickshell": (
            "quickshell",
            "REPAIR QUICKSHELL HUD",
            "RESTORE QUICKSHELL HUD",
            "Restore the KeskOS Quickshell HUD config?",
            repair_quickshell_hud,
        ),
        "--cache": (
            "rebuild-caches",
            "REBUILD ICON/FONT CACHE",
            "REBUILD ICON AND FONT CACHES",
            "Rebuild the icon and font caches now?",
            rebuild_caches,
        ),
    }


def perform_direct_action(
    ctx: RepairContext,
    key: str,
    label: str,
    subtitle: str,
    prompt: str,
    callback,
    *,
    auto_confirm: bool,
) -> int:
    record = ActionRecord(key=key, label=label)
    ctx.action_records.append(record)

    action_header(ctx.console, subtitle)
    if not auto_confirm and not ctx.console.confirm(prompt, default=False):
        record.status = "cancelled"
        record.completed_at = datetime.now().isoformat()
        ctx.logger.log(f"selected_action={key}:cancelled")
        ctx.console.status("skip", "repair action cancelled")
        return 0

    ctx.logger.log(f"selected_action={key}")
    exit_code = callback(ctx, record)
    finalize_record(record, exit_code)
    ctx.console.line()
    if exit_code == 0:
        ctx.console.status("ok", f"{label.lower()} completed")
    elif exit_code == 3:
        ctx.console.status("warn", f"{label.lower()} needs system permissions")
    else:
        ctx.console.status("warn", f"{label.lower()} completed with errors")
    return exit_code


def main(args: Sequence[str], root: Path) -> int:
    console = KeskConsole()
    arg_set = set(args)
    if args and args[0] in {"--help", "-h", "help"}:
        return print_help(console)

    logger = SessionLogger("repair")
    ctx = build_context(console, logger, root)
    last_exit_code = 0

    try:
        if "--status" in arg_set and "--json" in arg_set:
            print_json_payload(context_status_payload(ctx))
            return 0

        if "--status" in arg_set:
            record = ActionRecord(key="theme-status", label="SHOW CURRENT THEME STATUS")
            ctx.action_records.append(record)
            action_header(console, "CURRENT THEME STATUS")
            exit_code = show_current_theme_status(ctx, record)
            finalize_record(record, exit_code)
            return exit_code

        if "--export-report" in arg_set:
            record = ActionRecord(key="export-report", label="EXPORT REPAIR REPORT")
            ctx.action_records.append(record)
            exit_code = export_report_noninteractive(ctx, record)
            finalize_record(record, exit_code)
            if exit_code == 0:
                console.status("ok", f"repair report exported: {ctx.report_path}")
            else:
                console.status("warn", "failed to export repair report")
            return exit_code

        direct_specs = direct_action_specs()
        direct_flags = [flag for flag in direct_specs if flag in arg_set]
        if direct_flags:
            spec = direct_specs[direct_flags[0]]
            return perform_direct_action(ctx, *spec, auto_confirm="--yes" in arg_set)

        collect_theme_status(ctx, refresh=True, log=True)
        while True:
            render_menu(console, logger)
            choice = console.input("Select action").strip()

            if choice == "17":
                logger.log("selected_action=exit")
                return last_exit_code
            if choice == "1":
                last_exit_code = perform_action(ctx, "safe-repair", "SAFE REPAIR", "SAFE REPAIR", "Run safe repair now?", run_safe_repair)
                continue
            if choice == "2":
                last_exit_code = perform_action(ctx, "reset-panels", "RESET KDE PLASMA PANELS", "RESET PLASMA PANELS", "Reset the Plasma panel layout? This changes desktop layout.", reset_kde_panels)
                continue
            if choice == "3":
                last_exit_code = perform_action(ctx, "reset-launcher", "RESET KESK LAUNCHER", "RESTORE KESK LAUNCHER", "Restore the Kesk launcher and launcher wiring?", reset_kesk_launcher)
                continue
            if choice == "4":
                last_exit_code = perform_action(ctx, "visual-identity", "REAPPLY FULL KESKOS VISUAL IDENTITY", "FULL VISUAL IDENTITY REPAIR", "Reapply the full KeskOS visual identity now?", run_full_visual_identity_repair)
                continue
            if choice == "5":
                last_exit_code = perform_action(ctx, "plasma-theme", "REAPPLY PLASMA THEME/COLORS", "REAPPLY PLASMA THEME/COLORS", "Reapply the Plasma theme and color chain?", reapply_kde_theme)
                continue
            if choice == "6":
                last_exit_code = perform_action(ctx, "icon-theme", "REAPPLY ICON THEME", "REAPPLY ICON THEME", "Reapply the icon theme fallback chain?", reapply_icon_theme)
                continue
            if choice == "7":
                last_exit_code = perform_action(ctx, "cursor-theme", "REAPPLY CURSOR THEME", "REAPPLY CURSOR THEME", "Reapply the cursor theme fallback chain?", reapply_cursor_theme)
                continue
            if choice == "8":
                last_exit_code = perform_action(ctx, "konsole", "REAPPLY KONSOLE PROFILE", "RESTORE KONSOLE PROFILE", "Restore the KeskOS Konsole profile?", reapply_konsole_profile)
                continue
            if choice == "9":
                last_exit_code = perform_action(ctx, "dolphin", "REAPPLY DOLPHIN CONFIG", "RESTORE DOLPHIN CONFIG", "Restore Dolphin defaults if an official template exists?", reapply_dolphin_config)
                continue
            if choice == "10":
                last_exit_code = perform_action(ctx, "gtk-kvantum", "REAPPLY GTK/KVANTUM STYLING", "REAPPLY GTK/KVANTUM STYLING", "Reapply GTK and Kvantum styling where assets exist?", reapply_gtk_kvantum_styling)
                continue
            if choice == "11":
                last_exit_code = perform_action(ctx, "sddm", "REAPPLY SDDM LOGIN THEME", "RESTORE SDDM LOGIN THEME", "Restore the KeskOS SDDM login theme? This affects the login screen and may require sudo.", reapply_sddm_theme)
                continue
            if choice == "12":
                last_exit_code = perform_action(ctx, "plymouth", "REAPPLY PLYMOUTH BOOT THEME", "RESTORE PLYMOUTH BOOT THEME", "Restore the KeskOS Plymouth splash? This affects the boot splash and will rebuild initramfs.", reapply_plymouth_theme)
                continue
            if choice == "13":
                last_exit_code = perform_action(ctx, "quickshell", "REPAIR QUICKSHELL HUD", "RESTORE QUICKSHELL HUD", "Restore the KeskOS Quickshell HUD config?", repair_quickshell_hud)
                continue
            if choice == "14":
                last_exit_code = perform_action(ctx, "rebuild-caches", "REBUILD ICON/FONT CACHE", "REBUILD ICON AND FONT CACHES", "Rebuild the icon and font caches now?", rebuild_caches)
                continue
            if choice == "15":
                last_exit_code = perform_action(ctx, "theme-status", "SHOW CURRENT THEME STATUS", "CURRENT THEME STATUS", "", show_current_theme_status, confirm=False)
                continue
            if choice == "16":
                last_exit_code = perform_action(ctx, "export-report", "EXPORT REPAIR REPORT", "EXPORT REPAIR REPORT", "Export the current repair report?", export_report)
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
        console.header("KESK REPAIR CONSOLE", "ERROR")
        console.status("warn", f"repair failed: {exc}")
        return 1
    finally:
        logger.close()
