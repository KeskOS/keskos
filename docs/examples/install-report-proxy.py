#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import threading
import time
import urllib.error
import urllib.request

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

DISCORD_WEBHOOK = os.environ.get("DISCORD_INSTALL_REPORT_WEBHOOK", "").strip()
HOST = os.environ.get("INSTALL_REPORT_HOST", "127.0.0.1")
PORT = int(os.environ.get("INSTALL_REPORT_PORT", "8080"))
MAX_BODY_BYTES = 16 * 1024
RATE_LIMIT_WINDOW = 60
RATE_LIMIT_MAX = 20

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
    "error_stage_if_failed",
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

lock = threading.Lock()
recent_requests: dict[str, list[float]] = {}


def clean_payload(payload: dict) -> dict:
    cleaned = {key: payload[key] for key in ALLOWED_FIELDS if key in payload}
    extra = cleaned.get("extra_diagnostics")
    if extra is not None and not isinstance(extra, dict):
        cleaned.pop("extra_diagnostics", None)
    return cleaned


def rate_limited(client_ip: str) -> bool:
    now = time.time()
    with lock:
        bucket = [value for value in recent_requests.get(client_ip, []) if now - value < RATE_LIMIT_WINDOW]
        if len(bucket) >= RATE_LIMIT_MAX:
            recent_requests[client_ip] = bucket
            return True
        bucket.append(now)
        recent_requests[client_ip] = bucket
        return False


def discord_message(payload: dict) -> dict:
    lines = [
        f"install_result: {payload.get('install_result', 'unknown')}",
        f"keskos_version: {payload.get('keskos_version', 'unknown')}",
        f"iso_build_id: {payload.get('iso_build_id', 'unknown')}",
        f"install_mode: {payload.get('install_mode', 'unknown')}",
        f"boot_mode: {payload.get('boot_mode', 'unknown')}",
        f"browser_selected: {payload.get('browser_selected', 'unknown')}",
        f"top_bar_widgets_selected: {payload.get('top_bar_widgets_selected', [])}",
        f"optional_apps_selected: {payload.get('optional_apps_selected', [])}",
        f"sanitized_error_summary: {payload.get('sanitized_error_summary', '') or 'none'}",
    ]
    return {"content": "KeskOS install report\n```text\n" + "\n".join(lines) + "\n```"}


def post_to_discord(payload: dict) -> None:
    if not DISCORD_WEBHOOK:
        raise RuntimeError("DISCORD_INSTALL_REPORT_WEBHOOK is not configured")

    data = json.dumps(discord_message(payload)).encode("utf-8")
    request = urllib.request.Request(
        DISCORD_WEBHOOK,
        data=data,
        headers={"Content-Type": "application/json", "User-Agent": "keskos-install-report-proxy/1"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=5) as response:
        if response.status < 200 or response.status >= 300:
            raise RuntimeError(f"Discord returned HTTP {response.status}")


class Handler(BaseHTTPRequestHandler):
    server_version = "KeskInstallReportProxy/1"

    def do_POST(self) -> None:
        if self.path != "/install-report":
            self.send_error(404, "Not found")
            return

        client_ip = self.client_address[0]
        if rate_limited(client_ip):
            self.send_error(429, "Rate limit exceeded")
            return

        try:
            content_length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self.send_error(400, "Invalid Content-Length")
            return

        if content_length <= 0 or content_length > MAX_BODY_BYTES:
            self.send_error(413, "Payload too large")
            return

        raw = self.rfile.read(content_length)
        try:
            payload = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            self.send_error(400, "Invalid JSON")
            return

        if not isinstance(payload, dict):
            self.send_error(400, "JSON body must be an object")
            return

        cleaned = clean_payload(payload)
        try:
            post_to_discord(cleaned)
        except (RuntimeError, urllib.error.URLError) as error:
            self.send_error(502, f"Forwarding failed: {error}")
            return

        response = json.dumps({"ok": True}).encode("utf-8")
        self.send_response(202)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response)))
        self.end_headers()
        self.wfile.write(response)

    def log_message(self, format: str, *args) -> None:
        return


if __name__ == "__main__":
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"listening on http://{HOST}:{PORT}/install-report")
    server.serve_forever()
