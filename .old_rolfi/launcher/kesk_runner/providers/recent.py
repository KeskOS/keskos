from __future__ import annotations

from ..models import Result, SearchContext
from ..recent import RecentStore
from ..utils import CATEGORY_WEIGHTS


def search(context: SearchContext, query: str, store: RecentStore) -> list[Result]:
    if not query.strip():
        return []

    results: list[Result] = []
    for record in store.matching_records(query):
        action = record.get("action")
        if not isinstance(action, dict):
            continue
        results.append(
            Result(
                id=f"recent:{record.get('recent_key', record.get('title', 'item'))}",
                title=record.get("title", "Recent item"),
                subtitle=record.get("subtitle", ""),
                category="Recent",
                score=CATEGORY_WEIGHTS["Recent"] + context.recent_boosts.get(record.get("recent_key", ""), 0),
                action=action,
                copy_value=record.get("copy_value"),
                dangerous=bool(record.get("dangerous")),
                recent_key=record.get("recent_key"),
                terms=[record.get("title", ""), record.get("subtitle", ""), record.get("category", "")],
            )
        )

    return results[:10]
