# motion-rulebook

**Panel pins WHAT. The rulebook constrains HOW.**

Turning a manga panel into animation forces the generator to *invent*
information: the panel is one frozen frame, the animation needs motion
breakdown, between-panel fill, vocalization, off-frame content. An
**expansion rule** constrains exactly that invented information so it stays
true to the fictional world's canon.

`motion-rulebook` is the **automated workflow** for producing and applying
expansion rules. Every stage writes files for human review -- mining only
ever proposes *candidates*; humans promote them into canon.

## The workflow

```
corpus/  (user-submitted panels: image + event + artist + source)
  --describe-->  described.jsonl   (VLM documents observable elements)
  --mine------>  candidates.yaml   (consensus across instances;
                                    support >= 0.8 AND >= 2 artists)
  --ground---->  grounded.yaml     (official-source provenance ONLY;
                                    fan wikis rejected, never provenance)
  --human-->     rulebook.yaml     (reviewed, versioned, per-world content)
  --compile--->  prompt-pack.txt   (paste into any video generator)
  --check----->  verification report (VLM/human checklist per rule)
```

**Canon policy:** only official sources count as canon. The work itself
(episodes, manga volumes) is the primary source for depiction rules;
official sites/publications/game data are secondary. Fan wikis are at most
discovery leads -- they can never appear in provenance. The miner's
consensus gates (support threshold + artist diversity) separate canon
(stable across artists) from artist style.

**Honest boundary:** closed video tools (Runway, Pika, Kling, Luma,
Hailuo, Vidu, ...) cannot be hard-constrained. The workflow works by
*influence* (rule -> positive-only prompt text) + *verify* (checklist ->
judge -> bounded retry).

## Quickstart

```bash
pip install -r requirements.txt

# 1-3. mine candidates from a corpus (FakeVLM demo; real: --vlm openai)
motion-rulebook describe --corpus demo/pokemon-gen1/corpus \
    --out described.jsonl --vlm fake \
    --canned demo/pokemon-gen1/canned_descriptions.json
motion-rulebook mine --described described.jsonl --out candidates.yaml
motion-rulebook ground --candidates candidates.yaml \
    --evidence demo/pokemon-gen1/evidence.tsv --out grounded.yaml

# 4. human promotes grounded candidates into rulebooks/<world>.yaml,
#    then compile a prompt pack for any video tool:
motion-rulebook compile --panel demo/pokemon-gen1/panels/panel_pikachu_vs_onix.yaml \
    --rulebook demo/pokemon-gen1/rulebook.yaml --target compact \
    --grounder motion_rulebook.type_chart:grounder

# one-command end-to-end demo:
./demo/pokemon-gen1/run_demo.sh
```

## Layout

- `motion_rulebook/` -- generic engine (no IP-specific content):
  `rulebook.py` (schema/loader/matcher), `workflow/` (corpus/describe/
  mine/ground), `prompt_pack.py` (generic/compact compiler),
  `verifier.py` (checklist runner), `type_chart.py` (example grounding
  plugin: Gen-1 chart, kept as demo content), `cli.py`.
- `rulebooks/` -- generated rulebooks live here (not shipped; see its README).
- `demo/pokemon-gen1/` -- end-to-end demo: corpus -> candidates ->
  reviewed `rulebook.yaml` -> prompt packs. The demo proves the workflow;
  it is not the product.

## Rule schema

```yaml
- id: capture-sequence
  trigger: {type: event_sequence, event: capture}  # subset-matched
  constraint: "human-readable: what must hold"
  prompt_text: "positive-only, injected into video prompts"
  check: {question: "...", expected: "..."}       # verification
  provenance: {canon: tv-anime, ref: "EP003"}     # official only
```

Expansion point types: `move_depiction`, `event_sequence`,
`causal_feedback`, `vocalization`, `continuity`, `offscreen`,
`disambiguation`.

## Roadmap

- Panel-spec auto-extraction (VLM -> beat/cast/expansion points, human confirms)
- API harness: generate -> verify -> retry for hosted video APIs
- ComfyUI nodes (the one place true hard constraints are possible)
- More grounding plugins (other IPs' official sources)

## License

MIT
