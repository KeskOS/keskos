from __future__ import annotations

from pathlib import Path
import sys
from typing import Sequence

try:
    from PySide6.QtWidgets import QApplication
except ImportError as exc:  # pragma: no cover - dependency/runtime guard
    QApplication = None
    IMPORT_ERROR = exc
else:  # pragma: no cover - exercised in GUI runtime
    IMPORT_ERROR = None

from .app import build_application


def print_help() -> int:
    print("KESK SETTINGS")
    print("Usage: kesk-settings")
    print()
    print("Launches the KeskOS graphical control center.")
    print("Use `kesk settings` to auto-select GUI or TUI based on the current session.")
    return 0


def main(args: Sequence[str], root: Path) -> int:
    if args and args[0] in {"--help", "-h", "help"}:
        return print_help()

    if QApplication is None or IMPORT_ERROR is not None:
        print("Kesk Settings could not start because PySide6 is unavailable.")
        print(f"Import error: {IMPORT_ERROR}")
        return 1

    app, window = build_application(root)
    window.show()
    return app.exec()
