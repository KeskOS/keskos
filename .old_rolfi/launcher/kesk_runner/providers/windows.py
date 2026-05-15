from __future__ import annotations

import re
import shutil
import subprocess

from ..models import Result, SearchContext
from ..utils import (
    CATEGORY_WEIGHTS,
    is_kwin_window_id,
    kdotool_path,
    kdotool_search_pattern,
    launcher_debug_log,
    match_score,
)


WAYLAND_SKIP_CLASSES = {
    "ksmserver",
    "krunner",
    "plasmawindowed",
    "plasmashell",
    "quickshell",
    "rofi",
    "xdg-desktop-portal-kde",
}

WAYLAND_SKIP_TITLE_RE = re.compile(r"(?:^|[\s-])(rofi|krunner)(?:$|[\s-])", re.IGNORECASE)


def _wayland_fallback_results(query: str, message: str) -> list[Result]:
    return [
        Result(
            id="windows:kdotool-status",
            title=message,
            subtitle="Install kdotool-bin with yay/paru for in-launcher Wayland window switching.",
            category="Windows",
            score=CATEGORY_WEIGHTS["Windows"] + 2200,
            action={"type": "noop"},
            nonselectable=True,
            permanent=True,
            terms=["kdotool", "wayland", "windows", "kwin"],
        ),
        Result(
            id="windows:kde-fallback",
            title="Open KDE Window Runner",
            subtitle="Fallback outside the launcher while kdotool is unavailable.",
            category="Windows",
            score=CATEGORY_WEIGHTS["Windows"] + 2100,
            action={"type": "krunner-windows", "query": query},
            terms=["windows", "wayland", "krunner", "fallback", "kde"],
        ),
    ]


def _should_skip_wayland_window(title: str, window_class: str) -> bool:
    normalized_class = window_class.strip().lower()
    normalized_title = title.strip().lower()
    if normalized_class in WAYLAND_SKIP_CLASSES:
        return True
    if WAYLAND_SKIP_TITLE_RE.search(normalized_title):
        return True
    return False


def _run_kdotool(argv: list[str]) -> subprocess.CompletedProcess[str]:
    launcher_debug_log(f"kdotool argv={argv!r}")
    completed = subprocess.run(argv, capture_output=True, text=True, check=False)
    launcher_debug_log(
        "kdotool rc="
        + str(completed.returncode)
        + f" stdout={completed.stdout!r} stderr={completed.stderr!r}"
    )
    return completed


def _active_wayland_window_id(binary: str) -> str | None:
    completed = _run_kdotool([binary, "getactivewindow"])
    if completed.returncode != 0:
        return None

    for line in completed.stdout.splitlines():
        candidate = line.strip()
        if is_kwin_window_id(candidate):
            return candidate
    return None


def _search_wayland_windows(query: str) -> tuple[list[Result], str | None]:
    binary = kdotool_path()
    if not binary:
        return _wayland_fallback_results(query, "kdotool is missing"), None

    pattern = kdotool_search_pattern(query)
    completed = _run_kdotool(
        [
            binary,
            "search",
            "--limit",
            "40",
            pattern,
            "getwindowid",
            "%@",
            "getwindowname",
            "%@",
            "getwindowclassname",
            "%@",
        ]
    )
    if completed.returncode != 0:
        return _wayland_fallback_results(query, "kdotool could not query KWin windows"), (
            "kdotool failed while asking KWin for the current window list."
        )

    lines = [line.strip() for line in completed.stdout.splitlines()]
    count = 0
    while count < len(lines) and is_kwin_window_id(lines[count]):
        count += 1

    if count == 0:
        if query.strip():
            return [
                Result(
                    id="windows:no-match",
                    title="No matching windows",
                    subtitle="No open Wayland window matched the current search.",
                    category="Windows",
                    score=CATEGORY_WEIGHTS["Windows"] + 2000,
                    action={"type": "noop"},
                    nonselectable=True,
                    permanent=True,
                )
            ], None
        return [
            Result(
                id="windows:none-open",
                title="No open windows found",
                subtitle="kdotool did not return any normal application windows.",
                category="Windows",
                score=CATEGORY_WEIGHTS["Windows"] + 2000,
                action={"type": "noop"},
                nonselectable=True,
                permanent=True,
            )
        ], None

    expected_lines = count * 3
    if len(lines) < expected_lines:
        launcher_debug_log(
            f"kdotool parse-mismatch count={count} lines={len(lines)} raw_lines={lines!r}"
        )
        return _wayland_fallback_results(query, "kdotool returned unexpected window data"), (
            "kdotool returned output that the launcher could not parse."
        )

    window_ids = lines[:count]
    titles = lines[count : count * 2]
    classes = lines[count * 2 : count * 3]
    active_id = _active_wayland_window_id(binary)

    results: list[Result] = []
    for window_id, title, window_class in zip(window_ids, titles, classes, strict=False):
        if _should_skip_wayland_window(title, window_class):
            continue

        display_title = title or window_class or "Untitled window"
        subtitle = window_class or "Wayland window"
        if active_id == window_id:
            subtitle = f"{subtitle} | Focused now"

        score = match_score(query, [display_title, window_class, window_id])
        if query and score is None:
            continue

        results.append(
            Result(
                id=f"window:{window_id}",
                title=display_title,
                subtitle=subtitle,
                category="Windows",
                score=CATEGORY_WEIGHTS["Windows"] + (score or 0) + (150 if active_id == window_id else 0),
                action={"type": "window", "window_id": window_id},
                terms=[display_title, window_class, window_id, "wayland", "window"],
                active=active_id == window_id,
            )
        )

    if not results:
        return [
            Result(
                id="windows:no-visible-results",
                title="No matching windows",
                subtitle="The remaining KWin windows were filtered out or did not match your query.",
                category="Windows",
                score=CATEGORY_WEIGHTS["Windows"] + 2000,
                action={"type": "noop"},
                nonselectable=True,
                permanent=True,
            )
        ], None

    results.sort(key=lambda result: (-result.score, result.title.lower()))
    return results[:40], None


def search(context: SearchContext, query: str) -> list[Result]:
    if context.session_type == "wayland":
        results, _ = _search_wayland_windows(query)
        return results

    if not shutil.which("wmctrl"):
        return [
            Result(
                id="windows:wmctrl-missing",
                title="wmctrl is missing",
                subtitle="Install wmctrl for X11 window switching support.",
                category="Windows",
                score=50,
                action={"type": "noop"},
                nonselectable=True,
                permanent=True,
            )
        ]

    completed = subprocess.run(["wmctrl", "-lx"], capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        return []

    results: list[Result] = []
    for line in completed.stdout.splitlines():
        parts = line.split(None, 4)
        if len(parts) < 5:
            continue
        window_id, _, _, wm_class, title = parts
        score = match_score(query, [title, wm_class])
        if query and score is None:
            continue

        results.append(
            Result(
                id=f"window:{window_id}",
                title=title,
                subtitle=wm_class,
                category="Windows",
                score=CATEGORY_WEIGHTS["Windows"] + (score or 0),
                action={"type": "window", "window_id": window_id},
                terms=[title, wm_class],
            )
        )

    results.sort(key=lambda result: (-result.score, result.title.lower()))
    return results[:50]
