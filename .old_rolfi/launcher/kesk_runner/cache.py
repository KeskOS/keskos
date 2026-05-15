from __future__ import annotations

import configparser
import json
import os
import time
from pathlib import Path

try:
    from xdg.DesktopEntry import DesktopEntry
    from xdg.Exceptions import ParsingError
except ModuleNotFoundError:  # pragma: no cover - optional runtime dependency
    DesktopEntry = None
    ParsingError = Exception

from .utils import cache_home

APP_CACHE_TTL = 3600
FILE_CACHE_TTL = 900
APP_CACHE_VERSION = 1
FILE_CACHE_VERSION = 1


def cache_dir() -> Path:
    path = cache_home() / "keskos" / "launcher"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _read_payload(path: Path) -> dict | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _write_payload(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, separators=(",", ":")), encoding="utf-8")


def _cache_state(path: Path, ttl: int, version: int) -> tuple[dict | None, bool]:
    payload = _read_payload(path)
    if not payload or payload.get("version") != version:
        return payload, True
    generated = payload.get("generated", 0)
    return payload, (time.time() - generated) > ttl


def desktop_dirs() -> list[Path]:
    directories = [Path("/usr/share/applications"), Path.home() / ".local/share/applications"]
    return [directory for directory in directories if directory.is_dir()]


def _desktop_id(path: Path, roots: list[Path]) -> str:
    for root in roots:
        try:
            relpath = path.relative_to(root)
        except ValueError:
            continue
        return str(relpath).replace("/", "-")
    return path.name


def _fallback_desktop_entry(desktop_file: Path) -> dict | None:
    parser = configparser.ConfigParser(interpolation=None, strict=False)
    try:
        parser.read(desktop_file, encoding="utf-8")
    except (OSError, configparser.Error, UnicodeDecodeError):
        return None

    if not parser.has_section("Desktop Entry"):
        return None

    entry = parser["Desktop Entry"]
    if entry.get("Type", "").strip() != "Application":
        return None

    hidden = entry.get("Hidden", "").strip().lower()
    nodisplay = entry.get("NoDisplay", "").strip().lower()
    if hidden == "true" or nodisplay == "true":
        return None

    name = entry.get("Name", "").strip()
    if not name:
        return None

    categories = [item for item in entry.get("Categories", "").split(";") if item]
    return {
        "name": name,
        "generic_name": entry.get("GenericName", "").strip(),
        "comment": entry.get("Comment", "").strip(),
        "exec": entry.get("Exec", "").strip(),
        "categories": categories,
        "icon": entry.get("Icon", "").strip(),
    }


def build_app_cache() -> list[dict]:
    roots = desktop_dirs()
    entries: list[dict] = []
    seen: set[str] = set()

    for root in roots:
        for desktop_file in root.rglob("*.desktop"):
            if DesktopEntry is not None:
                try:
                    entry = DesktopEntry(str(desktop_file))
                except (ParsingError, OSError):
                    continue

                try:
                    if entry.getType() != "Application":
                        continue
                    if entry.getHidden() or entry.getNoDisplay():
                        continue
                except Exception:
                    continue

                entry_data = {
                    "name": (entry.getName() or "").strip(),
                    "generic_name": (entry.getGenericName() or "").strip(),
                    "comment": (entry.getComment() or "").strip(),
                    "exec": (entry.getExec() or "").strip(),
                    "categories": [item for item in (entry.getCategories() or []) if item],
                    "icon": (entry.getIcon() or "").strip(),
                }
            else:
                entry_data = _fallback_desktop_entry(desktop_file)
                if entry_data is None:
                    continue

            name = entry_data["name"]

            desktop_id = _desktop_id(desktop_file, roots)
            if desktop_id in seen:
                continue
            seen.add(desktop_id)

            entries.append(
                {
                    "desktop_id": desktop_id,
                    "name": name,
                    "generic_name": entry_data["generic_name"],
                    "comment": entry_data["comment"],
                    "exec": entry_data["exec"],
                    "categories": entry_data["categories"],
                    "icon": entry_data["icon"],
                }
            )

    entries.sort(key=lambda item: item["name"].lower())
    _write_payload(
        cache_dir() / "apps.json",
        {"version": APP_CACHE_VERSION, "generated": int(time.time()), "items": entries},
    )
    return entries


def load_app_cache(sync_if_missing: bool = True) -> tuple[list[dict], bool]:
    cache_path = cache_dir() / "apps.json"
    payload, stale = _cache_state(cache_path, APP_CACHE_TTL, APP_CACHE_VERSION)

    if payload:
        if stale and sync_if_missing:
            return build_app_cache(), False
        return list(payload.get("items", [])), stale

    if sync_if_missing:
        return build_app_cache(), False
    return [], True


def file_roots() -> list[Path]:
    home = Path.home()
    roots = [
        home,
        home / "Desktop",
        home / "Downloads",
        home / "Documents",
        home / "Pictures",
        home / "Videos",
        home / "Music",
    ]
    return [root for root in roots if root.exists()]


def _iter_home_entries(path: Path) -> list[Path]:
    try:
        return [child for child in path.iterdir() if not child.name.startswith(".")]
    except OSError:
        return []


def build_file_cache() -> list[dict]:
    entries: list[dict] = []
    seen: set[str] = set()

    for root in file_roots():
        if root == Path.home():
            candidates = _iter_home_entries(root)
        else:
            candidates = []
            for current_root, directories, files in os.walk(root):
                directories[:] = [item for item in directories if not item.startswith(".")]
                files = [item for item in files if not item.startswith(".")]
                current_path = Path(current_root)
                candidates.extend(current_path / name for name in directories)
                candidates.extend(current_path / name for name in files)

        for candidate in candidates:
            path_text = str(candidate)
            if path_text in seen:
                continue
            seen.add(path_text)
            entries.append(
                {
                    "path": path_text,
                    "name": candidate.name or path_text,
                    "relative": path_text.replace(str(Path.home()), "~", 1),
                    "is_dir": candidate.is_dir(),
                }
            )

    entries.sort(key=lambda item: item["relative"].lower())
    _write_payload(
        cache_dir() / "files.json",
        {"version": FILE_CACHE_VERSION, "generated": int(time.time()), "items": entries},
    )
    return entries


def load_file_cache(sync_if_missing: bool = False) -> tuple[list[dict], bool]:
    cache_path = cache_dir() / "files.json"
    payload, stale = _cache_state(cache_path, FILE_CACHE_TTL, FILE_CACHE_VERSION)

    if payload:
        if stale and sync_if_missing:
            return build_file_cache(), False
        return list(payload.get("items", [])), stale

    if sync_if_missing:
        return build_file_cache(), False
    return [], True


def warm_caches(sync_files: bool = True) -> None:
    load_app_cache(sync_if_missing=True)
    if sync_files:
        load_file_cache(sync_if_missing=True)
