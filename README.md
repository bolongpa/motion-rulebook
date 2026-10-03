# motion-rulebook

**Panel pins WHAT. The rulebook constrains HOW.**

Turning a manga panel into animation forces the generator to *invent*
information: the panel is one frozen frame, the animation needs motion
breakdown, between-panel fill, vocalization, off-frame content. An
**expansion rule** constrains exactly that invented information so it stays
true to the fictional world's canon.

`motion-rulebook` is the toolkit for authoring and applying expansion rules:

1. **Rulebook (user-editable data).** Canon depiction rules as YAML -- one
   rule = trigger + constraint + `prompt_text` + `check` + provenance.
   The engine is generic; each rulebook is per-world content. Pokemon Gen-1
   ships as the reference implementation (`rulebooks/pokemon-gen1.yaml`).
2. **Prompt-pack compiler (influence).** Closed video tools (Runway, Pika,
   Kling, Luma, Hailuo, Vidu, ...) can't be hard-constrained, so each rule
   compiles to positive-only natural language appended to your motion
   prompt. Copy-paste into any tool -- no API key needed.
3. **Verifier (verify).** Every rule also carries a `check`
   (question + expected answer) forming a verification checklist for the
   generated clip. v1 ships a deterministic `FakeVLM` judge; the
   generate -> verify -> retry loop against real video APIs is roadmap.

## Quickstart

```bash
pip install -r requirements.txt

# list the reference rules
motion-rulebook rules

# compile a panel into a prompt pack (paste into any video generator)
motion-rulebook compile --panel examples/pokemon-gen1/panel_pikachu_vs_onix.yaml

# compact single-block variant for tight prompt limits
motion-rulebook compile --panel examples/pokemon-gen1/panel_capture_caterpie.yaml \
    --target compact

# demo the verify step
motion-rulebook check --panel examples/pokemon-gen1/panel_capture_caterpie.yaml \
    --observe capture-sequence="the ball shook three times, then clicked"
```

## How it works

A panel spec declares its **expansion points** -- the places where
panel->animation must invent:

| type | invents... |
|---|---|
| `move_depiction` | how an attack looks in motion |
| `event_sequence` | fixed canonical sequences (capture, faint, evolution) |
| `causal_feedback` | battle consequences; effectiveness derived from data |
| `vocalization` | speech/sound delivery |
| `continuity` | local continuity between adjacent panels |
| `offscreen` | invention outside the drawn frame |
| `disambiguation` | resolving an ambiguous panel |

The compiler subset-matches each point against rule triggers. For
`causal_feedback` points the Gen-1 type chart (bundled data) derives the
effectiveness label first -- e.g. Electric vs Onix (Rock/Ground) resolves to
`immune`, selecting the immune depiction rule purely from data (the famous
EP005 moment), with no depiction logic hardcoded in the engine.

## Write your own rulebook

Fork `rulebooks/pokemon-gen1.yaml`. Keep the schema; replace the rules.
Every rule needs `id`, `trigger`, `constraint`, `prompt_text`
(positive-only -- negations backfire in diffusion text encoders),
`check.question` / `check.expected`, and `provenance.canon` / `provenance.ref`.
Rulebooks are versioned; generated video should cite the version used.

## Roadmap

- API harness: generate -> verify -> retry loop for Runway/Pika/Kling/Luma/Hailuo/Vidu
- ComfyUI nodes (the one place true hard constraints are possible)
- More reference rulebooks (other IPs, original works)

## License

MIT
