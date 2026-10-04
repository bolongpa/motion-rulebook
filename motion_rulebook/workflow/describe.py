"""Describe stage: VLM documents every corpus panel -> described.jsonl.

One JSON object per line:
    {"panel_id", "event", "artist", "source", "actors", "elements", "note"}
This file is the raw material for mining. Human-readable, diffable, and
re-runnable: if the describe prompt improves, delete and re-run.
"""
from __future__ import annotations

import json

from .corpus import CorpusItem
from .vlm import VisionModel


def describe_corpus(items: list[CorpusItem], vlm: VisionModel,
                    out_path: str) -> list[dict]:
    rows = []
    for item in items:
        d = vlm.describe(item.image, item.event)
        rows.append({
            "panel_id": item.id,
            "event": item.event,
            "artist": item.artist,
            "source": item.source,
            "actors": list(d.get("actors", [])),
            "elements": list(d.get("elements", [])),
            "note": d.get("note", ""),
        })
    with open(out_path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return rows


def load_described(path: str) -> list[dict]:
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows
