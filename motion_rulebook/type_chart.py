"""Gen-1 type effectiveness, bundled as example-domain data.

The prompt-pack compiler uses this to ground causal_feedback expansion
points: given a move type and the target's types, it derives the
effectiveness label (super_effective / neutral / not_very_effective /
immune) from data, then matches the rulebook rule for that label. The
rulebook never has to re-derive the chart, and the chart never has to
know about depiction -- separation of concerns.

This module is intentionally Pokemon-specific: it is *content* for the
reference implementation, not part of the generic engine. Other IPs ship
their own grounding data (or none).
"""
from __future__ import annotations

import json
from pathlib import Path

_CHART: dict = json.loads(
    (Path(__file__).parent / "data" / "type_chart_gen1.json").read_text(
        encoding="utf-8"))
_CHART.pop("_note", None)

LABELS = ("super_effective", "neutral", "not_very_effective", "immune")


def multiplier(attacking: str, defending: str) -> float:
    """Single-type multiplier; unknown types default to 1.0."""
    return _CHART.get(attacking.strip().lower(), {}).get(
        defending.strip().lower(), 1.0)


def effectiveness(attacking: str,
                  defending_types: list[str]) -> tuple[float, str]:
    """(multiplier, label) for an attacking type vs defender type list."""
    m = 1.0
    for d in defending_types:
        m *= multiplier(attacking, d)
    if m == 0:
        label = "immune"
    elif m > 1:
        label = "super_effective"
    elif m < 1:
        label = "not_very_effective"
    else:
        label = "neutral"
    return m, label
