"""Workflow: corpus -> describe -> mine -> ground."""
import json
import os

import pytest
import yaml

from motion_rulebook.workflow.corpus import load_corpus
from motion_rulebook.workflow.describe import describe_corpus, load_described
from motion_rulebook.workflow.vlm import FakeVisionModel
from motion_rulebook.workflow.mine import mine_candidates, normalize
from motion_rulebook.workflow.ground import (
    load_evidence, ground_candidates, domain_allowed,
)

DEMO = os.path.join(os.path.dirname(__file__), "..", "demo", "pokemon-gen1")


def _row(event, artist, pid, elements):
    return {"panel_id": pid, "event": event, "artist": artist,
            "source": "EPX", "actors": [], "elements": elements, "note": ""}


# ---- corpus ----

def test_demo_corpus_loads():
    items = load_corpus(os.path.join(DEMO, "corpus"))
    assert len(items) == 7
    assert {i.event for i in items} == {"move_thunderbolt", "event_capture"}


def test_corpus_rejects_duplicate_id(tmp_path):
    (tmp_path / "img.png").write_bytes(b"x")
    spec = {"items": [
        {"id": "a", "image": "img.png", "event": "e",
         "artist": "A", "source": "S"},
        {"id": "a", "image": "img.png", "event": "e",
         "artist": "B", "source": "S"},
    ]}
    (tmp_path / "corpus.yaml").write_text(yaml.safe_dump(spec))
    with pytest.raises(ValueError, match="duplicate item id"):
        load_corpus(str(tmp_path))


def test_corpus_rejects_missing_image(tmp_path):
    spec = {"items": [{"id": "a", "image": "nope.png", "event": "e",
                       "artist": "A", "source": "S"}]}
    (tmp_path / "corpus.yaml").write_text(yaml.safe_dump(spec))
    with pytest.raises(ValueError, match="image not found"):
        load_corpus(str(tmp_path))


# ---- describe ----

def test_describe_writes_jsonl(tmp_path):
    items = load_corpus(os.path.join(DEMO, "corpus"))
    canned = json.load(open(os.path.join(DEMO, "canned_descriptions.json")))
    out = str(tmp_path / "d.jsonl")
    rows = describe_corpus(items, FakeVisionModel(canned), out)
    assert len(rows) == 7
    assert load_described(out) == rows
    assert all(r["elements"] for r in rows)


def test_fake_vlm_unknown_panel():
    with pytest.raises(KeyError):
        FakeVisionModel({}).describe("/x/unknown.png", "e")


# ---- mine ----

def test_consensus_and_artist_gates():
    described = [
        _row("e", "A", "p1", ["shared across all", "artist-A habit", "rare one"]),
        _row("e", "A", "p2", ["shared across all", "artist-A habit"]),
        _row("e", "B", "p3", ["shared across all"]),
        _row("e", "B", "p4", ["Shared Across All"]),  # normalization merge
    ]
    cands = mine_candidates(described)
    got = {c["element"] for c in cands}
    assert got == {"shared across all"}  # habit fails artist gate, rare fails support
    c = cands[0]
    assert c["support"] == "4/4" and c["artists"] == ["A", "B"]


def test_mine_needs_diverse_corpus():
    described = [_row("e", "A", f"p{i}", ["only artist A"]) for i in range(5)]
    assert mine_candidates(described) == []


def test_demo_corpus_mines_four_candidates():
    items = load_corpus(os.path.join(DEMO, "corpus"))
    canned = json.load(open(os.path.join(DEMO, "canned_descriptions.json")))
    rows = describe_corpus(items, FakeVisionModel(canned), "/dev/null")
    cands = mine_candidates(rows)
    assert [c["id"] for c in cands] == [
        "cand-event_capture-01", "cand-event_capture-02",
        "cand-move_thunderbolt-03", "cand-move_thunderbolt-04"]
    assert all(c["support_ratio"] == 1.0 for c in cands)


# ---- ground ----

def test_official_domains_allowed():
    assert domain_allowed("https://www.pokemon.com/us/pokedex")
    assert domain_allowed("https://assets.pokemon.com/x.png")
    assert not domain_allowed("https://bulbapedia.bulbagarden.net/wiki/X")
    assert not domain_allowed("https://reddit.com/r/pokemon")


def test_ground_rejects_fan_wiki(tmp_path):
    p = tmp_path / "ev.tsv"
    p.write_text("c1\tofficial\tfan-wiki\tbulbapedia\t"
                 "https://bulbapedia.bulbagarden.net/wiki/X\tq\n")
    with pytest.raises(ValueError, match="not an official source"):
        load_evidence(str(p))


def test_ground_rejects_official_without_url(tmp_path):
    p = tmp_path / "ev.tsv"
    p.write_text("c1\tofficial\tpokemon.com\tref\t\tq\n")
    with pytest.raises(ValueError, match="needs a url"):
        load_evidence(str(p))


def test_ground_primary_needs_no_url(tmp_path):
    p = tmp_path / "ev.tsv"
    p.write_text("c1\tprimary\ttv-anime\tEP005\t\tcheeks glow\n")
    ev = load_evidence(str(p))
    out = ground_candidates([{"id": "c1", "status": "candidate"}], ev)
    assert out[0]["status"] == "grounded"
    assert out[0]["provenance"][0]["tier"] == "primary"


def test_ground_leaves_unevidenced_as_candidate():
    out = ground_candidates([{"id": "c1", "status": "candidate"}], [])
    assert out[0]["status"] == "candidate"
    assert "provenance" not in out[0]


def test_demo_evidence_grounds_all(tmp_path):
    items = load_corpus(os.path.join(DEMO, "corpus"))
    canned = json.load(open(os.path.join(DEMO, "canned_descriptions.json")))
    rows = describe_corpus(items, FakeVisionModel(canned), "/dev/null")
    cands = mine_candidates(rows)
    ev = load_evidence(os.path.join(DEMO, "evidence.tsv"))
    grounded = ground_candidates(cands, ev)
    assert all(c["status"] == "grounded" for c in grounded)
    assert all(c["provenance"][0]["canon"] == "tv-anime" for c in grounded)
