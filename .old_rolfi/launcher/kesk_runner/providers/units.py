from __future__ import annotations

import re

from ..models import Result, SearchContext
from ..utils import CATEGORY_WEIGHTS


CONVERSIONS = {
    ("cm", "inch"): lambda value: value / 2.54,
    ("inch", "cm"): lambda value: value * 2.54,
    ("m", "ft"): lambda value: value * 3.280839895,
    ("ft", "m"): lambda value: value / 3.280839895,
    ("km", "miles"): lambda value: value * 0.6213711922,
    ("miles", "km"): lambda value: value / 0.6213711922,
    ("kg", "lb"): lambda value: value * 2.2046226218,
    ("lb", "kg"): lambda value: value / 2.2046226218,
    ("c", "f"): lambda value: (value * 9.0 / 5.0) + 32.0,
    ("f", "c"): lambda value: (value - 32.0) * 5.0 / 9.0,
    ("gb", "mb"): lambda value: value * 1024.0,
    ("mb", "gb"): lambda value: value / 1024.0,
}

PATTERN = re.compile(
    r"^\s*(-?\d+(?:\.\d+)?)\s*(cm|inch|m|ft|km|miles|kg|lb|c|f|gb|mb)\s+to\s+(inch|cm|ft|m|miles|km|lb|kg|f|c|mb|gb)\s*$",
    re.IGNORECASE,
)


def search(context: SearchContext, query: str) -> list[Result]:
    match = PATTERN.match(query)
    if not match:
        return []

    value = float(match.group(1))
    source = match.group(2).lower()
    target = match.group(3).lower()
    converter = CONVERSIONS.get((source, target))
    if converter is None:
        return []

    converted = converter(value)
    result = f"{converted:.10g} {target}"

    return [
        Result(
            id=f"units:{query}",
            title=result,
            subtitle=f"Units | {value:g} {source} to {target}",
            category="Units",
            score=CATEGORY_WEIGHTS["Units"],
            action={"type": "copy", "value": result},
            copy_value=result,
            terms=[query, result],
        )
    ]
