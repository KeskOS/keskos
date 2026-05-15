from __future__ import annotations

from ..cache import load_app_cache
from ..models import Result, SearchContext
from ..utils import CATEGORY_WEIGHTS, match_score


def search(context: SearchContext, query: str, apps_only: bool = False) -> list[Result]:
    app_items, _ = load_app_cache(sync_if_missing=True)
    results: list[Result] = []

    for item in app_items:
        search_terms = [
            item.get("name", ""),
            item.get("generic_name", ""),
            item.get("comment", ""),
            item.get("exec", ""),
            " ".join(item.get("categories", [])),
        ]

        score = match_score(query, search_terms)
        if query and score is None:
            continue

        recent_key = f"app:{item['desktop_id']}"
        total = CATEGORY_WEIGHTS["Apps"] + (score or 0) + context.recent_boosts.get(recent_key, 0)
        subtitle_bits = [item.get("generic_name", ""), item.get("comment", "")]
        subtitle = " | ".join(bit for bit in subtitle_bits if bit).strip() or "Desktop application"

        results.append(
            Result(
                id=f"app:{item['desktop_id']}",
                title=item["name"],
                subtitle=subtitle,
                category="Apps",
                score=total,
                action={
                    "type": "app",
                    "desktop_id": item["desktop_id"],
                    "exec": item.get("exec", ""),
                },
                terms=search_terms,
                icon=item.get("icon") or None,
                recent_key=recent_key,
            )
        )

    results.sort(key=lambda result: (-result.score, result.title.lower()))
    limit = 80 if apps_only else 40
    return results[:limit]
