from __future__ import annotations

from ..models import Result, SearchContext
from ..utils import CATEGORY_WEIGHTS, match_score, normalize_text


POWER_ROWS = [
    {"id": "lock", "title": "Lock Screen", "subtitle": "Lock the current session", "aliases": ["lock", "lockscreen"], "action": {"type": "power", "name": "lock"}, "dangerous": False},
    {"id": "logout", "title": "Log Out", "subtitle": "End the KDE session", "aliases": ["logout", "sign out"], "action": {"type": "power", "name": "logout"}, "dangerous": True},
    {"id": "sleep", "title": "Sleep", "subtitle": "Suspend the system", "aliases": ["sleep", "suspend"], "action": {"type": "power", "name": "suspend"}, "dangerous": True},
    {"id": "hibernate", "title": "Hibernate", "subtitle": "Hibernate the system", "aliases": ["hibernate"], "action": {"type": "power", "name": "hibernate"}, "dangerous": True},
    {"id": "restart", "title": "Restart", "subtitle": "Reboot the machine", "aliases": ["restart", "reboot"], "action": {"type": "power", "name": "reboot"}, "dangerous": True},
    {"id": "shutdown", "title": "Shut Down", "subtitle": "Power off the machine", "aliases": ["shutdown", "poweroff"], "action": {"type": "power", "name": "poweroff"}, "dangerous": True},
]


def search(context: SearchContext, query: str, power_only: bool = False) -> list[Result]:
    results: list[Result] = []
    normalized_query = normalize_text(query)
    for row in POWER_ROWS:
        score = match_score(query, [row["title"], row["subtitle"], *row["aliases"]])
        if query and score is None:
            continue
        bonus = 0
        if normalized_query:
            if normalized_query == normalize_text(row["title"]) or normalized_query in {normalize_text(alias) for alias in row["aliases"]}:
                bonus = 3200
            elif normalize_text(row["title"]).startswith(normalized_query) or any(normalize_text(alias).startswith(normalized_query) for alias in row["aliases"]):
                bonus = 1500
        recent_key = f"power:{row['id']}"
        results.append(
            Result(
                id=f"power:{row['id']}",
                title=row["title"],
                subtitle=row["subtitle"],
                category="Power",
                score=CATEGORY_WEIGHTS["Power"] + (score or 0) + bonus + context.recent_boosts.get(recent_key, 0),
                action=row["action"],
                terms=row["aliases"],
                dangerous=row["dangerous"],
                recent_key=recent_key,
            )
        )

    results.sort(key=lambda result: (-result.score, result.title.lower()))
    return results[:30 if power_only else 10]
