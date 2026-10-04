"""CLI: motion-rulebook describe|mine|ground|compile|rules|check"""
from __future__ import annotations

import argparse
import json
import os

from .prompt_pack import compile_prompt_pack, load_panel, TARGETS
from .rulebook import Rulebook
from .verifier import FakeVLM, run_checks, report_markdown
from .workflow.corpus import load_corpus
from .workflow.describe import describe_corpus
from .workflow.vlm import FakeVisionModel, OpenAICompatibleVisionModel
from .workflow.mine import mine_candidates, write_candidates
from .workflow.describe import load_described
from .workflow.ground import load_evidence, ground_candidates, write_grounded


def _rulebook(path: str) -> Rulebook:
    print(f"Loading rulebook: {path}")
    return Rulebook.load(path)


def cmd_describe(args):
    items = load_corpus(args.corpus)
    print(f"Corpus: {len(items)} panels")
    if args.vlm == "fake":
        with open(args.canned, encoding="utf-8") as f:
            vlm = FakeVisionModel(json.load(f))
    else:
        vlm = OpenAICompatibleVisionModel(model=args.model)
    rows = describe_corpus(items, vlm, args.out)
    print(f"Wrote {args.out} ({len(rows)} described)")


def cmd_mine(args):
    described = load_described(args.described)
    cands = mine_candidates(described, min_support=args.min_support,
                            min_artists=args.min_artists)
    write_candidates(cands, args.out)
    print(f"Wrote {args.out} ({len(cands)} candidates)")
    for c in cands:
        print(f"  {c['id']} [{c['event']}] support={c['support']} "
              f"artists={len(c['artists'])}: {c['element'][:70]}")


def cmd_ground(args):
    import yaml
    with open(args.candidates, encoding="utf-8") as f:
        cands = yaml.safe_load(f)["candidates"]
    evidence = load_evidence(args.evidence)
    grounded = ground_candidates(cands, evidence)
    write_grounded(grounded, args.out)
    n = sum(1 for c in grounded if c["status"] == "grounded")
    print(f"Wrote {args.out} ({n}/{len(grounded)} grounded)")


def _load_grounder(spec: str):
    mod_name, _, attr = spec.partition(":")
    if not attr:
        raise ValueError(f"--grounder must be module:attr, got {spec!r}")
    import importlib
    mod = importlib.import_module(mod_name)
    fn = getattr(mod, attr)
    if not callable(fn):
        raise ValueError(f"--grounder {spec!r} is not callable")
    return fn


def cmd_compile(args):
    rb = _rulebook(args.rulebook)
    panel = load_panel(args.panel)
    grounders = [_load_grounder(s) for s in args.grounder or []]
    pack = compile_prompt_pack(rb, panel, target=args.target,
                               grounders=grounders)
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
    s.add_argument("--rulebook", required=True, help="rulebook YAML (generate via the mine workflow)")
    s.add_argument("--target", choices=TARGETS, default="generic")
    s.add_argument("--out", default="", help="write pack to file instead of stdout")
    s.add_argument("--grounder", action="append", default=[],
                   help="per-world grounding hook as module:attr, e.g. "
                        "motion_rulebook.type_chart:grounder")
    s.set_defaults(fn=cmd_compile)

    s = sub.add_parser("rules", help="list rules in a rulebook")
    s.add_argument("--rulebook", required=True, help="rulebook YAML (generate via the mine workflow)")
    s.set_defaults(fn=cmd_rules)

    s = sub.add_parser("check", help="demo verification with the FakeVLM judge")
    s.add_argument("--panel", required=True, help="panel spec YAML")
    s.add_argument("--rulebook", required=True, help="rulebook YAML (generate via the mine workflow)")
    s.add_argument("--clip", default="<clip>")
    s.add_argument("--observe", action="append", default=[],
                   help='id=answer pairs, e.g. --observe capture-sequence="shook three times"')
    s.set_defaults(fn=cmd_check)

    _add_workflow_parsers(sub)

    args = p.parse_args()
    args.fn(args)


def _add_workflow_parsers(sub):
    s = sub.add_parser("describe",
                       help="VLM-documents each corpus panel -> described.jsonl")
    s.add_argument("--corpus", required=True, help="corpus dir (corpus.yaml + img/)")
    s.add_argument("--out", required=True, help="output described.jsonl")
    s.add_argument("--vlm", choices=["fake", "openai"], default="fake")
    s.add_argument("--canned", default="",
                   help="canned descriptions JSON for --vlm fake")
    s.add_argument("--model", default="gpt-4o",
                   help="vision model for --vlm openai")
    s.set_defaults(fn=cmd_describe)

    s = sub.add_parser("mine",
                       help="consensus mining: described.jsonl -> candidates.yaml")
    s.add_argument("--described", required=True)
    s.add_argument("--out", required=True, help="output candidates.yaml")
    s.add_argument("--min-support", type=float, default=0.8)
    s.add_argument("--min-artists", type=int, default=2)
    s.set_defaults(fn=cmd_mine)

    s = sub.add_parser("ground",
                       help="attach official-source provenance -> grounded.yaml")
    s.add_argument("--candidates", required=True)
    s.add_argument("--evidence", required=True,
                   help="TSV: candidate_id, tier, canon, ref, url, quote")
    s.add_argument("--out", required=True, help="output grounded.yaml")
    s.set_defaults(fn=cmd_ground)


if __name__ == "__main__":
    main()
