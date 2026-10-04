#!/bin/bash
# End-to-end demo of the mining workflow (FakeVLM mechanics demo).
# Real runs: replace --vlm fake --canned ... with --vlm openai and real panels.
set -e
cd "$(dirname "$0")/../.."
D=demo/pokemon-gen1
mkdir -p $D/out

python -m motion_rulebook.cli describe --corpus $D/corpus \
    --out $D/out/described.jsonl --vlm fake --canned $D/canned_descriptions.json
python -m motion_rulebook.cli mine --described $D/out/described.jsonl \
    --out $D/out/candidates.yaml
python -m motion_rulebook.cli ground --candidates $D/out/candidates.yaml \
    --evidence $D/evidence.tsv --out $D/out/grounded.yaml

echo
echo "=== grounded candidates: a human promotes these into rulebook.yaml ==="
cat $D/out/grounded.yaml
echo
echo "=== prompt pack compiled from the reviewed rulebook ==="
python -m motion_rulebook.cli compile --panel $D/panels/panel_pikachu_vs_onix.yaml \
    --rulebook $D/rulebook.yaml --target compact \
    --grounder motion_rulebook.type_chart:grounder
