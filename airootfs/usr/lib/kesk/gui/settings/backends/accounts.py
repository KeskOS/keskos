from __future__ import annotations

from pathlib import Path
from typing import Any

from .common import kde_handoff, result_payload


def is_available(backend) -> bool:
    return bool(backend.tools.get("kcmshell6") or backend.tools.get("systemsettings"))


def read_current(backend) -> dict[str, Any]:
    config_root = backend.paths.home / ".config"
    account_files = sorted(
        {
            path.stem
            for path in (
                list(config_root.glob("kaccounts*"))
                + list((config_root / "kaccounts").glob("*"))
                + list((config_root / "libaccounts-glib").glob("*"))
            )
            if path.exists()
        }
    )
    return {
        "status": kde_handoff(
            "KDE Online Accounts is exposed through the native KDE module.",
            details=["Account discovery is lightweight; add/remove flows stay in KDE's dedicated module."],
            advanced_module="kcm_kaccounts",
        ),
        "connected_accounts": account_files,
        "sync_calendar": bool(backend.custom_value("accounts_sync_calendar", True)),
        "sync_files": bool(backend.custom_value("accounts_sync_files", True)),
        "sync_contacts": bool(backend.custom_value("accounts_sync_contacts", True)),
    }


def apply_changes(backend, values: dict[str, Any]) -> dict[str, Any]:
    backend.set_custom_values(
        {
            "accounts_sync_calendar": bool(values.get("sync_calendar", True)),
            "accounts_sync_files": bool(values.get("sync_files", True)),
            "accounts_sync_contacts": bool(values.get("sync_contacts", True)),
        }
    )
    return result_payload(
        True,
        "Online-account preferences saved.",
        details=["KeskOS sync preferences were stored."],
        requires=["Use the KDE Online Accounts module to add or remove actual account providers."],
    )


def open_advanced_settings(backend):
    return backend.open_kcm("kcm_kaccounts")
