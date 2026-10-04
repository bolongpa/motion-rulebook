# Demo: pokemon-gen1 (end-to-end workflow showcase)

This directory demonstrates the **automated workflow**, not a shipped
product. Nothing here is bundled as "the rulebook" -- the pipeline
produces candidates, a human reviews them into `rulebook.yaml`.

```
corpus/                  input: 7 placeholder panels + metadata
canned_descriptions.json FakeVLM stand-in for the describe stage
                         (real runs: --vlm openai with real panels)
evidence.tsv             human-approved official sources (primary tier:
                         the episodes themselves; fan wikis rejected --
                         see the commented-out row)
out/                     pipeline artifacts: described.jsonl,
                         candidates.yaml, grounded.yaml
rulebook.yaml            the REVIEWED demo output: what a human promotes
                         grounded candidates into
panels/                  demo panel specs for the compile stage
run_demo.sh              the whole loop in one command
```

## Run it

```bash
./demo/pokemon-gen1/run_demo.sh
```

Expected: 4 candidates mined (cheek-pouch glow, golden branching bolts,
three shakes, white flash on click) -- the artist-A-only speed lines and
one-off sparkles are filtered out by the consensus/artist-diversity gates.
All 4 ground against the episodes themselves (primary tier).
