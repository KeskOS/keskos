from __future__ import annotations

import json
import subprocess
from typing import Sequence

from PySide6.QtCore import QObject, QRunnable, QProcess, Signal


class WorkerSignals(QObject):
    finished = Signal(object)
    failed = Signal(str)


class CommandWorker(QRunnable):
    def __init__(self, command: Sequence[str], *, timeout: int = 30, parse_json: bool = False) -> None:
        super().__init__()
        self.command = list(command)
        self.timeout = timeout
        self.parse_json = parse_json
        self.signals = WorkerSignals()

    def run(self) -> None:
        try:
            result = subprocess.run(
                self.command,
                check=False,
                capture_output=True,
                text=True,
                errors="replace",
                timeout=self.timeout,
            )
        except subprocess.TimeoutExpired as exc:
            self.signals.failed.emit(f"Command timed out after {self.timeout}s: {' '.join(self.command)}")
            return
        except OSError as exc:
            self.signals.failed.emit(str(exc))
            return

        payload: object
        if self.parse_json:
            try:
                payload = json.loads(result.stdout or "{}")
            except json.JSONDecodeError as exc:
                self.signals.failed.emit(f"Invalid JSON from {' '.join(self.command)}: {exc}")
                return
        else:
            payload = {
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }

        if result.returncode not in {0, 2}:
            stderr = (result.stderr or result.stdout).strip()
            self.signals.failed.emit(stderr or f"Command failed with exit code {result.returncode}")
            return

        if isinstance(payload, dict):
            payload = dict(payload)
            payload["_returncode"] = result.returncode
        self.signals.finished.emit(payload)


class StreamProcess(QObject):
    output = Signal(str)
    finished = Signal(int)
    failed = Signal(str)

    def __init__(self, command: Sequence[str]) -> None:
        super().__init__()
        self.command = list(command)
        self.process = QProcess()
        self.process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self.process.readyReadStandardOutput.connect(self._drain_output)
        self.process.finished.connect(self._on_finished)
        self.process.errorOccurred.connect(self._on_error)

    def start(self) -> None:
        if not self.command:
            self.failed.emit("No command was provided.")
            return
        self.process.start(self.command[0], self.command[1:])

    def kill(self) -> None:
        if self.process.state() != QProcess.ProcessState.NotRunning:
            self.process.kill()

    def _drain_output(self) -> None:
        data = bytes(self.process.readAllStandardOutput()).decode("utf-8", errors="replace")
        if data:
            self.output.emit(data)

    def _on_finished(self, exit_code: int, _status: QProcess.ExitStatus) -> None:
        self._drain_output()
        self.finished.emit(exit_code)

    def _on_error(self, _error: QProcess.ProcessError) -> None:
        self.failed.emit(self.process.errorString())
