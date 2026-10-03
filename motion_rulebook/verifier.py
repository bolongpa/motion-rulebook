"""Verifier (layer 3: verify) -- v1 skeleton.

Closed video tools can only be influenced, not constrained, so generation
is followed by verification: each rule's `check` (question + expected
answer) is asked of the generated clip by a VLM judge. Failures feed a
bounded generate -> verify -> retry loop (the retry driver against real
video APIs is roadmap, not v1).

v1 ships:
    VLM            - judge interface: ask(media_path, question) -> str
    FakeVLM        - deterministic judge for demos/tests; answers come from
                     a caller-supplied observations dict
    run_checks     - ask every check, compare against expected
    CheckResult    - per-rule pass/fail with the judge's raw answer
"""
from __future__ import annotations

from dataclasses import dataclass


class VLM:
    """Judge interface. Subclass and implement ask()."""

    def ask(self, media_path: str, question: str) -> str:
        raise NotImplementedError


class FakeVLM(VLM):
    """Deterministic judge: answers are looked up from observations.

    observations maps check id (or question) -> the judge's answer string.
    Anything unmapped answers "" (treated as a fail -- the judge saw
    nothing supporting the expectation).
    """

    def __init__(self, observations: dict | None = None):
        self.observations = observations or {}

    def ask(self, media_path: str, question: str) -> str:
        return self.observations.get(question, "")


@dataclass
class CheckResult:
    rule_id: str
    question: str
    expected: str
    answer: str
    passed: bool


def run_checks(checks: list[dict], vlm: VLM,
               media_path: str = "<clip>") -> list[CheckResult]:
    """Ask each check of the judge; pass when expected appears in the answer."""
    results = []
    for c in checks:
        answer = vlm.ask(media_path, c["question"]) or ""
        passed = c["expected"].strip().lower() in answer.strip().lower()
        results.append(CheckResult(
            rule_id=c["id"], question=c["question"],
            expected=c["expected"], answer=answer, passed=passed))
    return results


def report_markdown(results: list[CheckResult]) -> str:
    L = ["# VERIFICATION REPORT"]
    passed = sum(r.passed for r in results)
    L.append(f"# {passed}/{len(results)} checks passed")
    L.append("")
    for r in results:
        mark = "PASS" if r.passed else "FAIL"
        L.append(f"- [{mark}] {r.rule_id}: {r.question}")
        L.append(f"    expected: {r.expected}")
        L.append(f"    judge saw: {r.answer or '(nothing)'}")
    return "\n".join(L) + "\n"
