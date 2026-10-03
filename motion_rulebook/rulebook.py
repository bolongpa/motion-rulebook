"""Expansion rulebook: user-editable canon depiction rules, stored as data.

Layer 1 of the architecture. A fictional world's rules differ per IP, so they
live in YAML files -- editable without touching the engine. The engine
(prompt-pack compiler + verifier) is generic; each rulebook is per-world
content. Pokemon Gen-1 ships as the reference implementation.

Rule schema:
    meta:
      name: pokemon-gen1-tv        # rulebook identifier
      version: 0.1.0               # versioned: generated video cites this
      canon_priority: [tv-anime, games-gen1]
    rules:
      - id: capture-sequence       # unique
        trigger:                   # subset-matched against an expansion point
          type: event_sequence
          event: capture
        constraint: >-             # human-readable: what must hold
          The ball shakes exactly three times, pauses, then clicks shut.
        prompt_text: >-            # positive-only, injected into video prompts
          The Poke Ball shakes exactly three times, pauses briefly, then
          clicks shut with a bright white flash.
        check:                     # verification: question + expected answer
          question: How many times does the Poke Ball shake before the click?
          expected: three
        provenance:                # every rule cites its canon source
          canon: tv-anime
          ref: "EP001 and standard series depiction"

Expansion point types (where panel->animation must invent):
    move_depiction  - how a move/attack is depicted in motion
    event_sequence  - fixed canonical sequences (capture, faint, evolution)
    causal_feedback - battle consequences (type-effectiveness feedback)
    vocalization    - speech/sound delivery
    continuity      - local continuity between adjacent panels
    offscreen       - invention outside the drawn frame
    disambiguation  - resolving an ambiguous panel
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

import yaml

EXPANSION_POINT_TYPES = frozenset({
    "move_depiction",
    "event_sequence",
    "causal_feedback",
    "vocalization",
    "continuity",
    "offscreen",
    "disambiguation",
})

_REQUIRED_RULE_FIELDS = ("id", "trigger", "constraint", "prompt_text",
                         "check", "provenance")

# Whole-word negation markers. Prompt text is injected into video-diffusion
# prompts, whose text encoders handle negation badly ("no wings" can
# *increase* the chance of wings) -- so injected text stays positive-only.
_NEGATION_RE = re.compile(
    r"\b(no|not|without|never|none|neither|nor|cannot|can't|don't|doesn't|"
    r"lack|lacking|devoid|free of|zero)\b", re.IGNORECASE)


def assert_no_negations(text: str) -> None:
    m = _NEGATION_RE.search(text)
    if m:
        raise ValueError(f"prompt text contains negation: {m.group(0)!r} in {text!r}")


@dataclass
class Rule:
    id: str
    trigger: dict
    constraint: str
    prompt_text: str
    check: dict = field(default_factory=dict)
    provenance: dict = field(default_factory=dict)

    def __post_init__(self):
        if not self.id or not isinstance(self.id, str):
            raise ValueError("rule needs a non-empty string id")
        if not isinstance(self.trigger, dict) or "type" not in self.trigger:
            raise ValueError(
                f"rule {self.id!r}: trigger must be a dict with a 'type' key")
        if self.trigger["type"] not in EXPANSION_POINT_TYPES:
            raise ValueError(
                f"rule {self.id!r}: unknown expansion point type "
                f"{self.trigger['type']!r}; must be one of "
                f"{sorted(EXPANSION_POINT_TYPES)}")
        if not self.constraint or not self.prompt_text:
            raise ValueError(
                f"rule {self.id!r}: constraint and prompt_text are required")
        assert_no_negations(self.prompt_text)
        for key in ("question", "expected"):
            if key not in self.check:
                raise ValueError(f"rule {self.id!r}: check needs {key!r}")
        for key in ("canon", "ref"):
            if key not in self.provenance:
                raise ValueError(f"rule {self.id!r}: provenance needs {key!r}")

    def matches(self, point: dict) -> bool:
        """True when every trigger key/value equals the point's (subset match)."""
        return all(point.get(k) == v for k, v in self.trigger.items())


class Rulebook:
    """A loaded, validated rulebook."""

    def __init__(self, meta: dict, rules: list[Rule]):
        self.meta = meta
        self.rules = rules
        self._by_id = {r.id: r for r in rules}

    @property
    def name(self) -> str:
        return self.meta.get("name", "unnamed")

    @property
    def version(self) -> str:
        return self.meta.get("version", "0.1.0")

    @classmethod
    def load(cls, path: str) -> "Rulebook":
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if not isinstance(data, dict) or "rules" not in data:
            raise ValueError(f"{path}: rulebook needs a top-level 'rules' list")
        meta = data.get("meta") or {}
        rules, seen = [], set()
        for raw in data["rules"]:
            for field_name in _REQUIRED_RULE_FIELDS:
                if field_name not in raw:
                    raise ValueError(
                        f"{path}: rule missing {field_name!r}: {raw!r}")
            rule = Rule(
                id=raw["id"],
                trigger=raw["trigger"],
                constraint=raw["constraint"],
                prompt_text=raw["prompt_text"],
                check=raw["check"],
                provenance=raw["provenance"],
            )
            if rule.id in seen:
                raise ValueError(f"{path}: duplicate rule id {rule.id!r}")
            seen.add(rule.id)
            rules.append(rule)
        return cls(meta, rules)

    def get(self, rule_id: str) -> Rule:
        return self._by_id[rule_id]

    def match(self, point: dict) -> list[Rule]:
        """Rules whose trigger matches this expansion point, in file order."""
        return [r for r in self.rules if r.matches(point)]
