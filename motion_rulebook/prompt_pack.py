"""Prompt-pack compiler (layer 2: influence).

Turns a panel spec + rulebook into a paste-ready prompt pack for any video
generator (Runway, Pika, Kling, Luma, Hailuo, Vidu, ...). Closed commercial
tools cannot be hard-constrained, so this layer works by *influence*: every
rule compiles to positive-only natural language that is appended to the
user's motion prompt. The same compilation also emits a verification
checklist for layer 3.

Panel spec (YAML):
    panel:
      id: ep005-pikachu-vs-onix
      scene: "Pewter Gym, rocky arena"
      beat: "Pikachu unleashes Thunderbolt on Onix"
      dialogue:
        - speaker: Ash
          line: "Pikachu, Thunderbolt, now!"
    expansion_points:
      - type: move_depiction
        move: Thunderbolt
        user: Pikachu
      - type: causal_feedback      # effectiveness derived from the type chart
        move_type: electric
        target: Onix
        target_types: [rock, ground]
      - type: vocalization
        speaker: Pikachu

Targets:
    generic - markdown sections; paste into any tool.
    compact - one flowing block for tools with tight prompt limits.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import yaml

from .rulebook import Rulebook
from .type_chart import effectiveness

TARGETS = ("generic", "compact")


@dataclass
class PromptPack:
    text: str
    checks: list[dict] = field(default_factory=list)   # id/question/expected
    matched_rule_ids: list[str] = field(default_factory=list)
    rulebook_name: str = ""
    rulebook_version: str = ""


def load_panel(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict) or "expansion_points" not in data:
        raise ValueError(f"{path}: panel spec needs an 'expansion_points' list")
    return data


def _ground_point(point: dict) -> dict:
    """Derive chart-grounded attributes before rule matching."""
    p = dict(point)
    if (p.get("type") == "causal_feedback"
            and "move_type" in p and "target_types" in p
            and "effectiveness" not in p):
        mult, label = effectiveness(p["move_type"], p["target_types"])
        p["effectiveness"] = label
        p["effectiveness_multiplier"] = mult
    return p


def compile_prompt_pack(rulebook: Rulebook, panel: dict,
                        target: str = "generic") -> PromptPack:
    if target not in TARGETS:
        raise ValueError(f"unknown target {target!r}; choose from {TARGETS}")
    points = [_ground_point(p) for p in panel.get("expansion_points", [])]
    matched: list[tuple[dict, object]] = []
    seen: set[str] = set()
    for p in points:
        for rule in rulebook.match(p):
            if rule.id not in seen:
                seen.add(rule.id)
                matched.append((p, rule))

    info = panel.get("panel", {}) or {}
    beat = info.get("beat", "")
    scene = info.get("scene", "")
    dialogue = info.get("dialogue", []) or []

    if target == "compact":
        text = _render_compact(info, matched, dialogue)
    else:
        text = _render_generic(rulebook, info, matched, dialogue)

    checks = [{"id": r.id,
               "question": r.check["question"],
               "expected": r.check["expected"]} for _, r in matched]
    return PromptPack(
        text=text,
        checks=checks,
        matched_rule_ids=[r.id for _, r in matched],
        rulebook_name=rulebook.name,
        rulebook_version=rulebook.version,
    )


def _render_generic(rulebook: Rulebook, info: dict,
                    matched: list, dialogue: list) -> str:
    L: list[str] = []
    L.append("# PROMPT PACK")
    L.append(f"# panel: {info.get('id', '?')} -- {info.get('beat', '')}")
    L.append(f"# rulebook: {rulebook.name} v{rulebook.version} "
             f"({len(matched)} rules matched)")
    L.append("# Paste everything below the line into your video generator.")
    L.append("")
    L.append("---")
    L.append("")
    L.append("## SCENE")
    scene_bits = [b for b in (info.get("scene"), info.get("beat")) if b]
    L.append((". ".join(scene_bits) + ".") if scene_bits else "")
    L.append("")
    L.append("## CANON RULES -- these must hold in the generated motion")
    for i, (_, rule) in enumerate(matched, 1):
        prov = rule.provenance
        L.append(f"{i}. [{rule.id}] {rule.prompt_text} "
                 f"(canon: {prov.get('canon')}, {prov.get('ref')})")
    if dialogue:
        L.append("")
        L.append("## DIALOGUE / VOCALIZATION")
        for d in dialogue:
            L.append(f"- {d.get('speaker', '?')}: \"{d.get('line', '')}\"")
    L.append("")
    L.append("## VERIFICATION CHECKLIST -- check the generated clip")
    for _, rule in matched:
        L.append(f"- [ ] {rule.id}: {rule.check['question']} "
                 f"(expect: {rule.check['expected']})")
    return "\n".join(L).rstrip() + "\n"


def _render_compact(info: dict, matched: list, dialogue: list) -> str:
    bits = [b for b in (info.get("scene"), info.get("beat")) if b]
    text = ". ".join(bits)
    if text and not text.endswith("."):
        text += "."
    if matched:
        text += " Canon motion rules: " + " ".join(
            r.prompt_text for _, r in matched)
    if dialogue:
        quotes = "; ".join(
            f"{d.get('speaker', '?')}: \"{d.get('line', '')}\"" for d in dialogue)
        text += f" Dialogue: {quotes}."
    return text + "\n"
