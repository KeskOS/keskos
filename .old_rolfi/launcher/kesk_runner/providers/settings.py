from __future__ import annotations

from ..models import Result, SearchContext
from ..utils import CATEGORY_WEIGHTS, match_score, normalize_text


SETTINGS_ROWS = [
    {"id": "display", "title": "Display", "subtitle": "Monitor layout and scaling", "module": "kcm_kscreen", "aliases": ["display", "monitor", "screen", "resolution"]},
    {"id": "network", "title": "Network", "subtitle": "Connections and Wi-Fi", "module": "kcm_networkmanagement", "aliases": ["network", "wifi", "ethernet", "internet"]},
    {"id": "bluetooth", "title": "Bluetooth", "subtitle": "Bluetooth devices and pairing", "module": "kcm_bluetooth", "aliases": ["bluetooth"]},
    {"id": "audio", "title": "Audio", "subtitle": "Sound devices and volume", "module": "kcm_pulseaudio", "aliases": ["audio", "sound", "speaker", "microphone"]},
    {"id": "keyboard", "title": "Keyboard", "subtitle": "Layouts and key repeat", "module": "kcm_keyboard", "aliases": ["keyboard", "layout", "typing"]},
    {"id": "mouse", "title": "Mouse", "subtitle": "Mouse and touchpad settings", "module": "kcm_mouse", "aliases": ["mouse", "touchpad", "pointer"]},
    {"id": "appearance", "title": "Appearance", "subtitle": "Theme, colors, and desktop look", "module": "kcm_desktoptheme", "aliases": ["theme", "appearance", "desktop theme", "look"]},
    {"id": "colors", "title": "Colors", "subtitle": "Color scheme selection", "module": "kcm_colors", "aliases": ["colors", "accent", "palette"]},
    {"id": "power", "title": "Power", "subtitle": "Sleep and battery behavior", "module": "kcm_powerdevilprofilesconfig", "aliases": ["power", "battery", "sleep"]},
    {"id": "users", "title": "Users", "subtitle": "Accounts and permissions", "module": "kcm_users", "aliases": ["users", "accounts", "login"]},
    {"id": "firewall", "title": "Firewall", "subtitle": "Open firewall settings", "module": "", "aliases": ["firewall", "security"]},
]


def search(context: SearchContext, query: str, settings_only: bool = False) -> list[Result]:
    results: list[Result] = []
    normalized_query = normalize_text(query)
    for row in SETTINGS_ROWS:
        score = match_score(query, [row["title"], row["subtitle"], *row["aliases"]])
        if query and score is None:
            continue
        bonus = 0
        if normalized_query:
            if normalized_query == normalize_text(row["title"]) or normalized_query in {normalize_text(alias) for alias in row["aliases"]}:
                bonus = 700
            elif normalize_text(row["title"]).startswith(normalized_query) or any(normalize_text(alias).startswith(normalized_query) for alias in row["aliases"]):
                bonus = 260
        recent_key = f"settings:{row['id']}"
        results.append(
            Result(
                id=f"settings:{row['id']}",
                title=row["title"],
                subtitle=row["subtitle"],
                category="Settings",
                score=CATEGORY_WEIGHTS["Settings"] + (score or 0) + bonus + context.recent_boosts.get(recent_key, 0),
                action={"type": "settings", "module": row["module"]},
                terms=row["aliases"],
                recent_key=recent_key,
            )
        )

    results.sort(key=lambda result: (-result.score, result.title.lower()))
    return results[:30 if settings_only else 12]
