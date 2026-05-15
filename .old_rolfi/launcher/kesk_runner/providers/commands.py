from __future__ import annotations

from ..models import Result, SearchContext
from ..utils import CATEGORY_WEIGHTS, executable_exists, is_dangerous_command


def search(context: SearchContext, query: str) -> list[Result]:
    stripped = query.strip()
    if not stripped or not executable_exists(stripped):
        return []

    return [
        Result(
            id=f"command:{stripped}",
            title=f"Run {stripped}",
            subtitle="Command in terminal",
            category="Commands",
            score=CATEGORY_WEIGHTS["Commands"],
            action={"type": "command", "command": stripped},
            terms=[stripped],
            dangerous=is_dangerous_command(stripped),
        )
    ]
