from __future__ import annotations

from datetime import datetime
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

ACCENT_HEX = "#ce6a35"
APP_VERSION = "0.1.0"

STATUS_PREFIXES = {
    "ok": "[ OK ]",
    "warn": "[ !! ]",
    "work": "[ .. ]",
    "skip": "[ -- ]",
}


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
