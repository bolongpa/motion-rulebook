"""Mine stage: consensus across instances -> candidate rules.

An observed element becomes a *candidate* only when it is stable across
the corpus:
    support          instances containing it / instances of the event
                     must be >= min_support (default 0.8)
    artist_diversity distinct artists whose instances contain it
                     must be >= min_artists (default 2)

The second condition is the point: it separates canon (stable across
artists/sources) from artist style (one artist's habit). A small or
single-artist corpus cannot produce candidates -- by design.

Output candidates.yaml: one entry per candidate with support counts and
the panel ids behind it. Mining never writes final rules; a human
promotes candidates into a rulebook.
"""
from __future__ import annotations

import re

import yaml

_WS_RE = re.compile(r"\s+")


def normalize(element: str) -> str:
    return _WS_RE.sub(" ", element.strip().lower())


def mine_candidates(described: list[dict], min_support: float = 0.8,
                    min_artists: int = 2) -> list[dict]:
    by_event: dict[str, list[dict]] = {}
    for row in described:
        by_event.setdefault(row["event"], []).append(row)

    candidates = []
    for event, rows in sorted(by_event.items()):
        n = len(rows)
        # element -> {"count": int, "artists": set, "panels": [...], "display": str}
        agg: dict[str, dict] = {}
        for r in rows:
            seen_here = set()
            for el in r.get("elements", []):
                key = normalize(el)
                if not key or key in seen_here:
                    continue
                seen_here.add(key)
                a = agg.setdefault(key, {"count": 0, "artists": set(),
                                         "panels": [], "display": el.strip()})
                a["count"] += 1
                a["artists"].add(r.get("artist", "?"))
                a["panels"].append(r.get("panel_id", "?"))
        for key in sorted(agg):
            a = agg[key]
            support = a["count"] / n
            if support >= min_support and len(a["artists"]) >= min_artists:
                candidates.append({
                    "id": f"cand-{event}-{len(candidates) + 1:02d}",
                    "event": event,
                    "element": a["display"],
                    "support": f"{a['count']}/{n}",
                    "support_ratio": round(support, 3),
                    "artists": sorted(a["artists"]),
                    "panels": a["panels"],
                    "status": "candidate",
                })
    return candidates


def write_candidates(candidates: list[dict], path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump({"candidates": candidates}, f,
                       allow_unicode=True, sort_keys=False)
