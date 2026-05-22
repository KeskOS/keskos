#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import os
import re
import shutil
import socket
import subprocess
import urllib.error
import urllib.request

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

API_ENDPOINT = "https://api.keskos.org/install-report"
TEMP_REPORT_PATH = Path("/tmp/keskos-install-report.json")
DEFAULT_SOURCE_PATH = Path("/var/lib/keskos/install-report-source.json")
DEFAULT_SESSION_PATH = Path("/var/lib/keskos/install-session.json")
LIVE_SESSION_PATH = Path("/tmp/keskos-install-session.json")
DEFAULT_CHOICES_PATH = Path("/var/lib/keskos/install-choices.json")
LIVE_CHOICES_PATH = Path("/tmp/keskos-install-choices.json")
DEFAULT_PACKAGE_LIST_PATH = Path("/var/lib/keskos/final-packages.txt")
LIVE_PACKAGE_LIST_PATH = Path("/tmp/keskos-final-packages.txt")
INSTALL_REPORT_SENT_MARKER = Path("/etc/keskos/install-report-sent.json")
INSTALL_REPORT_SENT_STATE = Path("/var/lib/keskos/install-report-sent.json")
MAX_BODY_BYTES = 64 * 1024

ALLOWED_FIELDS = {
    "install_result",
    "install_duration_seconds",
    "keskos_version",
    "iso_build_id",
    "installer_version",
    "kernel_version",
    "calamares_version",
    "install_mode",
    "boot_mode",
    "filesystem_selected",
    "desktop_profile_selected",
    "browser_selected",
    "top_bar_widgets_selected",
    "optional_apps_selected",
    "failed_stage",
    "sanitized_error_summary",
    "timestamp_utc",
    "timezone",
    "locale_language",
    "cpu_model",
    "ram_amount",
    "disk_size",
    "gpu_vendor_model",
    "network_online_during_install",
    "package_install_success_count",
    "package_install_fail_count",
    "extra_diagnostics",
}


def config_root() -> Path:
    return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))


def state_root() -> Path:
    return Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local" / "state"))


def log_path() -> Path:
    override = os.environ.get("KESK_INSTALL_REPORT_LOG_FILE", "").strip()
    if override:
        return Path(override)
    return state_root() / "kesk" / "logs" / "install-report.log"


def write_log(message: str) -> None:
    path = log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with path.open("a", encoding="utf-8") as handle:
        handle.write(f"[{timestamp}] {message}\n")


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def json_response(ok: bool, message: str, **extra: Any) -> int:
    payload: dict[str, Any] = {"ok": ok, "message": message}
    payload.update(extra)
    print(json.dumps(payload, sort_keys=True))
    return 0


def command_exists(name: str) -> bool:
    return shutil.which(name) is not None


def run_capture(argv: list[str], timeout: int = 10) -> subprocess.CompletedProcess[str] | None:
    try:
        return subprocess.run(argv, capture_output=True, text=True, timeout=timeout, check=False)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None


def json_path(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def read_json(paths: list[Path]) -> dict[str, Any]:
    for path in paths:
        payload = json_path(path)
        if payload:
            return payload
    return {}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_lines(path: Path) -> list[str]:
    try:
        return path.read_text(encoding="utf-8", errors="replace").splitlines()
    except FileNotFoundError:
        return []


def write_marker(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    write_json(path, payload)


def read_key_value_file(path: Path) -> dict[str, str]:
    data: dict[str, str] = {}
    try:
        for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            data[key.strip()] = value.strip().strip('"').strip("'")
    except FileNotFoundError:
        return {}
    return data


def rooted_path(target_root: Path, relative: str) -> Path:
    return target_root.joinpath(relative.lstrip("/"))


def first_existing_text(paths: list[Path], key: str) -> str:
    for path in paths:
        value = read_key_value_file(path).get(key, "").strip()
        if value:
            return value
    return ""


def release_metadata(target_root: Path) -> tuple[list[dict[str, str]], str]:
    version_path = rooted_path(target_root, "/usr/share/kesk/version")
    paths = [
        rooted_path(target_root, "/etc/os-release"),
        rooted_path(target_root, "/etc/kesk-release"),
        version_path,
    ]
    raw_version_lines = read_lines(version_path)
    return [read_key_value_file(path) for path in paths], raw_version_lines[0].strip() if raw_version_lines else ""


def first_release_value(release_maps: list[dict[str, str]], keys: list[str]) -> str:
    for release_map in release_maps:
        for key in keys:
            value = release_map.get(key, "").strip()
            if value:
                return value
    return ""


def detect_keskos_version(target_root: Path) -> str | None:
    release_maps, raw_version_line = release_metadata(target_root)
    version_name = first_release_value(release_maps, ["PRETTY_NAME", "NAME"])
    version_id = first_release_value(release_maps, ["VERSION_ID", "VERSION", "LAYER", "BUILD_DATE", "BUILD_ID"])

    if version_name and version_name.lower() not in {"keskos", "keskos live"}:
        return sanitize_string(version_name)

    if version_id:
        base_name = "KeskOS Live" if version_name.lower() == "keskos live" else "KeskOS"
        return sanitize_string(f"{base_name} {version_id}")

    if version_name:
        return sanitize_string(version_name)
    if raw_version_line:
        return sanitize_string(raw_version_line)
    return None


def detect_iso_build_id(session: dict[str, Any], target_root: Path) -> str | None:
    value = str(session.get("iso_build_id") or "").strip()
    if not value:
        release_maps, _ = release_metadata(target_root)
        value = first_release_value(release_maps, ["BUILD_ID", "BUILD_DATE", "IMAGE_BUILD_DATE", "VERSION_ID", "VERSION"])
    return sanitize_string(value) if value else None


def detect_kernel_version() -> str | None:
    output = run_capture(["uname", "-r"], timeout=5)
    if output and output.stdout.strip():
        return sanitize_string(output.stdout.strip())
    return None


def detect_calamares_version() -> str | None:
    output = run_capture(["calamares", "--version"], timeout=10)
    if output and output.stdout.strip():
        return sanitize_string(output.stdout.strip())
    if output and output.stderr.strip():
        return sanitize_string(output.stderr.strip())
    output = run_capture(["pacman", "-Q", "calamares"], timeout=10)
    if output and output.stdout.strip():
        parts = output.stdout.strip().split(maxsplit=1)
        if len(parts) == 2:
            return sanitize_string(parts[1])
    return None


def detect_install_mode() -> str:
    return "normal"


def detect_boot_mode(session: dict[str, Any]) -> str | None:
    value = str(session.get("boot_mode") or "").strip().lower()
    if value in {"uefi", "bios"}:
        return value
    if Path("/sys/firmware/efi").exists():
        return "uefi"
    if Path("/sys").exists():
        return "bios"
    return None


def detect_filesystem(target_root: Path) -> str | None:
    try:
        for raw_line in rooted_path(target_root, "/etc/fstab").read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) >= 3 and parts[1] == "/":
                return sanitize_string(parts[2])
    except FileNotFoundError:
        pass
    return None


def detect_timezone(target_root: Path) -> str | None:
    localtime = rooted_path(target_root, "/etc/localtime")
    try:
        target = localtime.resolve(strict=True)
        marker = "/usr/share/zoneinfo/"
        value = str(target)
        if marker in value:
            return sanitize_string(value.split(marker, 1)[1])
    except FileNotFoundError:
        pass

    timedatectl = run_capture(["timedatectl", "show", "-p", "Timezone", "--value"], timeout=5)
    if timedatectl and timedatectl.stdout.strip():
        return sanitize_string(timedatectl.stdout.strip())
    return None


def detect_locale_language(target_root: Path) -> str | None:
    locale_conf = read_key_value_file(rooted_path(target_root, "/etc/locale.conf"))
    lang = locale_conf.get("LANG", "").strip() or os.environ.get("LANG", "").strip()
    if not lang:
        return None
    return sanitize_string(lang.split(".", 1)[0])


def detect_cpu_model() -> str | None:
    output = run_capture(["lscpu"], timeout=10)
    if output and output.stdout:
        for line in output.stdout.splitlines():
            if line.lower().startswith("model name:"):
                return sanitize_string(line.split(":", 1)[1].strip())
    return None


def detect_ram_amount() -> int | None:
    try:
        for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
            if line.startswith("MemTotal:"):
                kib = int(line.split()[1])
                gib = int(round((kib * 1024) / (1024 ** 3)))
                return max(gib, 1)
    except (FileNotFoundError, ValueError):
        pass
    return None


def detect_disk_size() -> int | None:
    output = run_capture(["lsblk", "-bdn", "-o", "SIZE,TYPE"], timeout=10)
    if output and output.stdout:
        largest = 0
        for line in output.stdout.splitlines():
            parts = line.split()
            if len(parts) != 2 or parts[1] != "disk":
                continue
            try:
                largest = max(largest, int(parts[0]))
            except ValueError:
                continue
        if largest > 0:
            return max(int(round(largest / (1024 ** 3))), 1)
    return None


def detect_gpu_vendor_model() -> str | None:
    output = run_capture(["lspci"], timeout=10)
    if output and output.stdout:
        for line in output.stdout.splitlines():
            if (
                "VGA compatible controller" in line
                or "3D controller" in line
                or "Display controller" in line
            ):
                value = line.split(": ", 1)[1].strip() if ": " in line else line.strip()
                return sanitize_string(value)
    return None


def ping_online() -> bool | None:
    output = run_capture(["ping", "-c", "1", "-W", "2", "8.8.8.8"], timeout=5)
    if output is None:
        return None
    return output.returncode == 0


def detect_network_online_during_install(session: dict[str, Any]) -> bool | None:
    value = session.get("network_online_during_install")
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered == "yes":
            return True
        if lowered == "no":
            return False
    if command_exists("ping"):
        return ping_online()
    return None


def load_choices(target_root: Path, prefer_live: bool = False) -> dict[str, Any]:
    paths = [rooted_path(target_root, "/var/lib/keskos/install-choices.json"), DEFAULT_CHOICES_PATH]
    if prefer_live:
        paths.insert(0, LIVE_CHOICES_PATH)
    return read_json(paths)


def selected_browser_from_choices(choices: dict[str, Any]) -> str | None:
    browser = choices.get("browser", {})
    if isinstance(browser, dict):
        value = str(browser.get("resolved_key") or browser.get("selected_key") or "").strip()
        return sanitize_string(value) if value else None
    return None


def selected_desktop_profile(choices: dict[str, Any]) -> str | None:
    value = str(choices.get("desktop_profile") or "").strip()
    return sanitize_string(value) if value else None


def selected_optional_apps(choices: dict[str, Any], prefer_live: bool, target_root: Path) -> list[str]:
    packages: list[str] = []
    for path in (
        [LIVE_PACKAGE_LIST_PATH] if prefer_live else []
    ) + [rooted_path(target_root, "/var/lib/keskos/final-packages.txt"), DEFAULT_PACKAGE_LIST_PATH]:
        if not path.exists():
            continue
        for line in read_lines(path):
            value = sanitize_string(line.strip())
            if value and value not in packages:
                packages.append(value)
        if packages:
            break

    if not packages:
        for key in ("final_packages", "extra_packages"):
            values = choices.get(key)
            if isinstance(values, list):
                for value in values:
                    item = sanitize_string(str(value).strip())
                    if item and item not in packages:
                        packages.append(item)

    return packages[:128]


def count_package_results(target_root: Path) -> tuple[int | None, int | None]:
    package_lines = read_lines(rooted_path(target_root, "/var/lib/keskos/final-packages.txt"))
    packages = []
    seen = set()
    for raw_line in package_lines:
        package = raw_line.strip()
        if not package or package in seen:
            continue
        seen.add(package)
        packages.append(package)

    if not packages:
        return None, None

    success = 0
    failed = 0
    pacman = run_capture(["which", "pacman"], timeout=5)
    if pacman is None:
        return None, None

    for package in packages:
        output = run_capture(["pacman", "--root", str(target_root), "-Q", package], timeout=5)
        if output and output.returncode == 0:
            success += 1
        else:
            failed += 1
    return success, failed


def usernames_to_redact() -> set[str]:
    values = {
        os.environ.get("USER", "").strip(),
        os.environ.get("LOGNAME", "").strip(),
        Path.home().name.strip(),
    }
    return {value for value in values if value and value not in {"root", "/"}}


def hostnames_to_redact() -> set[str]:
    values = {socket.gethostname().strip()}
    fqdn = socket.getfqdn().strip()
    if fqdn:
        values.add(fqdn)
    return {value for value in values if value}


def redact_standalone_token(text: str, token: str, replacement: str) -> str:
    escaped = re.escape(token)
    patterns = [
        re.compile(rf"(?<![A-Za-z0-9_.-]){escaped}(?![A-Za-z0-9_.-])"),
        re.compile(rf"(?<=/){escaped}(?=/|$)"),
        re.compile(rf"(?<=@){escaped}(?![A-Za-z0-9_.-])"),
    ]
    result = text
    for pattern in patterns:
        result = pattern.sub(replacement, result)
    return result


def sanitize_string(value: str) -> str:
    redacted = value
    for username in usernames_to_redact():
        redacted = redact_standalone_token(redacted, username, "<user>")
    for hostname in hostnames_to_redact():
        redacted = redact_standalone_token(redacted, hostname, "<host>")

    patterns = [
        (re.compile(r"/home/[^/\s]+"), "/home/<user>"),
        (re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"), "<ip>"),
        (re.compile(r"\b(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}\b"), "<mac>"),
        (re.compile(r"\b[a-f0-9]{32}\b", re.IGNORECASE), "<id>"),
        (
            re.compile(
                r"(?i)\b(?:password|passwd|token|secret|api[_-]?key|bearer|authorization)\b\s*[:=]\s*\S+"
            ),
            "<redacted-secret>",
        ),
    ]
    for pattern, replacement in patterns:
        redacted = pattern.sub(replacement, redacted)

    redacted = re.sub(r"\s+", " ", redacted).strip()
    if len(redacted) > 240:
        redacted = redacted[:237].rstrip() + "..."
    return redacted


def sanitize_payload(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): sanitize_payload(item) for key, item in value.items()}
    if isinstance(value, list):
        return [sanitize_payload(item) for item in value]
    if isinstance(value, str):
        return sanitize_string(value)
    return value


def prune_unknowns(payload: dict[str, Any]) -> dict[str, Any]:
    cleaned: dict[str, Any] = {}
    for key, value in payload.items():
        if key not in ALLOWED_FIELDS:
            continue
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        if isinstance(value, list) and not value:
            continue
        cleaned[key] = value
    return cleaned


def enforce_size_limit(payload: dict[str, Any]) -> dict[str, Any]:
    candidate = dict(payload)
    while len(json.dumps(candidate, sort_keys=True).encode("utf-8")) > MAX_BODY_BYTES:
        if "extra_diagnostics" in candidate:
            candidate.pop("extra_diagnostics", None)
            continue
        if "optional_apps_selected" in candidate and len(candidate["optional_apps_selected"]) > 16:
            candidate["optional_apps_selected"] = candidate["optional_apps_selected"][:16]
            continue
        if "sanitized_error_summary" in candidate and len(candidate["sanitized_error_summary"]) > 96:
            candidate["sanitized_error_summary"] = candidate["sanitized_error_summary"][:93].rstrip() + "..."
            continue
        break
    return candidate


def post_payload(payload: dict[str, Any]) -> tuple[bool, str]:
    data = json.dumps(payload, sort_keys=True).encode("utf-8")
    request = urllib.request.Request(
        API_ENDPOINT,
        data=data,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "keskos-install-report/1",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            if response.status == 202 or 200 <= response.status < 300:
                return True, "Install report sent."
            return False, f"Install report server returned HTTP {response.status}."
    except urllib.error.HTTPError as error:
        if error.code == 202:
            return True, "Install report sent."
        return False, f"Install report server returned HTTP {error.code}."
    except urllib.error.URLError:
        return False, "Install report server is unreachable."
    except TimeoutError:
        return False, "Install report request timed out."


def build_success_source_payload(target_root: Path) -> dict[str, Any]:
    session = read_json([rooted_path(target_root, "/var/lib/keskos/install-session.json"), DEFAULT_SESSION_PATH])
    choices = load_choices(target_root, prefer_live=False)
    started_at = int(session.get("started_at_epoch") or 0)
    duration = max(0, int(datetime.now(timezone.utc).timestamp()) - started_at) if started_at > 0 else None
    success_count, fail_count = count_package_results(target_root)

    payload: dict[str, Any] = {
        "install_result": "success",
        "timestamp_utc": utc_now(),
        "install_duration_seconds": duration,
        "keskos_version": detect_keskos_version(target_root),
        "iso_build_id": detect_iso_build_id(session, target_root),
        "kernel_version": detect_kernel_version(),
        "calamares_version": detect_calamares_version(),
        "install_mode": detect_install_mode(),
        "boot_mode": detect_boot_mode(session),
        "filesystem_selected": detect_filesystem(target_root),
        "desktop_profile_selected": selected_desktop_profile(choices),
        "browser_selected": selected_browser_from_choices(choices),
        "optional_apps_selected": selected_optional_apps(choices, False, target_root),
        "timezone": detect_timezone(target_root),
        "locale_language": detect_locale_language(target_root),
        "cpu_model": detect_cpu_model(),
        "ram_amount": detect_ram_amount(),
        "disk_size": detect_disk_size(),
        "gpu_vendor_model": detect_gpu_vendor_model(),
        "network_online_during_install": detect_network_online_during_install(session),
        "package_install_success_count": success_count,
        "package_install_fail_count": fail_count,
    }
    return enforce_size_limit(prune_unknowns(sanitize_payload(payload)))


def write_success_source(target_root: Path) -> dict[str, Any]:
    payload = build_success_source_payload(target_root)
    destination = rooted_path(target_root, "/var/lib/keskos/install-report-source.json")
    write_json(destination, payload)
    return payload


def summarize_failure_log(log_file: Path | None) -> tuple[str | None, str | None, int | None, int | None]:
    if log_file is None or not log_file.exists():
        return None, None, None, None

    lines = [line.strip() for line in read_lines(log_file) if line.strip()]
    joined = "\n".join(lines[-400:])
    lowered = joined.lower()

    stage_patterns = {
        "packages": [r"\bpackages?\b", r"\bpackagechooser\b"],
        "bootloader": [r"\bbootloader\b", r"\bgrub\b", r"\bsystemd-boot\b"],
        "partition": [r"\bpartition\b", r"\bmount\b", r"\bunpackfs\b"],
        "users": [r"\busers?\b"],
        "network": [r"\bnetwork\b"],
        "locale": [r"\blocale\b", r"\bkeyboard\b"],
        "postinstall": [r"\bpostinstall\b", r"\bkeskos-postinstall\b"],
        "desktop_profile": [r"desktop profile", r"\bkeskoschoices\b", r"\bbrowser\b", r"\bbundles\b"],
        "services": [r"\bservices-systemd\b", r"\bsystemd\b"],
        "initcpio": [r"\binitcpio\b", r"\bmkinitcpio\b"],
    }
    failed_stage = None
    for stage, patterns in stage_patterns.items():
        if any(re.search(pattern, lowered) for pattern in patterns):
            failed_stage = stage
            break

    summary = None
    for line in reversed(lines):
        cleaned = sanitize_string(line)
        if not cleaned:
            continue
        if cleaned.startswith("==="):
            continue
        if cleaned.startswith("---"):
            continue
        lowered_line = cleaned.lower()
        if "password" in lowered_line or "token" in lowered_line:
            continue
        if any(keyword in lowered_line for keyword in ("failed", "error", "fatal", "aborted", "cancel")):
            summary = cleaned
            break
    if summary is None:
        for line in reversed(lines):
            cleaned = sanitize_string(line)
            if cleaned and not cleaned.startswith(("===", "---")):
                summary = cleaned
                break

    package_success = None
    package_fail = None
    if re.search(r"\bpackages?\b", lowered):
        install_ok = len(re.findall(r"(?i)\binstalled\b", joined))
        install_failed = len(re.findall(r"(?i)\bfailed\b", joined))
        if install_ok or install_failed:
            package_success = install_ok
            package_fail = install_failed

    return failed_stage, summary, package_success, package_fail


def build_failure_payload(status: int | None, log_file: Path | None) -> dict[str, Any]:
    session = read_json([LIVE_SESSION_PATH, DEFAULT_SESSION_PATH])
    choices = load_choices(Path("/"), prefer_live=True)
    started_at = int(session.get("started_at_epoch") or 0)
    duration = max(0, int(datetime.now(timezone.utc).timestamp()) - started_at) if started_at > 0 else None
    failed_stage, summary, success_count, fail_count = summarize_failure_log(log_file)

    payload: dict[str, Any] = {
        "install_result": "failed",
        "timestamp_utc": utc_now(),
        "install_duration_seconds": duration,
        "keskos_version": detect_keskos_version(Path("/")) or "KeskOS Live",
        "iso_build_id": detect_iso_build_id(session, Path("/")),
        "kernel_version": detect_kernel_version(),
        "calamares_version": detect_calamares_version(),
        "install_mode": detect_install_mode(),
        "boot_mode": detect_boot_mode(session),
        "desktop_profile_selected": selected_desktop_profile(choices),
        "browser_selected": selected_browser_from_choices(choices),
        "optional_apps_selected": selected_optional_apps(choices, True, Path("/")),
        "failed_stage": failed_stage,
        "sanitized_error_summary": summary or (f"Calamares exited with status {status}." if status is not None else None),
        "timezone": detect_timezone(Path("/")),
        "locale_language": detect_locale_language(Path("/")),
        "cpu_model": detect_cpu_model(),
        "ram_amount": detect_ram_amount(),
        "disk_size": detect_disk_size(),
        "gpu_vendor_model": detect_gpu_vendor_model(),
        "network_online_during_install": detect_network_online_during_install(session),
        "package_install_success_count": success_count,
        "package_install_fail_count": fail_count,
    }
    return enforce_size_limit(prune_unknowns(sanitize_payload(payload)))


def installer_report_already_sent() -> bool:
    return INSTALL_REPORT_SENT_MARKER.exists() or INSTALL_REPORT_SENT_STATE.exists()


def mark_installer_report_sent(payload: dict[str, Any]) -> None:
    marker_payload = {
        "install_result": payload.get("install_result", "success"),
        "timestamp_utc": utc_now(),
        "iso_build_id": payload.get("iso_build_id"),
    }
    for path in (INSTALL_REPORT_SENT_MARKER, INSTALL_REPORT_SENT_STATE):
        write_marker(path, marker_payload)


def load_runtime_payload() -> dict[str, Any]:
    raw = os.environ.get("KESK_INSTALL_REPORT_RUNTIME_JSON", "").strip()
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def basic_payload_from_source() -> dict[str, Any]:
    return read_json([DEFAULT_SOURCE_PATH])


def build_followup_payload(include_extra: bool) -> dict[str, Any]:
    payload = dict(basic_payload_from_source())
    runtime = load_runtime_payload()

    if runtime.get("install_result"):
        payload["install_result"] = sanitize_string(str(runtime["install_result"]))
    if runtime.get("browser_selected"):
        payload["browser_selected"] = sanitize_string(str(runtime["browser_selected"]))
    if "top_bar_widgets_selected" in runtime:
        payload["top_bar_widgets_selected"] = [sanitize_string(str(item)) for item in runtime.get("top_bar_widgets_selected") or []]
    if "optional_apps_selected" in runtime:
        payload["optional_apps_selected"] = [sanitize_string(str(item)) for item in runtime.get("optional_apps_selected") or []]

    if include_extra:
        payload["extra_diagnostics"] = sanitize_payload(
            {
                "welcome_mode": runtime.get("welcome_mode", "unknown"),
                "network_connection_type": runtime.get("network_connection_type", "unknown"),
                "network_uplink_checked": bool(runtime.get("network_uplink_checked", False)),
                "network_uplink_online": bool(runtime.get("network_uplink_online", False)),
                "nmcli_available": bool(runtime.get("nmcli_available", False)),
                "ping_available": bool(runtime.get("ping_available", False)),
                "browser_install_result": runtime.get("browser_install_result", "unknown"),
                "browser_default_result": runtime.get("browser_default_result", "unknown"),
                "browser_theme_result": runtime.get("browser_theme_result", "unknown"),
                "topbar_result": runtime.get("topbar_result", "unknown"),
                "optional_apps_result": runtime.get("optional_apps_result", "unknown"),
                "theme_result": runtime.get("theme_result", "unknown"),
            }
        )

    payload["timestamp_utc"] = utc_now()
    return enforce_size_limit(prune_unknowns(sanitize_payload(payload)))


def followup_has_new_information(payload: dict[str, Any], source: dict[str, Any], include_extra: bool) -> bool:
    if include_extra and payload.get("extra_diagnostics"):
        return True

    for key in ("browser_selected", "top_bar_widgets_selected", "optional_apps_selected", "network_online_during_install"):
        if payload.get(key) != source.get(key):
            return True
    return False


def write_temp_and_send(payload: dict[str, Any], offline_skip: bool) -> tuple[bool, str]:
    write_json(TEMP_REPORT_PATH, payload)
    try:
        if offline_skip and command_exists("ping"):
            online = ping_online()
            if online is False:
                write_log("send skipped offline")
                return False, "Install report skipped because no uplink is available."
        write_log(
            "send payload result={} version={} iso={} keys={}".format(
                payload.get("install_result", "unknown"),
                payload.get("keskos_version", "unknown"),
                payload.get("iso_build_id", "unknown"),
                ",".join(sorted(payload.keys())),
            )
        )
        ok, message = post_payload(payload)
        write_log(
            "send result ok={} bytes={} message={}".format(
                "yes" if ok else "no",
                len(json.dumps(payload, sort_keys=True).encode("utf-8")),
                sanitize_string(message),
            )
        )
        return ok, message
    finally:
        try:
            TEMP_REPORT_PATH.unlink()
        except FileNotFoundError:
            pass


def command_write_source(args: argparse.Namespace) -> int:
    target_root = Path(args.target_root)
    payload = write_success_source(target_root)
    return json_response(True, f"Wrote install report source to {rooted_path(target_root, '/var/lib/keskos/install-report-source.json')}", payload=payload)


def command_send_installer_success(args: argparse.Namespace) -> int:
    target_root = Path(args.target_root)
    payload = json_path(rooted_path(target_root, "/var/lib/keskos/install-report-source.json"))
    if not payload:
        payload = write_success_source(target_root)
    payload = enforce_size_limit(prune_unknowns(sanitize_payload(payload)))
    write_log(
        "installer success send requested iso_build_id={} browser={}".format(
            payload.get("iso_build_id", "unknown"),
            payload.get("browser_selected", "unknown"),
        )
    )
    ok, message = write_temp_and_send(payload, offline_skip=True)
    if ok:
        mark_installer_report_sent(payload)
    return json_response(ok, message)


def command_send_installer_failure(args: argparse.Namespace) -> int:
    log_file = Path(args.log_file) if args.log_file else None
    payload = build_failure_payload(args.status, log_file)
    write_log(
        "installer failure send requested status={} stage={}".format(
            args.status if args.status is not None else "unknown",
            payload.get("failed_stage", "unknown"),
        )
    )
    ok, message = write_temp_and_send(payload, offline_skip=False)
    return json_response(ok, message)


def command_send_followup(args: argparse.Namespace) -> int:
    include_extra = bool(args.include_extra)
    source_payload = basic_payload_from_source()
    payload = build_followup_payload(include_extra)

    if installer_report_already_sent() and not followup_has_new_information(payload, source_payload, include_extra):
        message = "Basic installer report already sent during installation."
        write_log("follow-up basic report skipped because installer report marker exists and no new fields were added")
        return json_response(True, message)

    write_log(
        "follow-up send requested include_extra={} browser={} optional_apps={} widgets={}".format(
            "yes" if include_extra else "no",
            payload.get("browser_selected", "unknown"),
            len(payload.get("optional_apps_selected", [])),
            len(payload.get("top_bar_widgets_selected", [])),
        )
    )
    ok, message = write_temp_and_send(payload, offline_skip=True)
    return json_response(ok, message)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="KeskOS install report helper")
    subparsers = parser.add_subparsers(dest="command", required=True)

    write_source = subparsers.add_parser("write-source", help="Collect installer success payload source data")
    write_source.add_argument("--target-root", default="/", help="Target root to inspect")
    write_source.set_defaults(func=command_write_source)

    success = subparsers.add_parser("send-installer-success", help="Send the success install report from the installer")
    success.add_argument("--target-root", default="/", help="Target root to inspect")
    success.set_defaults(func=command_send_installer_success)

    failure = subparsers.add_parser("send-installer-failure", help="Send the failed install report from the installer")
    failure.add_argument("--status", type=int, default=None, help="Calamares exit status")
    failure.add_argument("--log-file", default="", help="Installer log file to summarize")
    failure.set_defaults(func=command_send_installer_failure)

    followup = subparsers.add_parser("send", help="Send an optional post-install follow-up report")
    followup.add_argument("--include-extra", action="store_true", help="Include extra diagnostic details")
    followup.set_defaults(func=command_send_followup)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
