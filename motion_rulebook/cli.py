"""CLI: motion-rulebook compile|rules|check"""
from __future__ import annotations

import argparse
import os

from .prompt_pack import compile_prompt_pack, load_panel, TARGETS
from .rulebook import Rulebook
from .verifier import FakeVLM, run_checks, report_markdown

DEFAULT_RULEBOOK = os.path.join("rulebooks", "pokemon-gen1.yaml")


def _rulebook(path: str) -> Rulebook:
    print(f"Loading rulebook: {path}")
    return Rulebook.load(path)


def cmd_compile(args):
    rb = _rulebook(args.rulebook)
    panel = load_panel(args.panel)
    pack = compile_prompt_pack(rb, panel, target=args.target)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(pack.text)
        print(f"Wrote {args.out} ({len(pack.matched_rule_ids)} rules matched)")
    else:
        print(pack.text)


def cmd_rules(args):
    rb = _rulebook(args.rulebook)
    print(f"{rb.name} v{rb.version} -- {len(rb.rules)} rules")
    for r in rb.rules:
        trig = ", ".join(f"{k}={v}" for k, v in r.trigger.items())
        print(f"  {r.id}  [{trig}]  (canon: {r.provenance.get('canon')})")


def cmd_check(args):
    """Demo the verify step with the deterministic FakeVLM.

    --observe takes id=answer pairs describing what the judge "saw" in the
    clip, e.g.: --observe capture-sequence="the ball shook three times"
    """
    rb = _rulebook(args.rulebook)
    panel = load_panel(args.panel)
    pack = compile_prompt_pack(rb, panel)
    by_id = {c["id"]: c for c in pack.checks}
    observations = {}
    for item in args.observe or []:
        rid, _, answer = item.partition("=")
        rid, answer = rid.strip(), answer.strip()
        if rid in by_id:
            observations[by_id[rid]["question"]] = answer
    results = run_checks(pack.checks, FakeVLM(observations),
                         media_path=args.clip)
    print(report_markdown(results))


def main():
    p = argparse.ArgumentParser(
        prog="motion-rulebook",
        description="Expansion rules for panel-to-animation: compile rulebooks "
                    "into prompt packs, verify generated clips.")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("compile", help="compile a panel spec into a prompt pack")
    s.add_argument("--panel", required=True, help="panel spec YAML")
    s.add_argument("--rulebook", default=DEFAULT_RULEBOOK)
    s.add_argument("--target", choices=TARGETS, default="generic")
    s.add_argument("--out", default="", help="write pack to file instead of stdout")
    s.set_defaults(fn=cmd_compile)

    s = sub.add_parser("rules", help="list rules in a rulebook")
    s.add_argument("--rulebook", default=DEFAULT_RULEBOOK)
    s.set_defaults(fn=cmd_rules)

    s = sub.add_parser("check", help="demo verification with the FakeVLM judge")
    s.add_argument("--panel", required=True, help="panel spec YAML")
    s.add_argument("--rulebook", default=DEFAULT_RULEBOOK)
    s.add_argument("--clip", default="<clip>")
    s.add_argument("--observe", action="append", default=[],
                   help='id=answer pairs, e.g. --observe capture-sequence="shook three times"')
    s.set_defaults(fn=cmd_check)

    args = p.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
