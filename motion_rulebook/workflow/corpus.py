"""Corpus: user-submitted panels for rule mining.

Layout:
    corpus/
      corpus.yaml      # items: [{id, image, event, artist, source}]
      img/...

Each item pins one *instance* of an event (e.g. one Thunderbolt depiction).
Diversity matters: the same event should come from different artists and
sources, so mining can separate canon (stable across artists) from artist
style. Metadata is required -- an unlabeled image teaches nothing.
"""
from __future__ import annotations

from dataclasses import dataclass

import yaml


@dataclass
class CorpusItem:
    id: str
    image: str   # path to the panel image, relative to the corpus dir
    event: str   # event label, e.g. "move_thunderbolt", "event_capture"
    artist: str  # who drew it -- diversity across artists is the point
    source: str  # where it's from, e.g. "EP005", "manga ch.12"


def load_corpus(corpus_dir: str) -> list[CorpusItem]:
    import os
    spec = os.path.join(corpus_dir, "corpus.yaml")
    with open(spec, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict) or "items" not in data:
        raise ValueError(f"{spec}: needs an 'items' list")
    items, seen = [], set()
    for raw in data["items"]:
        for key in ("id", "image", "event", "artist", "source"):
            if not raw.get(key):
                raise ValueError(f"{spec}: item missing {key!r}: {raw!r}")
        if raw["id"] in seen:
            raise ValueError(f"{spec}: duplicate item id {raw['id']!r}")
        seen.add(raw["id"])
        img = raw["image"] if os.path.isabs(raw["image"]) \
            else os.path.join(corpus_dir, raw["image"])
        if not os.path.isfile(img):
            raise ValueError(f"{spec}: image not found: {img}")
        items.append(CorpusItem(id=raw["id"], image=img, event=raw["event"],
                                artist=raw["artist"], source=raw["source"]))
    if not items:
        raise ValueError(f"{spec}: corpus is empty")
    return items
