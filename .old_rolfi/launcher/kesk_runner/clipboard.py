from __future__ import annotations

import os
import shutil
import subprocess


def copy_text(value: str) -> tuple[bool, str]:
    session_type = os.environ.get("XDG_SESSION_TYPE", "").lower()

    if session_type == "wayland" and shutil.which("wl-copy"):
        completed = subprocess.run(["wl-copy"], input=value.encode("utf-8"), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return completed.returncode == 0, "Copied to clipboard." if completed.returncode == 0 else "Failed to copy with wl-copy."

    if shutil.which("xclip"):
        completed = subprocess.run(["xclip", "-selection", "clipboard"], input=value.encode("utf-8"), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return completed.returncode == 0, "Copied to clipboard." if completed.returncode == 0 else "Failed to copy with xclip."

    if shutil.which("xsel"):
        completed = subprocess.run(["xsel", "--clipboard", "--input"], input=value.encode("utf-8"), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return completed.returncode == 0, "Copied to clipboard." if completed.returncode == 0 else "Failed to copy with xsel."

    return False, "Clipboard tool missing."
