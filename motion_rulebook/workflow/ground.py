"""Ground stage: attach official-source provenance to candidates.

Canon rule (project policy): **only official sources count as canon.**
The work itself (episodes, manga volumes) is the primary source for
depiction rules; official sites/publications/game data are secondary.
Fan wikis, forums, and social media are never provenance -- at most they
are discovery leads that point at an official source, which is then cited
directly.

Evidence is supplied as a TSV (human-approved: the human decides what
counts as official):
    candidate_id \\t tier \\t canon \\t ref \\t url \\t quote

Tiers:
    primary   the work itself, e.g. canon=tv-anime ref=EP005 (url optional)
    official  official site/publication/data; url REQUIRED and its domain
              must be on the allowlist below, otherwise the row is rejected.

Output grounded.yaml: candidates with provenance attached (status ->
"grounded") or still "candidate" when no evidence was supplied.
"""
from __future__ import annotations

from urllib.parse import urlparse

import yaml

# Official domains only. Extend per IP; never add fan wikis.
OFFICIAL_DOMAINS = (
    "pokemon.com",
    "assets.pokemon.com",
    "nintendo.com",
    "nintendo.co.jp",
    "gamefreak.co.jp",
    "pokemon.co.jp",
    "tpc-api.pokemon.com",
)


def domain_allowed(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return any(host == d or host.endswith("." + d) for d in OFFICIAL_DOMAINS)


def load_evidence(path: str) -> list[dict]:
    rows = []
    with open(path, encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            line = line.rstrip("\n")
            if not line.strip() or line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) != 6:
                raise ValueError(f"{path}:{i}: need 6 tab-separated columns, "
                                 f"got {len(parts)}")
            cid, tier, canon, ref, url, quote = [p.strip() for p in parts]
            if tier not in ("primary", "official"):
                raise ValueError(f"{path}:{i}: tier must be primary|official")
            if not canon or not ref:
                raise ValueError(f"{path}:{i}: canon and ref are required")
            if tier == "official":
                if not url:
                    raise ValueError(f"{path}:{i}: official tier needs a url")
                if not domain_allowed(url):
                    raise ValueError(
                        f"{path}:{i}: {url!r} is not an official source -- "
                        f"fan wikis and forums can never be provenance")
            rows.append({"candidate_id": cid, "tier": tier, "canon": canon,
                         "ref": ref, "url": url, "quote": quote})
    return rows


def ground_candidates(candidates: list[dict],
                      evidence: list[dict]) -> list[dict]:
    by_id: dict[str, list[dict]] = {}
    for e in evidence:
        by_id.setdefault(e["candidate_id"], []).append(e)
    grounded = []
    for c in candidates:
        c = dict(c)
        prov = by_id.get(c["id"], [])
        if prov:
            c["provenance"] = [
                {"tier": e["tier"], "canon": e["canon"], "ref": e["ref"],
                 **({"url": e["url"]} if e["url"] else {}),
                 **({"quote": e["quote"]} if e["quote"] else {})}
                for e in prov
            ]
            c["status"] = "grounded"
        grounded.append(c)
    return grounded


def write_grounded(grounded: list[dict], path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump({"candidates": grounded}, f,
                       allow_unicode=True, sort_keys=False)
