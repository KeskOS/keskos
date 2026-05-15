from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class SearchContext:
    mode: str
    query: str
    session_type: str
    home: Path
    cache_dir: Path
    data_dir: Path
    recent_boosts: dict[str, int]


@dataclass(slots=True)
class Result:
    id: str
    title: str
    subtitle: str
    category: str
    score: int
    action: dict[str, Any]
    terms: list[str] = field(default_factory=list)
    icon: str | None = None
    copy_value: str | None = None
    dangerous: bool = False
    urgent: bool = False
    active: bool = False
    nonselectable: bool = False
    permanent: bool = False
    recent_key: str | None = None


@dataclass(slots=True)
class ActionOutcome:
    close_rofi: bool = True
    switch_mode: str | None = None
    message: str | None = None
    copied: bool = False
