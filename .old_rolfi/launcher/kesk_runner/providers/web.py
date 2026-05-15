from __future__ import annotations

import urllib.parse

from ..models import Result, SearchContext
from ..utils import CATEGORY_WEIGHTS, looks_like_url, normalize_url


SHORTCUTS = {
    "gg": "https://www.google.com/search?q={query}",
    "google": "https://www.google.com/search?q={query}",
    "ddg": "https://duckduckgo.com/?q={query}",
    "duck": "https://duckduckgo.com/?q={query}",
    "yt": "https://www.youtube.com/results?search_query={query}",
    "youtube": "https://www.youtube.com/results?search_query={query}",
    "wiki": "https://en.wikipedia.org/wiki/Special:Search?search={query}",
}


def search(context: SearchContext, query: str) -> list[Result]:
    stripped = query.strip()
    if not stripped:
        return []

    if looks_like_url(stripped):
        target = normalize_url(stripped)
        return [
            Result(
                id=f"url:{target}",
                title=target,
                subtitle="Open URL",
                category="Web",
                score=CATEGORY_WEIGHTS["Web"] + 400,
                action={"type": "web", "url": target},
                terms=[stripped, target],
                recent_key=f"web:{target}",
            )
        ]

    parts = stripped.split(maxsplit=1)
    if not parts:
        return []

    shortcut = parts[0].lower()
    if shortcut not in SHORTCUTS or len(parts) < 2:
        return []

    subject = parts[1].strip()
    target = SHORTCUTS[shortcut].format(query=urllib.parse.quote_plus(subject))
    service = {
        "gg": "Google",
        "google": "Google",
        "ddg": "DuckDuckGo",
        "duck": "DuckDuckGo",
        "yt": "YouTube",
        "youtube": "YouTube",
        "wiki": "Wikipedia",
    }[shortcut]

    recent_key = f"web:{shortcut}:{subject.lower()}"
    return [
        Result(
            id=f"web:{shortcut}:{subject}",
            title=f"Search {service} for {subject}",
            subtitle=target,
            category="Web",
            score=CATEGORY_WEIGHTS["Web"] + 250 + context.recent_boosts.get(recent_key, 0),
            action={"type": "web", "url": target},
            terms=[shortcut, subject, service],
            recent_key=recent_key,
        )
    ]
