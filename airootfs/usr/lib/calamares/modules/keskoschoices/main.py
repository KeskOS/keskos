#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import json
from pathlib import Path

import libcalamares

from libcalamares.utils import gettext_languages, gettext_path

import gettext

_translation = gettext.translation(
    "calamares-python",
    localedir=gettext_path(),
    languages=gettext_languages(),
    fallback=True,
)
_ = _translation.gettext


STATUS = _("Preparing KeskOS deployment defaults.")


def pretty_name():
    return _("Resolve KeskOS deployment defaults.")


def pretty_status_message():
    return STATUS


def debug(message: str) -> None:
    libcalamares.utils.debug(f"[keskoschoices] {message}")


def warn(message: str) -> None:
    libcalamares.utils.warning(f"[keskoschoices] {message}")


def unique(items: list[str]) -> list[str]:
    seen = set()
    ordered = []
    for item in items:
        if not item or item in seen:
            continue
        seen.add(item)
        ordered.append(item)
    return ordered


def load_manifest(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def split_selection(raw_value) -> list[str]:
    if raw_value is None:
        return []
    return unique([item.strip() for item in str(raw_value).split(",") if item.strip()])


def default_features(manifest: dict) -> dict:
    return {key: bool(value.get("default", False)) for key, value in manifest.get("features", {}).items()}


def bool_value(raw_value, default: bool = False) -> bool:
    if raw_value is None:
        return default
    if isinstance(raw_value, bool):
        return raw_value

    normalized = str(raw_value).strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off", ""}:
        return False
    return default


def normalize_list(raw_value) -> list[str]:
    if raw_value is None:
        return []
    if isinstance(raw_value, list):
        return unique([str(item).strip() for item in raw_value if str(item).strip()])
    return split_selection(raw_value)


def load_install_defaults(config: dict, manifest: dict) -> dict:
    browser = str(config.get("defaultBrowser", "librewolf")).strip() or "librewolf"
    apply_browser_theme = bool_value(config.get("applyBrowserTheme"), default=False)
    remove_other_browsers_after_install = bool_value(config.get("removeOtherBrowsersAfterInstall"), default=False)
    bundles = [item for item in normalize_list(config.get("defaultBundles", [])) if item in manifest.get("bundles", {})]
    desktop_profile = str(config.get("defaultDesktopProfile", "kesk_default")).strip() or "kesk_default"
    addons = [item for item in normalize_list(config.get("defaultAddons", [])) if item in manifest.get("features", {})]
    extra_packages = normalize_list(config.get("extraPackages", []))
    force_enabled_features = [
        item for item in normalize_list(config.get("forceEnabledFeatures", [])) if item in manifest.get("features", {})
    ]
    force_disabled_features = [
        item for item in normalize_list(config.get("forceDisabledFeatures", [])) if item in manifest.get("features", {})
    ]

    features = default_features(manifest)
    if desktop_profile == "plasma_base":
        for feature_key in (
            "quickshell_topbar",
            "plasma_theme",
            "window_borders",
            "sddm_theme",
            "plymouth",
        ):
            if feature_key in features:
                features[feature_key] = False
        features["kde_bottom_taskbar"] = True
    else:
        for feature_key in (
            "quickshell_topbar",
            "kde_bottom_taskbar",
            "plasma_theme",
            "window_borders",
            "sddm_theme",
            "plymouth",
        ):
            if feature_key in features:
                features[feature_key] = True

    features["browser_startpage"] = apply_browser_theme

    for feature_key in addons:
        if feature_key in features:
            features[feature_key] = True

    for feature_key in force_disabled_features:
        if feature_key in features:
            features[feature_key] = False

    for feature_key in force_enabled_features:
        if feature_key in features:
            features[feature_key] = True

    return {
        "browser": browser,
        "apply_browser_theme": apply_browser_theme,
        "remove_other_browsers_after_install": remove_other_browsers_after_install,
        "bundles": bundles,
        "desktop_profile": desktop_profile,
        "addons": addons,
        "extra_packages": extra_packages,
        "features": features,
    }


def package_operation(source: str, key: str, packages: list[str]) -> dict | None:
    package_list = unique(packages)
    if not package_list:
        return None
    return {"source": source, key: package_list}


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def write_json(path: Path, payload: dict) -> None:
    ensure_parent(path)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, lines: list[str]) -> None:
    ensure_parent(path)
    path.write_text("\n".join(lines).strip() + ("\n" if lines else ""), encoding="utf-8")


def resolve_browser(selections: dict, manifest: dict) -> tuple[dict, list[str]]:
    # Browser installation/default selection moved to Kesk Welcome first boot.
    # Keep a stable payload shape for older report readers, but do not resolve
    # or apply a browser from Calamares anymore.
    return (
        {
            "selected_key": "welcome",
            "resolved_key": "welcome",
            "package": "",
            "desktop": "",
            "family": "deferred",
            "remove_other_browsers_after_install": False,
        },
        [],
    )


def build_choice_payload(selections: dict, manifest: dict) -> tuple[dict, list[dict], list[str]]:
    warnings: list[str] = []
    browser, browser_warnings = resolve_browser(selections, manifest)
    warnings.extend(browser_warnings)

    bundle_packages: list[str] = []
    for bundle_key in selections["bundles"]:
        bundle_packages.extend(manifest["bundles"][bundle_key]["packages"])

    extra_packages = unique(selections.get("extra_packages", []))

    feature_packages: list[str] = []
    for feature_key, enabled in selections["features"].items():
        if enabled:
            feature_packages.extend(manifest["features"].get(feature_key, {}).get("packages", []))

    operations: list[dict] = []

    bundle_op = package_operation("keskos-bundles", "try_install", bundle_packages)
    if bundle_op:
        operations.append(bundle_op)

    extra_op = package_operation("keskos-extras", "try_install", extra_packages)
    if extra_op:
        operations.append(extra_op)

    feature_op = package_operation("keskos-features", "try_install", feature_packages)
    if feature_op:
        operations.append(feature_op)

    final_packages: list[str] = []
    for op in operations:
        final_packages.extend(op.get("try_install", []))
        final_packages.extend(op.get("install", []))

    choices = {
        "browser": browser,
        "apply_browser_theme": bool(selections["apply_browser_theme"]),
        "bundles": selections["bundles"],
        "desktop_profile": selections["desktop_profile"],
        "addons": selections["addons"],
        "extra_packages": extra_packages,
        "features": selections["features"],
        "warnings": warnings,
        "final_packages": unique(final_packages),
    }

    return choices, operations, warnings


def merge_package_operations(new_ops: list[dict]) -> list[dict]:
    existing = libcalamares.globalstorage.value("packageOperations") or []
    merged = []
    seen_sources = {op["source"] for op in new_ops}

    for op in existing:
        if isinstance(op, dict) and op.get("source") not in seen_sources:
            merged.append(op)

    merged.extend(new_ops)
    return merged


def run():
    global STATUS

    config = libcalamares.job.configuration
    manifest_path = str(config.get("manifestPath", "/usr/share/keskos/installer/package-manifest.json"))
    live_choices_path = Path(str(config.get("choicesOutput", "/tmp/keskos-install-choices.json")))
    live_packages_path = Path(str(config.get("packageListOutput", "/tmp/keskos-final-packages.txt")))
    target_choices_relative = str(config.get("targetChoicesPath", "/var/lib/keskos/install-choices.json"))
    target_packages_relative = str(config.get("targetPackageListPath", "/var/lib/keskos/final-packages.txt"))

    debug(f"Loading manifest from {manifest_path}")
    manifest = load_manifest(manifest_path)
    selections = load_install_defaults(config, manifest)
    choices, operations, warnings = build_choice_payload(selections, manifest)

    merged_operations = merge_package_operations(operations)
    libcalamares.globalstorage.insert("packageOperations", merged_operations)

    root_mount_point = libcalamares.globalstorage.value("rootMountPoint") or "/"
    target_root = Path(str(root_mount_point))
    target_choices_path = target_root / target_choices_relative.lstrip("/")
    target_packages_path = target_root / target_packages_relative.lstrip("/")

    write_json(live_choices_path, choices)
    write_text(live_packages_path, choices["final_packages"])
    write_json(target_choices_path, choices)
    write_text(target_packages_path, choices["final_packages"])

    libcalamares.globalstorage.insert("keskosBrowserDesktop", choices["browser"]["desktop"])
    libcalamares.globalstorage.insert("keskosBrowserKey", choices["browser"]["resolved_key"])

    for warning_message in warnings:
        warn(warning_message)

    STATUS = _("Resolved KeskOS deployment defaults.")
    debug(
        f"Browser setup deferred to Welcome "
        f"profile={choices['desktop_profile']} apply_browser_theme={choices['apply_browser_theme']}"
    )
    return None
