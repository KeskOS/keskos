from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import importlib.util
import json
from pathlib import Path
import os
import shlex
import signal
import subprocess
import sys
import tempfile
from typing import Iterable, Sequence

try:
    from rich import box
    from rich.console import Console
    from rich.markup import escape as rich_escape
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text

    HAS_RICH = True
except ImportError:  # pragma: no cover - fallback path
    HAS_RICH = False
    Console = None
    Panel = None
    Table = None
    Text = None
    box = None
    rich_escape = None

APP_VERSION = "0.1.0"
BRANDING_HELPER_PATH = Path("/usr/lib/keskos/branding.py")
DEFAULT_ACCENT_HEX = "#ce6a35"

STATUS_PREFIXES = {
    "ok": "[ OK ]",
    "warn": "[ !! ]",
    "work": "[ .. ]",
    "skip": "[ -- ]",
}


@dataclass(frozen=True)
class Branding:
    name: str = "KeskOS"
    pretty_name: str = "KeskOS"
    layer: str = ""
    layer_name: str = ""
    brand_line: str = "KeskOS"
    channel: str = "stable"
    build_id: str = "dev"
    accent_color: str = DEFAULT_ACCENT_HEX
    home_url: str = "https://keskos.org"
    documentation_url: str = "https://docs.keskos.org"
    download_url: str = "https://downloads.keskos.org"
    support_url: str = "https://docs.keskos.org"
    bug_report_url: str = "https://github.com/KeskOS"

    def as_json(self) -> dict[str, str]:
        return {
            "name": self.name,
            "pretty_name": self.pretty_name,
            "layer": self.layer,
            "layer_name": self.layer_name,
            "brand_line": self.brand_line,
            "channel": self.channel,
            "build_id": self.build_id,
            "accent_color": self.accent_color,
            "home_url": self.home_url,
            "documentation_url": self.documentation_url,
            "download_url": self.download_url,
            "support_url": self.support_url,
            "bug_report_url": self.bug_report_url,
        }


_branding_cache: Branding | None = None


def _normalize_branding(payload: dict[str, object]) -> Branding:
    name = str(payload.get("name") or "KeskOS").strip() or "KeskOS"
    layer = str(payload.get("layer") or "").strip()
    layer_name = str(payload.get("layer_name") or "").strip()
    brand_line = str(payload.get("brand_line") or "").strip()
    pretty_name = str(payload.get("pretty_name") or "").strip()

    if not layer_name and layer:
        layer_name = f"Layer {layer}"
    if not brand_line:
        brand_line = pretty_name or name
    if not pretty_name:
        pretty_name = brand_line or name

    return Branding(
        name=name,
        pretty_name=pretty_name or "KeskOS",
        layer=layer,
        layer_name=layer_name,
        brand_line=brand_line or name,
        channel=str(payload.get("channel") or "stable").strip() or "stable",
        build_id=str(payload.get("build_id") or "dev").strip() or "dev",
        accent_color=str(payload.get("accent_color") or DEFAULT_ACCENT_HEX).strip() or DEFAULT_ACCENT_HEX,
        home_url=str(payload.get("home_url") or "https://keskos.org").strip() or "https://keskos.org",
        documentation_url=str(payload.get("documentation_url") or "https://docs.keskos.org").strip()
        or "https://docs.keskos.org",
        download_url=str(payload.get("download_url") or "https://downloads.keskos.org").strip()
        or "https://downloads.keskos.org",
        support_url=str(payload.get("support_url") or "https://docs.keskos.org").strip() or "https://docs.keskos.org",
        bug_report_url=str(payload.get("bug_report_url") or "https://github.com/KeskOS").strip()
        or "https://github.com/KeskOS",
    )


def _load_branding_from_helper() -> Branding | None:
    if not BRANDING_HELPER_PATH.is_file():
        return None

    spec = importlib.util.spec_from_file_location("keskos_branding", BRANDING_HELPER_PATH)
    if spec is None or spec.loader is None:
        return None

    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception:
        return None

    load_branding = getattr(module, "load_branding", None)
    if callable(load_branding):
        try:
            branding = load_branding()
        except Exception:
            branding = None
        if branding is not None:
            return _normalize_branding(getattr(branding, "__dict__", {}))

    payload: dict[str, object] = {}
    for attr, field_name in (
        ("OS_NAME", "name"),
        ("OS_PRETTY_NAME", "pretty_name"),
        ("OS_LAYER", "layer"),
        ("OS_LAYER_NAME", "layer_name"),
        ("OS_BRAND_LINE", "brand_line"),
        ("OS_CHANNEL", "channel"),
        ("OS_BUILD_ID", "build_id"),
        ("OS_ACCENT_COLOR", "accent_color"),
        ("OS_HOME_URL", "home_url"),
        ("OS_DOCUMENTATION_URL", "documentation_url"),
        ("OS_DOWNLOAD_URL", "download_url"),
        ("OS_SUPPORT_URL", "support_url"),
        ("OS_BUG_REPORT_URL", "bug_report_url"),
    ):
        value = getattr(module, attr, None)
        if isinstance(value, str) and value.strip():
            payload[field_name] = value.strip()

    return _normalize_branding(payload) if payload else None


def load_branding(force_reload: bool = False) -> Branding:
    global _branding_cache

    if _branding_cache is not None and not force_reload:
        return _branding_cache

    branding = _load_branding_from_helper()
    if branding is None:
        branding = Branding()

    _branding_cache = branding
    return branding


def branded_header_title(suffix: str) -> str:
    brand_line = load_branding().brand_line.strip() or "KeskOS"
    return f"{brand_line} {suffix}".strip()


def branding_version_rows() -> list[tuple[str, str]]:
    branding = load_branding()
    return [
        ("OS", branding.brand_line),
        ("Layer", branding.layer or "unavailable"),
        ("Channel", branding.channel),
        ("Build", branding.build_id),
    ]


ACCENT_HEX = load_branding().accent_color or DEFAULT_ACCENT_HEX


def shell_join(command: Sequence[str]) -> str:
    return " ".join(shlex.quote(part) for part in command)


def state_home() -> Path:
    if os.environ.get("KESK_LOG_DIR"):
        return Path(os.environ["KESK_LOG_DIR"]).expanduser()
    if os.environ.get("XDG_STATE_HOME"):
        return Path(os.environ["XDG_STATE_HOME"]).expanduser() / "kesk" / "logs"
    return Path.home() / ".local" / "state" / "kesk" / "logs"


def log_dir_candidates() -> list[Path]:
    candidates: list[Path] = []
    uid = os.getuid() if hasattr(os, "getuid") else os.getpid()

    if os.environ.get("KESK_LOG_DIR"):
        candidates.append(Path(os.environ["KESK_LOG_DIR"]).expanduser())
    if os.environ.get("XDG_STATE_HOME"):
        candidates.append(Path(os.environ["XDG_STATE_HOME"]).expanduser() / "kesk" / "logs")

    candidates.append(Path.home() / ".local" / "state" / "kesk" / "logs")

    if os.environ.get("XDG_RUNTIME_DIR"):
        candidates.append(Path(os.environ["XDG_RUNTIME_DIR"]).expanduser() / "kesk" / "logs")

    candidates.append(Path(tempfile.gettempdir()) / f"kesk-{uid}" / "logs")

    deduped: list[Path] = []
    seen: set[Path] = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        deduped.append(candidate)
    return deduped


class SessionLogger:
    def __init__(self, scope: str) -> None:
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        self.path: Path | str = "logging unavailable"
        self._handle = None
        self._logging_enabled = False

        for logs_dir in log_dir_candidates():
            try:
                logs_dir.mkdir(parents=True, exist_ok=True)
                path = logs_dir / f"{scope}-{timestamp}.log"
                handle = path.open("a", encoding="utf-8", buffering=1)
            except OSError:
                continue

            self.path = path
            self._handle = handle
            self._logging_enabled = True
            break

        self.log(f"start_time={datetime.now().isoformat()}")

    def log(self, message: str) -> None:
        if not self._logging_enabled or self._handle is None:
            return
        stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._handle.write(f"{stamp} {message}\n")

    def close(self) -> None:
        self.log(f"end_time={datetime.now().isoformat()}")
        if self._handle is not None:
            self._handle.close()


class KeskConsole:
    def __init__(self) -> None:
        self.use_ansi = sys.stdout.isatty() and os.environ.get("TERM", "dumb") != "dumb"
        self.console = Console(highlight=False, soft_wrap=True) if HAS_RICH else None

    def _accent(self, text: str) -> str:
        if not self.use_ansi:
            return text
        return f"\033[38;2;206;106;53m{text}\033[0m"

    def _muted(self, text: str) -> str:
        if not self.use_ansi:
            return text
        return f"\033[90m{text}\033[0m"

    def clear(self) -> None:
        if self.console:
            self.console.clear()
            return
        if self.use_ansi:
            sys.stdout.write("\033[2J\033[H")
            sys.stdout.flush()

    def header(self, title: str, subtitle: str) -> None:
        if self.console:
            body = Text()
            body.append(f"{title}\n", style=f"bold {ACCENT_HEX}")
            body.append(subtitle, style="bold white")
            self.console.print(
                Panel.fit(
                    body,
                    border_style=ACCENT_HEX,
                    box=box.SQUARE,
                    padding=(0, 2),
                )
            )
            return

        lines = [title, subtitle]
        width = max(len(line) for line in lines) + 4
        top = f"┌{'─' * width}┐"
        bottom = f"└{'─' * width}┘"
        print(self._accent(top))
        for line in lines:
            print(self._accent("│") + f" {line.ljust(width - 2)} " + self._accent("│"))
        print(self._accent(bottom))

    def status(self, kind: str, message: str) -> None:
        prefix = STATUS_PREFIXES.get(kind, STATUS_PREFIXES["work"])
        if self.console:
            line = Text()
            line.append(prefix, style=f"bold {ACCENT_HEX}")
            line.append(" ")
            line.append(message)
            self.console.print(line)
            return
        print(f"{self._accent(prefix)} {message}")

    def section(self, title: str) -> None:
        if self.console:
            self.console.rule(f"[{ACCENT_HEX}]{title}[/{ACCENT_HEX}]", style=ACCENT_HEX)
            return
        print(self._accent(f"\n== {title} =="))

    def line(self, message: str = "") -> None:
        if self.console:
            self.console.print(message, markup=False, highlight=False)
            return
        print(message)

    def muted(self, message: str) -> None:
        if self.console:
            self.console.print(Text(message, style="bright_black"))
            return
        print(self._muted(message))

    def menu(self, options: Iterable[str]) -> None:
        for option in options:
            self.line(option)

    def table(self, title: str, rows: Sequence[tuple[str, str]]) -> None:
        if self.console:
            table = Table(title=title, title_style=f"bold {ACCENT_HEX}", box=box.SQUARE, border_style=ACCENT_HEX)
            table.add_column("Command", style=f"bold {ACCENT_HEX}")
            table.add_column("Description", style="white")
            for command, description in rows:
                table.add_row(command, description)
            self.console.print(table)
            return

        self.section(title)
        for command, description in rows:
            self.line(f"{command.ljust(18)} {description}")

    def input(self, prompt: str) -> str:
        prompt_text = f"{prompt}: "
        if self.console:
            escaped = rich_escape(prompt_text) if rich_escape else prompt_text
            return self.console.input(f"[{ACCENT_HEX}]{escaped}[/{ACCENT_HEX}]")
        return input(self._accent(prompt_text))

    def confirm(self, prompt: str, default: bool = False) -> bool:
        suffix = "[Y/n]" if default else "[y/N]"
        try:
            answer = self.input(f"{prompt} {suffix}").strip().lower()
        except EOFError:
            return default
        if not answer:
            return default
        return answer in {"y", "yes"}

    def pause(self, message: str = "Press Enter to return") -> None:
        try:
            self.input(message)
        except EOFError:
            return

    def command_output(self, message: str) -> None:
        if self.console:
            self.console.print(message, markup=False, highlight=False)
            return
        print(message)


def run_capture(command: Sequence[str], logger: SessionLogger) -> subprocess.CompletedProcess[str]:
    logger.log(f"command={shell_join(command)}")
    result = subprocess.run(
        list(command),
        check=False,
        capture_output=True,
        text=True,
        errors="replace",
    )
    logger.log(f"exit_code={result.returncode}")
    if result.stdout.strip():
        logger.log("stdout_begin")
        for line in result.stdout.splitlines():
            logger.log(f"stdout {line}")
        logger.log("stdout_end")
    if result.stderr.strip():
        logger.log("stderr_begin")
        for line in result.stderr.splitlines():
            logger.log(f"stderr {line}")
        logger.log("stderr_end")
    return result


def stream_command(command: Sequence[str], logger: SessionLogger, console: KeskConsole) -> int:
    logger.log(f"command={shell_join(command)}")
    process = subprocess.Popen(
        list(command),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        errors="replace",
        bufsize=1,
    )

    try:
        assert process.stdout is not None
        for line in process.stdout:
            line = line.rstrip("\n")
            console.command_output(line)
            logger.log(f"output {line}")
    except KeyboardInterrupt:
        process.send_signal(signal.SIGINT)
        process.wait()
        logger.log("interrupted=true")
        raise

    exit_code = process.wait()
    logger.log(f"exit_code={exit_code}")
    return exit_code
