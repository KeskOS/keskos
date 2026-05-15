from __future__ import annotations

import json
import time
from pathlib import Path

from .models import Result
from .utils import data_home, match_score


class RecentStore:
    def __init__(self) -> None:
        self.path = data_home() / "kesk-runner" / "recent.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.records: dict[str, dict] = self._load()

    def _load(self) -> dict[str, dict]:
        if not self.path.is_file():
            return {}
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        if isinstance(payload, dict):
            return payload
        return {}

    def save(self) -> None:
        self.path.write_text(json.dumps(self.records, ensure_ascii=True, separators=(",", ":")), encoding="utf-8")

    def record(self, result: Result) -> None:
        if not result.recent_key or result.action.get("type") == "command":
            return

        current = self.records.get(result.recent_key, {})
        current.update(
            {
                "title": result.title,
                "subtitle": result.subtitle,
                "category": result.category,
                "action": result.action,
                "copy_value": result.copy_value,
                "dangerous": result.dangerous,
                "recent_key": result.recent_key,
                "count": int(current.get("count", 0)) + 1,
                "updated": int(time.time()),
            }
        )
        self.records[result.recent_key] = current
        self.save()

    def boost_map(self) -> dict[str, int]:
        boosts: dict[str, int] = {}
        now = int(time.time())
        for key, record in self.records.items():
            age_hours = max(0, (now - int(record.get("updated", now))) // 3600)
            freshness = max(0, 72 - age_hours)
            count = int(record.get("count", 1))
            boosts[key] = min(600, freshness * 4 + count * 30)
        return boosts

    def matching_records(self, query: str) -> list[dict]:
        items: list[tuple[int, dict]] = []
        for record in self.records.values():
            score = match_score(query, [record.get("title", ""), record.get("subtitle", ""), record.get("category", "")])
            if score is None:
                continue
            items.append((score + self.boost_map().get(record.get("recent_key", ""), 0), record))
        items.sort(key=lambda item: item[0], reverse=True)
        return [record for _, record in items[:12]]
