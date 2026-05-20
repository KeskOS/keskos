from __future__ import annotations

from typing import Any

from .common import BackendStatus, connected, limited, missing, result_payload


def is_available(backend) -> bool:
    return bool(backend.tools.get("bluetoothctl"))


def _systemctl(backend, *args: str) -> bool:
    tool = backend.tools.get("systemctl")
    if not tool:
        return False
    result = backend._run([tool, *args], capture=True, timeout=20)
    return result is not None and result.returncode == 0


def _service_state(backend) -> str:
    tool = backend.tools.get("systemctl")
    if not tool:
        return "unknown"
    result = backend._run([tool, "is-active", "bluetooth.service"], capture=True, timeout=10)
    if result is None or result.returncode != 0:
        return "inactive"
    return result.stdout.strip() or "inactive"


def _paired_devices(backend) -> list[dict[str, str | bool]]:
    tool = backend.tools.get("bluetoothctl")
    if not tool:
        return []
    result = backend._run([tool, "paired-devices"], capture=True, timeout=15)
    if result is None or result.returncode != 0:
        return []
    devices: list[dict[str, str | bool]] = []
    for line in result.stdout.splitlines():
        stripped = line.strip()
        if not stripped.startswith("Device "):
            continue
        parts = stripped.split(maxsplit=2)
        if len(parts) < 3:
            continue
        address = parts[1]
        name = parts[2]
        details = _device_details(backend, address)
        devices.append(
            {
                "address": address,
                "name": name,
                "connected": details.get("connected", False),
                "trusted": details.get("trusted", False),
            }
        )
    return devices


def _device_details(backend, address: str) -> dict[str, bool]:
    tool = backend.tools.get("bluetoothctl")
    if not tool:
        return {}
    result = backend._run([tool, "info", address], capture=True, timeout=10)
    if result is None or result.returncode != 0:
        return {}
    info = {"connected": False, "trusted": False}
    for line in result.stdout.splitlines():
        stripped = line.strip().lower()
        if stripped.startswith("connected:"):
            info["connected"] = stripped.endswith("yes")
        elif stripped.startswith("trusted:"):
            info["trusted"] = stripped.endswith("yes")
    return info


def _nearby_devices(backend) -> list[dict[str, str]]:
    tool = backend.tools.get("bluetoothctl")
    if not tool:
        return []
    result = backend._run([tool, "devices"], capture=True, timeout=15)
    if result is None or result.returncode != 0:
        return []
    devices: list[dict[str, str]] = []
    for line in result.stdout.splitlines():
        stripped = line.strip()
        if not stripped.startswith("Device "):
            continue
        parts = stripped.split(maxsplit=2)
        if len(parts) < 3:
            continue
        devices.append({"address": parts[1], "name": parts[2]})
    return devices


def _adapter_name(backend) -> str:
    tool = backend.tools.get("bluetoothctl")
    if not tool:
        return "Unavailable"
    result = backend._run([tool, "list"], capture=True, timeout=10)
    if result is None or result.returncode != 0:
        return "Unavailable"
    for line in result.stdout.splitlines():
        stripped = line.strip()
        if stripped.startswith("Controller "):
            parts = stripped.split(maxsplit=2)
            if len(parts) >= 3:
                return parts[2]
    return "Unavailable"


def _powered(backend) -> bool | None:
    tool = backend.tools.get("bluetoothctl")
    if not tool:
        return None
    result = backend._run([tool, "show"], capture=True, timeout=10)
    if result is None or result.returncode != 0:
        return None
    for line in result.stdout.splitlines():
        stripped = line.strip().lower()
        if stripped.startswith("powered:"):
            return stripped.endswith("yes")
    return None


def _status(backend) -> BackendStatus:
    if not backend.tools.get("bluetoothctl"):
        return missing("Bluetooth tools are not installed.", missing_tools=["bluetoothctl"], advanced_module="kcm_bluetooth")
    adapter = _adapter_name(backend)
    service = _service_state(backend)
    if adapter == "Unavailable":
        return limited(
            "No Bluetooth adapter was detected.",
            details=["Install or enable the adapter to use Bluetooth controls."],
            advanced_module="kcm_bluetooth",
        )
    if service != "active":
        return limited(
            "Bluetooth tools are available, but the bluetooth.service is not active.",
            details=["Start the service to pair or connect devices."],
            admin_required=True,
            advanced_module="kcm_bluetooth",
        )
    return connected("Bluetooth adapter and service are available.", advanced_module="kcm_bluetooth")


def read_current(backend) -> dict[str, Any]:
    service = _service_state(backend)
    powered = _powered(backend)
    return {
        "status": _status(backend),
        "tool_state": "found" if backend.tools.get("bluetoothctl") else "missing",
        "adapter_name": _adapter_name(backend),
        "adapter_present": _adapter_name(backend) != "Unavailable",
        "service_state": service,
        "service_management_supported": bool(backend.tools.get("pkexec") and backend.tools.get("systemctl")),
        "enabled": bool(powered) if powered is not None else False,
        "receive_files": bool(backend.custom_value("bluetooth_receive_files", False)),
        "paired_devices": _paired_devices(backend),
        "nearby_devices": _nearby_devices(backend),
        "scan_supported": bool(backend.tools.get("bluetoothctl")),
    }


def apply_changes(backend, values: dict[str, Any]) -> dict[str, Any]:
    tool = backend.tools.get("bluetoothctl")
    if not tool:
        return result_payload(False, "Bluetooth tools are not installed.", warnings=["Install bluez-utils to manage Bluetooth devices."])

    details: list[str] = []
    warnings: list[str] = []
    if _service_state(backend) != "active" and bool(values.get("enabled")):
        if backend.tools.get("pkexec") and backend.tools.get("systemctl"):
            backend.run_pkexec([backend.tools["systemctl"], "start", "bluetooth.service"])
        if _service_state(backend) != "active":
            warnings.append("Bluetooth service is not running. The radio state could not be applied.")
            return result_payload(True, "Bluetooth preferences saved with warnings.", warnings=warnings)

    target_state = "on" if bool(values.get("enabled")) else "off"
    result = backend._run([tool, "power", target_state], capture=True, timeout=20)
    if result is not None and result.returncode == 0:
        details.append(f"Bluetooth radio set to {target_state}.")
    else:
        warnings.append("Bluetooth radio state could not be changed.")

    backend.set_custom_values({"bluetooth_receive_files": bool(values.get("receive_files", False))})
    if "receive_files" in values:
        details.append("Stored Bluetooth file-receive preference.")
    return result_payload(True, "Bluetooth settings updated.", details=details, warnings=warnings)


def _device_command(backend, action: str, address: str, *, timeout: int = 45) -> dict[str, Any]:
    tool = backend.tools.get("bluetoothctl")
    if not tool:
        return result_payload(False, "Bluetooth tools are not installed.")
    result = backend._run([tool, action, address], capture=True, timeout=timeout)
    success = result is not None and result.returncode == 0
    summary = f"Bluetooth action `{action}` completed." if success else f"Bluetooth action `{action}` failed."
    warnings = [] if success else [f"`bluetoothctl {action} {address}` did not complete successfully."]
    return result_payload(success, summary, warnings=warnings)


def connect_device(backend, address: str) -> dict[str, Any]:
    return _device_command(backend, "connect", address)


def disconnect_device(backend, address: str) -> dict[str, Any]:
    return _device_command(backend, "disconnect", address)


def pair_device(backend, address: str) -> dict[str, Any]:
    return _device_command(backend, "pair", address, timeout=90)


def trust_device(backend, address: str) -> dict[str, Any]:
    return _device_command(backend, "trust", address)


def remove_device(backend, address: str) -> dict[str, Any]:
    return _device_command(backend, "remove", address)


def start_service(backend) -> dict[str, Any]:
    if not backend.tools.get("systemctl"):
        return result_payload(False, "systemctl is not available.", warnings=["Bluetooth service management requires systemctl."])
    if not backend.tools.get("pkexec"):
        return result_payload(False, "pkexec is not available.", warnings=["Administrator permission is required to start bluetooth.service."])
    result = backend.run_pkexec([backend.tools["systemctl"], "start", "bluetooth.service"])
    if result.returncode == 0 and _service_state(backend) == "active":
        return result_payload(True, "bluetooth.service was started.", details=["Bluetooth service is now active."])
    return result_payload(False, "bluetooth.service could not be started.", warnings=["Bluetooth service start requires admin access and a valid BlueZ installation."])


def scan_devices(backend) -> dict[str, Any]:
    tool = backend.tools.get("bluetoothctl")
    if not tool:
        return result_payload(False, "Bluetooth tools are not installed.", warnings=["Install bluez-utils to scan for Bluetooth devices."])
    if _service_state(backend) != "active":
        return result_payload(False, "Bluetooth service is not running.", warnings=["Start bluetooth.service before scanning for devices."])
    start = backend._run([tool, "--timeout", "12", "scan", "on"], capture=True, timeout=20)
    backend._run([tool, "scan", "off"], capture=True, timeout=10)
    if start is None or start.returncode != 0:
        return result_payload(False, "Bluetooth scan did not complete successfully.", warnings=["bluetoothctl could not start a device scan."])
    return result_payload(True, "Bluetooth device scan completed.", details=["Nearby devices were refreshed from bluetoothctl."])


def open_advanced_settings(backend):
    return backend.open_kcm("kcm_bluetooth")
