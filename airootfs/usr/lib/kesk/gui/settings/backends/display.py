from __future__ import annotations

from typing import Any

from .common import intentional_handoff, missing, result_payload


def is_available(backend) -> bool:
    return bool(backend.tools.get("kscreen-doctor")) or bool(backend.tools.get("qdbus6"))


def _status(backend):
    if backend.tools.get("kscreen-doctor"):
        details = ["Display layout and scaling stay in KDE's advanced display module to avoid unsafe black-screen situations."]
        if not backend.tools.get("brightnessctl"):
            details.append("Brightness control is unavailable because brightnessctl is not installed.")
        return intentional_handoff("Display state is readable through KScreen, but live changes stay in KDE.", details=details, advanced_module="kcm_kscreen")
    if backend.tools.get("qdbus6"):
        return intentional_handoff(
            "Display state is only partially readable without kscreen-doctor, and live changes stay in KDE.",
            details=["Display layout and scaling stay in KDE's advanced display module to avoid unsafe black-screen situations."],
            advanced_module="kcm_kscreen",
        )
    return missing("No direct display backend is available.", missing_tools=["kscreen-doctor", "qdbus6"], advanced_module="kcm_kscreen")


def _brightness(backend) -> int | None:
    tool = backend.tools.get("brightnessctl")
    if not tool:
        return None
    result = backend._run([tool, "-m"], capture=True, timeout=10)
    if result is None or result.returncode != 0:
        return None
    parts = result.stdout.strip().split(",")
    if len(parts) >= 4 and parts[3].endswith("%"):
        try:
            return int(parts[3].removesuffix("%"))
        except ValueError:
            return None
    return None


def read_current(backend) -> dict[str, Any]:
    data = backend.parse_display_info()
    brightness = _brightness(backend)
    return {
        "status": _status(backend),
        "monitor_list": data.get("monitor_list", []),
        "output_summary": data.get("output_summary", "Display detection unavailable"),
        "session": data.get("session", "unknown"),
        "plasma_version": data.get("plasma_version", "unavailable"),
        "resolution": str(backend.custom_value("display_resolution", "Automatic")),
        "refresh_rate": int(backend.custom_value("display_refresh_rate", 60)),
        "scale_percent": int(backend.custom_value("display_scale_percent", 100)),
        "orientation": str(backend.custom_value("display_orientation", "Normal")),
        "brightness": brightness if brightness is not None else int(backend.custom_value("display_brightness", 100)),
        "night_color": backend.as_bool(backend.custom_value("display_night_color"), False),
        "supports_live_layout": False,
        "supports_brightness": brightness is not None,
        "apply_supported": False,
        "handoff_reason": "Display layout and scaling are opened in KDE Display Settings to avoid unsafe display changes or black-screen risk.",
    }


def apply_changes(backend, values: dict[str, Any]) -> dict[str, Any]:
    return result_payload(
        True,
        "Display settings are intentionally handed off to KDE Display Settings.",
        warnings=["Use KDE Display Settings for live layout, scaling, refresh-rate, orientation, and brightness changes on this system."],
        requires=["Open KDE Display Settings to make safe display changes."],
    )


def open_advanced_settings(backend):
    return backend.open_kcm("kcm_kscreen")
