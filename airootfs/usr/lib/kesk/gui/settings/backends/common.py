from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

SUPPORT_LEVELS = {
    "connected": "Native",
    "limited": "Limited",
    "kde_handoff": "KDE Handoff",
    "intentional_handoff": "KDE Handoff",
    "requires_admin": "Requires Admin",
    "missing": "Unsupported",
    "unsupported": "Unsupported",
    "planned": "Planned",
}

SUPPORT_UI_KINDS = {
    "Native": "ok",
    "Limited": "work",
    "KDE Handoff": "work",
    "Requires Admin": "warn",
    "Unsupported": "skip",
    "Planned": "skip",
}


@dataclass(frozen=True)
class BackendStatus:
    code: str
    summary: str
    details: list[str] = field(default_factory=list)
    missing_tools: list[str] = field(default_factory=list)
    admin_required: bool = False
    advanced_module: str | None = None

    @property
    def ui_kind(self) -> str:
        return {
            "connected": "ok",
            "limited": "work",
            "kde_handoff": "work",
            "intentional_handoff": "work",
            "missing": "skip",
            "requires_admin": "warn",
        }.get(self.code, "skip")

    @property
    def display_label(self) -> str:
        return {
            "connected": "Connected",
            "limited": "Limited",
            "kde_handoff": "KDE Handoff",
            "intentional_handoff": "KDE Handoff",
            "missing": "Missing tools",
            "requires_admin": "Requires Admin",
        }.get(self.code, "Missing tools")

    @property
    def support_level(self) -> str:
        return support_level_for_status(self)

    @property
    def support_ui_kind(self) -> str:
        return support_ui_kind(self.support_level)


def connected(summary: str, *, details: list[str] | None = None, advanced_module: str | None = None) -> BackendStatus:
    return BackendStatus("connected", summary, details or [], [], False, advanced_module)


def limited(
    summary: str,
    *,
    details: list[str] | None = None,
    missing_tools: list[str] | None = None,
    admin_required: bool = False,
    advanced_module: str | None = None,
) -> BackendStatus:
    return BackendStatus("limited", summary, details or [], missing_tools or [], admin_required, advanced_module)


def kde_handoff(
    summary: str,
    *,
    details: list[str] | None = None,
    missing_tools: list[str] | None = None,
    advanced_module: str | None = None,
) -> BackendStatus:
    return BackendStatus("kde_handoff", summary, details or [], missing_tools or [], False, advanced_module)


def intentional_handoff(
    summary: str,
    *,
    details: list[str] | None = None,
    advanced_module: str | None = None,
) -> BackendStatus:
    return BackendStatus("intentional_handoff", summary, details or [], [], False, advanced_module)


def missing(summary: str, *, missing_tools: list[str] | None = None, advanced_module: str | None = None) -> BackendStatus:
    return BackendStatus("missing", summary, [], missing_tools or [], False, advanced_module)


def requires_admin(summary: str, *, details: list[str] | None = None, advanced_module: str | None = None) -> BackendStatus:
    return BackendStatus("requires_admin", summary, details or [], [], True, advanced_module)


def result_payload(
    success: bool,
    summary: str,
    *,
    details: list[str] | None = None,
    warnings: list[str] | None = None,
    requires: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "success": success,
        "summary": summary,
        "details": details or [],
        "warnings": warnings or [],
        "requires": requires or [],
    }


def support_level_for_status(status_or_code: BackendStatus | str) -> str:
    code = status_or_code.code if isinstance(status_or_code, BackendStatus) else str(status_or_code)
    return SUPPORT_LEVELS.get(code, "Unsupported")


def support_ui_kind(level: str) -> str:
    return SUPPORT_UI_KINDS.get(level, "skip")
