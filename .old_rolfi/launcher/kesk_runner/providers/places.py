from __future__ import annotations

from pathlib import Path

from ..models import Result, SearchContext
from ..utils import CATEGORY_WEIGHTS, match_score


def _place_rows(home: Path) -> list[dict]:
    return [
        {"id": "home", "title": "Home", "subtitle": str(home), "target": str(home), "prefer_dolphin": True, "terms": ["home", "folder", str(home)]},
        {"id": "desktop", "title": "Desktop", "subtitle": str(home / "Desktop"), "target": str(home / "Desktop"), "prefer_dolphin": True, "terms": ["desktop"]},
        {"id": "downloads", "title": "Downloads", "subtitle": str(home / "Downloads"), "target": str(home / "Downloads"), "prefer_dolphin": True, "terms": ["downloads"]},
        {"id": "documents", "title": "Documents", "subtitle": str(home / "Documents"), "target": str(home / "Documents"), "prefer_dolphin": True, "terms": ["documents", "docs"]},
        {"id": "pictures", "title": "Pictures", "subtitle": str(home / "Pictures"), "target": str(home / "Pictures"), "prefer_dolphin": True, "terms": ["pictures", "images", "photos"]},
        {"id": "videos", "title": "Videos", "subtitle": str(home / "Videos"), "target": str(home / "Videos"), "prefer_dolphin": True, "terms": ["videos", "movies"]},
        {"id": "music", "title": "Music", "subtitle": str(home / "Music"), "target": str(home / "Music"), "prefer_dolphin": True, "terms": ["music", "audio"]},
        {"id": "trash", "title": "Trash", "subtitle": "trash:/", "target": "trash:/", "prefer_dolphin": False, "terms": ["trash", "bin", "recycle"]},
        {"id": "network", "title": "Network", "subtitle": "network:/", "target": "network:/", "prefer_dolphin": False, "terms": ["network", "shares", "smb"]},
    ]


def search(context: SearchContext, query: str) -> list[Result]:
    results: list[Result] = []
    for row in _place_rows(context.home):
        score = match_score(query, [row["title"], row["subtitle"], *row["terms"]])
        if query and score is None:
            continue

        recent_key = f"place:{row['id']}"
        results.append(
            Result(
                id=f"place:{row['id']}",
                title=row["title"],
                subtitle=row["subtitle"],
                category="Places",
                score=CATEGORY_WEIGHTS["Places"] + (score or 0) + context.recent_boosts.get(recent_key, 0),
                action={
                    "type": "path",
                    "path": row["target"],
                    "prefer_dolphin": row["prefer_dolphin"],
                },
                terms=row["terms"],
                recent_key=recent_key,
            )
        )

    results.sort(key=lambda result: (-result.score, result.title.lower()))
    return results[:15]
