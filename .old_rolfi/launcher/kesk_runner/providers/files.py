from __future__ import annotations

from ..cache import load_file_cache
from ..models import Result, SearchContext
from ..utils import CATEGORY_WEIGHTS, match_score


def search(context: SearchContext, query: str) -> list[Result]:
    file_items, stale = load_file_cache(sync_if_missing=False)
    if not query.strip():
        return []

    if not file_items:
        return [
            Result(
                id="files:indexing",
                title="Indexing common folders",
                subtitle="Open the launcher again in a moment for file results.",
                category="Files",
                score=50,
                action={"type": "noop"},
                nonselectable=True,
                permanent=True,
            )
        ]

    results: list[Result] = []
    for item in file_items:
        search_terms = [item["name"], item["relative"]]
        score = match_score(query, search_terms)
        if score is None:
            continue

        recent_key = f"file:{item['path']}"
        subtitle = item["relative"]
        if stale:
            subtitle += " | cache refreshing"

        results.append(
            Result(
                id=f"file:{item['path']}",
                title=item["name"],
                subtitle=subtitle,
                category="Files",
                score=CATEGORY_WEIGHTS["Files"] + score + context.recent_boosts.get(recent_key, 0),
                action={
                    "type": "path",
                    "path": item["path"],
                    "prefer_dolphin": bool(item["is_dir"]),
                },
                terms=search_terms,
                recent_key=recent_key,
            )
        )

    results.sort(key=lambda result: (-result.score, result.title.lower()))
    return results[:25]
