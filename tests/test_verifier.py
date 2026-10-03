"""Verifier: FakeVLM judge and check runner."""
from motion_rulebook.verifier import FakeVLM, run_checks, report_markdown

CHECKS = [
    {"id": "capture-sequence",
     "question": "How many times does the Poke Ball shake before the click?",
     "expected": "three"},
    {"id": "thunderbolt-depiction",
     "question": "Where does the lightning come from?",
     "expected": "the cheek pouches"},
]


def test_pass_when_expected_in_answer():
    vlm = FakeVLM({
        "How many times does the Poke Ball shake before the click?":
            "The ball shook three times, then clicked.",
        "Where does the lightning come from?":
            "Lightning arcs from the cheek pouches.",
    })
    results = run_checks(CHECKS, vlm)
    assert all(r.passed for r in results)


def test_fail_when_judge_saw_nothing_supporting():
    vlm = FakeVLM({
        "How many times does the Poke Ball shake before the click?":
            "The ball shook five times.",
    })
    results = run_checks(CHECKS, vlm)
    assert not results[0].passed      # five != three
    assert not results[1].passed      # unmapped -> "" -> fail


def test_report_marks_pass_fail():
    vlm = FakeVLM({CHECKS[0]["question"]: "three shakes"})
    md = report_markdown(run_checks(CHECKS, vlm))
    assert "1/2 checks passed" in md
    assert "[PASS] capture-sequence" in md
    assert "[FAIL] thunderbolt-depiction" in md
