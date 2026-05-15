from __future__ import annotations

import html
import os
import re
import shlex
import shutil
import subprocess
from pathlib import Path


CATEGORY_WEIGHTS = {
    "Calculator": 5200,
    "Units": 5100,
    "Apps": 4400,
    "Settings": 4100,
    "Recent": 3950,
    "Places": 3600,
    "Files": 3400,
    "Web": 3200,
    "Power": 2600,
    "Windows": 2500,
    "Commands": 1600,
}

URL_RE = re.compile(r"^(?:https?://|file://|about:)[^\s]+$", re.IGNORECASE)
HOST_RE = re.compile(
    r"^(?:localhost|(?:[a-z0-9-]+\.)+[a-z]{2,}|(?:\d{1,3}\.){3}\d{1,3})(?::\d+)?(?:/.*)?$",
    re.IGNORECASE,
)
KWIN_WINDOW_ID_RE = re.compile(r"^\{[0-9a-fA-F-]{36}\}$")
FIELD_CODE_RE = re.compile(r"%(?:[uUfFickK])")
UNSAFE_COMMAND_RE = re.compile(
    r"(^|\s)(rm\s+-rf|dd(\s|$)|mkfs(\.|$|\s)|reboot(\s|$)|shutdown(\s|$)|poweroff(\s|$)|systemctl\s+reboot|systemctl\s+poweroff)",
    re.IGNORECASE,
)


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def launcher_debug_enabled() -> bool:
    return os.environ.get("KESKOS_LAUNCHER_DEBUG", "").strip().lower() in {"1", "true", "yes", "on"}


def launcher_debug_log(message: str) -> None:
    if not launcher_debug_enabled():
        return

    debug_log = cache_home() / "keskos" / "launcher-debug.log"
    debug_log.parent.mkdir(parents=True, exist_ok=True)
    with debug_log.open("a", encoding="utf-8") as handle:
        handle.write(f"{message}\n")


def escape_markup(value: str) -> str:
    return html.escape(value, quote=False)


def exactish_terms(*values: str) -> list[str]:
    return [value for value in values if value]


def _fuzzy_score(query: str, candidate: str) -> int | None:
    if not query or not candidate:
        return None

    cursor = -1
    score = 0
    for char in query:
        index = candidate.find(char, cursor + 1)
        if index < 0:
            return None
        if index == cursor + 1:
            score += 14
        else:
            score += max(2, 8 - (index - cursor))
        cursor = index
    return score - len(candidate)


def match_score(query: str, values: list[str]) -> int | None:
    normalized_query = normalize_text(query)
    if not normalized_query:
        return 0

    best: int | None = None
    for value in values:
        candidate = normalize_text(value)
        if not candidate:
            continue

        if candidate == normalized_query:
            score = 1200
        elif candidate.startswith(normalized_query):
            score = 1000 - len(candidate)
        elif normalized_query in candidate:
            score = 820 - candidate.index(normalized_query)
        else:
            fuzzy = _fuzzy_score(normalized_query, candidate)
            if fuzzy is None:
                continue
            score = 520 + fuzzy

        if best is None or score > best:
            best = score

    return best


def looks_like_url(value: str) -> bool:
    stripped = value.strip()
    return bool(URL_RE.match(stripped) or HOST_RE.match(stripped))


def normalize_url(value: str) -> str:
    stripped = value.strip()
    if URL_RE.match(stripped):
        return stripped
    if HOST_RE.match(stripped):
        return f"https://{stripped}"
    return stripped


def is_math_expression(value: str) -> bool:
    stripped = value.strip().lower()
    if not stripped:
        return False
    return bool(
        re.fullmatch(r"[\d\s\+\-\*\/\(\)\.,^%a-z_]+", stripped)
        and any(token in stripped for token in ("+", "-", "*", "/", "sqrt", "sin", "cos", "tan", "pi"))
    )


def sanitize_exec(exec_line: str) -> str:
    cleaned = exec_line.replace("%%", "%")
    cleaned = FIELD_CODE_RE.sub("", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def is_kwin_window_id(value: str) -> bool:
    return bool(KWIN_WINDOW_ID_RE.fullmatch(value.strip()))


def kdotool_path() -> str | None:
    return shutil.which("kdotool")


def kdotool_search_pattern(query: str) -> str:
    stripped = query.strip()
    if not stripped:
        return ".*"
    return re.escape(stripped)


def choose_terminal() -> list[str]:
    for candidate in ("konsole", "kitty", "alacritty", "foot", "xterm"):
        if shutil.which(candidate):
            return [candidate]
    return ["xterm"]


def konsole_profile_args() -> list[str]:
    user_profile = Path.home() / ".local/share/konsole" / "KeskOS.profile"
    system_profile = Path("/usr/share/konsole/KeskOS.profile")
    if user_profile.is_file() or system_profile.is_file():
        return ["--profile", "KeskOS"]
    return []


def launch_in_terminal(command: str | None = None) -> None:
    terminal = choose_terminal()
    binary = Path(terminal[0]).name

    if command is None:
        argv = terminal
        if binary == "konsole":
            argv = terminal + konsole_profile_args()
        subprocess.Popen(argv, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        return

    if binary == "konsole":
        argv = terminal + konsole_profile_args() + ["-e", "bash", "-lc", command]
    elif binary in {"kitty", "foot", "xterm"}:
        argv = terminal + ["bash", "-lc", command]
    elif binary == "alacritty":
        argv = terminal + ["-e", "bash", "-lc", command]
    else:
        argv = terminal + ["bash", "-lc", command]

    subprocess.Popen(argv, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)


def launch_detached(argv: list[str]) -> None:
    subprocess.Popen(argv, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)


def launch_shell(command: str) -> None:
    launch_detached(["bash", "-lc", command])


def open_path(target: str, prefer_dolphin: bool = False) -> None:
    if prefer_dolphin and shutil.which("dolphin"):
        launch_detached(["dolphin", target])
        return
    launch_detached(["xdg-open", target])


def browser_homepage_url() -> str:
    homepage_path = "/usr/share/keskos/startpage/index.html"
    if Path(homepage_path).is_file():
        return f"file://{homepage_path}"
    return "https://google.com"


def open_browser(url: str | None = None) -> None:
    target = url or browser_homepage_url()
    if shutil.which("xdg-open"):
        launch_detached(["xdg-open", target])
        return
    if shutil.which("librewolf"):
        launch_detached(["librewolf", target])
        return
    if shutil.which("zen-browser"):
        launch_detached(["zen-browser", target])
        return
    if shutil.which("brave-browser"):
        launch_detached(["brave-browser", target])
        return
    if shutil.which("firefox"):
        launch_detached(["firefox", target])
        return
    open_path(target)


def kde_logout_command() -> list[list[str]]:
    commands: list[list[str]] = []
    if shutil.which("qdbus6"):
        commands.extend(
            [
                ["qdbus6", "org.kde.Shutdown", "/Shutdown", "org.kde.Shutdown.logout"],
                ["qdbus6", "org.kde.ksmserver", "/KSMServer", "logout", "0", "0", "0"],
            ]
        )
    if shutil.which("qdbus"):
        commands.extend(
            [
                ["qdbus", "org.kde.Shutdown", "/Shutdown", "org.kde.Shutdown.logout"],
                ["qdbus", "org.kde.ksmserver", "/KSMServer", "logout", "0", "0", "0"],
            ]
        )
    return commands


def kde_restart_commands() -> list[list[str]]:
    commands: list[list[str]] = []
    if shutil.which("qdbus6"):
        commands.extend(
            [
                ["qdbus6", "org.kde.Shutdown", "/Shutdown", "org.kde.Shutdown.logoutAndReboot"],
                ["qdbus6", "org.freedesktop.login1", "/org/freedesktop/login1", "org.freedesktop.login1.Manager.Reboot", "true"],
                ["loginctl", "reboot"],
                ["systemctl", "reboot"],
            ]
        )
    if shutil.which("qdbus"):
        commands.extend(
            [
                ["qdbus", "org.kde.Shutdown", "/Shutdown", "org.kde.Shutdown.logoutAndReboot"],
            ]
        )
    if shutil.which("loginctl"):
        commands.append(["loginctl", "reboot"])
    if shutil.which("systemctl"):
        commands.append(["systemctl", "reboot"])
    return commands


def kde_poweroff_commands() -> list[list[str]]:
    commands: list[list[str]] = []
    if shutil.which("qdbus6"):
        commands.extend(
            [
                ["qdbus6", "org.kde.Shutdown", "/Shutdown", "org.kde.Shutdown.logoutAndShutdown"],
                ["qdbus6", "org.freedesktop.login1", "/org/freedesktop/login1", "org.freedesktop.login1.Manager.PowerOff", "true"],
            ]
        )
    if shutil.which("qdbus"):
        commands.extend(
            [
                ["qdbus", "org.kde.Shutdown", "/Shutdown", "org.kde.Shutdown.logoutAndShutdown"],
            ]
        )
    if shutil.which("loginctl"):
        commands.append(["loginctl", "poweroff"])
    if shutil.which("systemctl"):
        commands.append(["systemctl", "poweroff"])
    return commands


def suspend_commands() -> list[list[str]]:
    commands: list[list[str]] = []
    if shutil.which("loginctl"):
        commands.append(["loginctl", "suspend"])
    if shutil.which("systemctl"):
        commands.append(["systemctl", "suspend"])
    return commands


def hibernate_commands() -> list[list[str]]:
    commands: list[list[str]] = []
    if shutil.which("loginctl"):
        commands.append(["loginctl", "hibernate"])
    if shutil.which("systemctl"):
        commands.append(["systemctl", "hibernate"])
    return commands


def kde_window_runner_commands(query: str = "") -> list[list[str]]:
    commands: list[list[str]] = []
    for binary in ("qdbus6", "qdbus"):
        if not shutil.which(binary):
            continue
        commands.extend(
            [
                [binary, "org.kde.krunner", "/App", "org.kde.krunner.App.querySingleRunner", "windows", query],
                [binary, "org.kde.krunner", "/App", "querySingleRunner", "windows", query],
            ]
        )
    return commands


def run_first_success(commands: list[list[str]]) -> bool:
    for argv in commands:
        try:
            completed = subprocess.run(argv, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        except OSError:
            continue
        if completed.returncode == 0:
            return True
    return False


def is_dangerous_command(command: str) -> bool:
    return bool(UNSAFE_COMMAND_RE.search(command))


def executable_exists(command: str) -> bool:
    try:
        argv = shlex.split(command)
    except ValueError:
        return False
    if not argv:
        return False
    return shutil.which(argv[0]) is not None


def data_home() -> Path:
    return Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share"))


def cache_home() -> Path:
    return Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
