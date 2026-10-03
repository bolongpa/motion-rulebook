"""Rulebook schema, validation, and matching."""
import os

import pytest
import yaml

from motion_rulebook.rulebook import (
    Rule, Rulebook, EXPANSION_POINT_TYPES, assert_no_negations,
)

RB = os.path.join(os.path.dirname(__file__), "..", "rulebooks", "pokemon-gen1.yaml")


@pytest.fixture(scope="module")
def rb():
    return Rulebook.load(RB)


def test_reference_rulebook_loads(rb):
    assert rb.name == "pokemon-gen1-tv"
    assert rb.version == "0.1.0"
    assert len(rb.rules) == 10
    assert len({r.id for r in rb.rules}) == 10  # ids unique


def test_every_rule_has_provenance(rb):
    for r in rb.rules:
        assert r.provenance["canon"]
        assert r.provenance["ref"]
        assert r.check["question"]
        assert r.check["expected"]


def test_prompt_text_is_positive_only(rb):
    for r in rb.rules:
        assert_no_negations(r.prompt_text)  # must not raise


def test_trigger_types_are_known(rb):
    for r in rb.rules:
        assert r.trigger["type"] in EXPANSION_POINT_TYPES


def test_capture_match(rb):
    ms = rb.match({"type": "event_sequence", "event": "capture",
                   "target": "Caterpie"})
    assert [r.id for r in ms] == ["capture-sequence"]


def test_move_depiction_match(rb):
    ms = rb.match({"type": "move_depiction", "move": "Thunderbolt",
                   "user": "Pikachu"})
    assert [r.id for r in ms] == ["thunderbolt-depiction"]


def test_unknown_move_matches_nothing(rb):
    assert rb.match({"type": "move_depiction", "move": "Hyper Beam"}) == []


def test_vocalization_matches_any_speaker(rb):
    ms = rb.match({"type": "vocalization", "speaker": "Caterpie"})
    assert [r.id for r in ms] == ["pokemon-vocalization"]


def test_subset_match_ignores_extra_point_keys(rb):
    ms = rb.match({"type": "event_sequence", "event": "faint",
                   "target": "Onix", "round": 3})
    assert [r.id for r in ms] == ["faint-sequence"]


def _rule_dict(**kw):
    base = {
        "id": "x", "trigger": {"type": "vocalization"},
        "constraint": "c", "prompt_text": "A calm meadow.",
        "check": {"question": "q?", "expected": "e"},
        "provenance": {"canon": "tv-anime", "ref": "EP001"},
    }
    base.update(kw)
    return base


def test_rejects_unknown_expansion_point_type():
    with pytest.raises(ValueError, match="unknown expansion point type"):
        Rule(**_rule_dict(trigger={"type": "teleport"}))


def test_rejects_negation_in_prompt_text():
    with pytest.raises(ValueError, match="negation"):
        Rule(**_rule_dict(prompt_text="A meadow with no trees."))


def test_rejects_missing_check_field():
    with pytest.raises(ValueError, match="check needs"):
        Rule(**_rule_dict(check={"question": "q?"}))


def test_rejects_duplicate_ids(tmp_path):
    data = {"meta": {}, "rules": [_rule_dict(id="dup"), _rule_dict(id="dup")]}
    p = tmp_path / "rb.yaml"
    p.write_text(yaml.safe_dump(data))
    with pytest.raises(ValueError, match="duplicate rule id"):
        Rulebook.load(str(p))


def test_rejects_missing_required_field(tmp_path):
    d = _rule_dict()
    del d["prompt_text"]
    p = tmp_path / "rb.yaml"
    p.write_text(yaml.safe_dump({"rules": [d]}))
    with pytest.raises(ValueError, match="prompt_text"):
        Rulebook.load(str(p))
