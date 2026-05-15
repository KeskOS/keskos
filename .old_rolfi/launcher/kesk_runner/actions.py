from __future__ import annotations

import os
import shlex
import shutil
import subprocess
from pathlib import Path

from .clipboard import copy_text
from .models import ActionOutcome, Result
from .utils import (
    browser_homepage_url,
    hibernate_commands,
    is_kwin_window_id,
    kde_window_runner_commands,
    kde_poweroff_commands,
    kde_restart_commands,
    kdotool_path,
    kde_logout_command,
    launch_detached,
    launch_in_terminal,
    launcher_debug_log,
    launch_shell,
    open_browser,
    open_path,
    run_first_success,
    sanitize_exec,
    suspend_commands,
)


def execute_action(result: Result) -> ActionOutcome:
    action_type = result.action.get("type")

    if action_type == "noop":
        return ActionOutcome(close_rofi=False)

    if action_type == "switch-mode":
        return ActionOutcome(close_rofi=False, switch_mode=result.action["mode"])

    if action_type == "launcher":
        launcher_bin = Path("/usr/local/bin/keskos-launcher")
        mode = result.action.get("mode")
        if not launcher_bin.is_file():
            return ActionOutcome(close_rofi=False, message="keskos-launcher is not installed yet.")
        if not mode:
            return ActionOutcome(close_rofi=False, message="Launcher mode was missing.")
        env = os.environ.copy()
        env.pop("ROFI_RETV", None)
        env.pop("ROFI_INFO", None)
        env.pop("ROFI_DATA", None)
        env.pop("ROFI_INPUT", None)
        command = (
            f"sleep 0.12; "
            f"exec {shlex.quote(str(launcher_bin))} --mode {shlex.quote(str(mode))} "
            ">/dev/null 2>&1"
        )
        try:
            subprocess.Popen(
                ["bash", "-lc", command],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
                env=env,
            )
        except OSError:
            return ActionOutcome(close_rofi=False, message=f"Failed to open the {mode} launcher.")
        return ActionOutcome()

    if action_type == "copy":
        success, message = copy_text(result.action.get("value", ""))
        return ActionOutcome(close_rofi=success, message=message, copied=success)

    if action_type == "app":
        desktop_id = result.action.get("desktop_id")
        exec_line = result.action.get("exec", "")
        if desktop_id and shutil.which("gtk-launch"):
            launch_detached(["gtk-launch", desktop_id])
            return ActionOutcome()
        if exec_line:
            launch_shell(sanitize_exec(exec_line))
            return ActionOutcome()
        return ActionOutcome(close_rofi=False, message="Could not launch the selected app.")

    if action_type == "terminal":
        launch_in_terminal()
        return ActionOutcome()

    if action_type == "command":
        launch_in_terminal(result.action["command"])
        return ActionOutcome()

    if action_type == "browser":
        open_browser(result.action.get("url") or browser_homepage_url())
        return ActionOutcome()

    if action_type == "path":
        open_path(result.action["path"], prefer_dolphin=bool(result.action.get("prefer_dolphin")))
        return ActionOutcome()

    if action_type == "web":
        open_browser(result.action["url"])
        return ActionOutcome()

    if action_type == "settings":
        module = result.action.get("module", "")
        if module:
            launch_shell(f"systemsettings {module} >/dev/null 2>&1 || systemsettings >/dev/null 2>&1")
        else:
            launch_detached(["systemsettings"])
        return ActionOutcome()

    if action_type == "power":
        name = result.action["name"]
        if name == "lock":
            if shutil.which("loginctl"):
                launch_detached(["loginctl", "lock-session"])
                return ActionOutcome()
            return ActionOutcome(close_rofi=False, message="loginctl is not available for screen locking.")
        if name == "logout":
            if run_first_success(kde_logout_command()):
                return ActionOutcome()
            return ActionOutcome(close_rofi=False, message="No KDE logout command succeeded.")
        if name == "suspend":
            if run_first_success(suspend_commands()):
                return ActionOutcome()
            return ActionOutcome(close_rofi=False, message="No suspend command succeeded.")
        if name == "hibernate":
            if run_first_success(hibernate_commands()):
                return ActionOutcome()
            return ActionOutcome(close_rofi=False, message="No hibernate command succeeded.")
        if name == "reboot":
            if run_first_success(kde_restart_commands()):
                return ActionOutcome()
            return ActionOutcome(close_rofi=False, message="No restart command succeeded.")
        if name == "poweroff":
            if run_first_success(kde_poweroff_commands()):
                return ActionOutcome()
            return ActionOutcome(close_rofi=False, message="No shutdown command succeeded.")
        return ActionOutcome(close_rofi=False, message=f"Unsupported power action: {name}")

    if action_type == "window":
        window_id = result.action.get("window_id")
        if not window_id:
            return ActionOutcome(close_rofi=False, message="No window id was attached to the selected result.")

        if is_kwin_window_id(window_id):
            binary = kdotool_path()
            if not binary:
                return ActionOutcome(
                    close_rofi=False,
                    message="kdotool is not installed, so Wayland window switching cannot stay inside the launcher.",
                )

            completed = subprocess.run(
                [binary, "windowactivate", window_id],
                capture_output=True,
                text=True,
                check=False,
            )
            launcher_debug_log(
                "kdotool activate "
                + f"window_id={window_id!r} rc={completed.returncode} "
                + f"stdout={completed.stdout!r} stderr={completed.stderr!r}"
            )
            if completed.returncode == 0:
                return ActionOutcome()
            return ActionOutcome(close_rofi=False, message="kdotool could not focus the selected Wayland window.")

        if not shutil.which("wmctrl"):
            return ActionOutcome(close_rofi=False, message="wmctrl is not available for window focusing.")
        completed = subprocess.run(["wmctrl", "-ia", window_id], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        if completed.returncode == 0:
            return ActionOutcome()
        return ActionOutcome(close_rofi=False, message="Failed to focus the selected window.")

    if action_type == "krunner-windows":
        query = str(result.action.get("query", ""))
        if run_first_success(kde_window_runner_commands(query)):
            return ActionOutcome()
        return ActionOutcome(close_rofi=False, message="KDE's window runner is not available.")

    return ActionOutcome(close_rofi=False, message=f"Unsupported action type: {action_type}")


def builtin_result(name: str, home: Path) -> Result:
    homepage_url = browser_homepage_url()
    if name == "terminal":
        return Result(
            id="builtin:terminal",
            title="Terminal",
            subtitle="Open terminal",
            category="Actions",
            score=0,
            action={"type": "terminal"},
        )
    if name == "files":
        return Result(
            id="builtin:files",
            title="Files",
            subtitle=str(home),
            category="Actions",
            score=0,
            action={"type": "path", "path": str(home), "prefer_dolphin": True},
        )
    if name == "browser":
        return Result(
            id="builtin:browser",
            title="Browser",
            subtitle=homepage_url,
            category="Actions",
            score=0,
            action={"type": "browser", "url": homepage_url},
        )
    raise ValueError(f"Unknown builtin action: {name}")
