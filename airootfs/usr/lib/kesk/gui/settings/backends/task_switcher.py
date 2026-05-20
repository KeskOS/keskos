from __future__ import annotations

from typing import Any

from .common import kde_handoff, result_payload


def is_available(_backend) -> bool:
    return True


def read_current(backend) -> dict[str, Any]:
    layout = backend.kread(backend.kwinrc, ("TabBox",), "LayoutName", "org.kde.breeze.desktop")
    return {
        "status": kde_handoff(
            "Task-switcher status is readable, but detailed Alt+Tab writes still use KDE's advanced module.",
            details=["The exact KWin tab-box keys vary between Plasma releases, so direct writes stay conservative."],
            advanced_module="kwintabbox",
        ),
        "style": layout,
        "include_minimized": backend.as_bool(backend.kread(backend.kwinrc, ("TabBox",), "ApplicationsIncludeMinimized", "true"), True),
        "all_desktops": backend.as_bool(backend.kread(backend.kwinrc, ("TabBox",), "AllDesktopsMode", "false"), False),
    }


def apply_changes(_backend, _values: dict[str, Any]) -> dict[str, Any]:
    return result_payload(
        True,
        "Task-switcher changes were not applied directly.",
        warnings=["Open advanced KDE task-switcher settings for reliable Alt+Tab changes on this Plasma version."],
        requires=["Use the advanced KDE task-switcher module for live changes."],
    )


def open_advanced_settings(backend):
    return backend.open_kcm("kwintabbox")
