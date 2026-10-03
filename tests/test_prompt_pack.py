"""Prompt-pack compiler: chart-grounded matching and both targets."""
import os

import pytest

from motion_rulebook.prompt_pack import compile_prompt_pack, load_panel
from motion_rulebook.rulebook import Rulebook
from motion_rulebook.type_chart import effectiveness, multiplier

RB = os.path.join(os.path.dirname(__file__), "..", "rulebooks", "pokemon-gen1.yaml")
EX = os.path.join(os.path.dirname(__file__), "..", "examples", "pokemon-gen1")


@pytest.fixture(scope="module")
def rb():
    return Rulebook.load(RB)


def test_type_chart_grounds_immune():
    # Electric vs Rock/Ground (Onix): 1.0 * 0 -> immune. The EP005 moment.
    m, label = effectiveness("electric", ["rock", "ground"])
    assert m == 0
    assert label == "immune"


def test_type_chart_grounds_not_very_effective():
    m, label = effectiveness("electric", ["grass", "poison"])
    assert label == "not_very_effective"
    assert m == 0.5


def test_type_chart_grounds_super_effective():
    _, label = effectiveness("electric", ["water", "flying"])
    assert label == "super_effective"


def test_unknown_types_default_neutral():
    assert multiplier("mist", "dragon") == 1.0


def test_onix_panel_selects_immune_rule(rb):
    panel = load_panel(os.path.join(EX, "panel_pikachu_vs_onix.yaml"))
    pack = compile_prompt_pack(rb, panel)
    assert pack.matched_rule_ids == [
        "thunderbolt-depiction", "effectiveness-immune", "pokemon-vocalization"]
    assert "cheek pouches glow bright yellow" in pack.text
    assert "stands completely unaffected" in pack.text
    # checklist carries every matched rule
    assert len(pack.checks) == 3
    assert pack.checks[1]["id"] == "effectiveness-immune"


def test_bulbasaur_panel_selects_not_very_effective(rb):
    panel = load_panel(os.path.join(EX, "panel_pikachu_vs_bulbasaur.yaml"))
    pack = compile_prompt_pack(rb, panel)
    assert "effectiveness-not-very-effective" in pack.matched_rule_ids
    assert "effectiveness-immune" not in pack.matched_rule_ids


def test_capture_panel(rb):
    panel = load_panel(os.path.join(EX, "panel_capture_caterpie.yaml"))
    pack = compile_prompt_pack(rb, panel)
    assert pack.matched_rule_ids == ["capture-sequence"]
    assert "shakes exactly three times" in pack.text


def test_generic_pack_structure(rb):
    panel = load_panel(os.path.join(EX, "panel_capture_caterpie.yaml"))
    pack = compile_prompt_pack(rb, panel, target="generic")
    for section in ("## SCENE", "## CANON RULES", "## VERIFICATION CHECKLIST"):
        assert section in pack.text
    assert "pokemon-gen1-tv v0.1.0" in pack.text


def test_compact_pack_is_single_block(rb):
    panel = load_panel(os.path.join(EX, "panel_pikachu_vs_onix.yaml"))
    pack = compile_prompt_pack(rb, panel, target="compact")
    assert "##" not in pack.text
    assert "cheek pouches glow bright yellow" in pack.text
    assert pack.text.count("\n") <= 2


def test_unknown_target_rejected(rb):
    panel = load_panel(os.path.join(EX, "panel_capture_caterpie.yaml"))
    with pytest.raises(ValueError, match="unknown target"):
        compile_prompt_pack(rb, panel, target="tiktok")


def test_rules_do_not_duplicate_across_points(rb):
    panel = {"expansion_points": [
        {"type": "vocalization", "speaker": "Pikachu"},
        {"type": "vocalization", "speaker": "Ash"},
    ]}
    pack = compile_prompt_pack(rb, panel)
    assert pack.matched_rule_ids == ["pokemon-vocalization"]
