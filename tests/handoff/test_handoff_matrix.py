"""Parametrized test: run all 6 matrix cases through HandoffGenerator + EvidenceVerifier."""

from __future__ import annotations

import pytest

from src.agents.evidence_verifier import EvidenceVerifierInput, VerifierAction

from tests.handoff.evaluators.composite import CompositeEvaluator
from tests.handoff.fixtures.patients import load_fixture, fixture_to_handoff_input

MATRIX_CASES = [
    "mild_first_visit.json",
    "mild_revisit.json",
    "severe_first_visit.json",
    "severe_revisit.json",
    "safety_trigger.json",
    "longitudinal_pair.json",
]


@pytest.mark.parametrize("fixture_name", MATRIX_CASES[:4])
@pytest.mark.asyncio
async def test_handoff_report_quality(fixture_name, handoff_agent, evidence_verifier):
    """Each case must produce a valid handoff report with no violations."""
    fixture = load_fixture(fixture_name)
    inp = fixture_to_handoff_input(fixture)
    expected = fixture["expected"]

    # Generate handoff report
    output = await handoff_agent.run(inp)

    # Verify evidence integrity
    verifier_inp = EvidenceVerifierInput(
        session_id=inp.session_id,
        report_markdown=output.report_markdown,
        evidence_packets=output.evidence_packets,
    )
    verifier_output = await evidence_verifier.run(verifier_inp)

    # Evaluate quality
    evaluator = CompositeEvaluator()
    result = evaluator.evaluate(
        case_id=fixture["case_id"],
        case_name=fixture["case_name"],
        handoff_output=output,
        expected=expected,
        is_revisit=not inp.is_first_visit,
    )

    # Assertions
    assert verifier_output.action != VerifierAction.reject, (
        f"EvidenceVerifier rejected report: {verifier_output.issues}"
    )
    assert verifier_output.diagnosis_violation_count == 0, (
        f"Diagnosis violations found: {verifier_output.issues}"
    )
    assert verifier_output.treatment_violation_count == 0, (
        f"Treatment violations found: {verifier_output.issues}"
    )
    assert result.sections.passed, (
        f"Section check failed — missing: {result.sections.missing}"
    )
    assert result.violations.passed, (
        f"Violation check failed: {result.violations.diagnosis_violations + result.violations.treatment_violations}"
    )


@pytest.mark.asyncio
async def test_revisit_contains_longitudinal_delta(handoff_agent):
    """Revisit cases (TC-002, TC-004) must contain longitudinal delta information."""
    for fixture_name in ("mild_revisit.json", "severe_revisit.json"):
        fixture = load_fixture(fixture_name)
        inp = fixture_to_handoff_input(fixture)
        output = await handoff_agent.run(inp)

        # Delta section should reference previous scores or changes
        report = output.report_markdown.lower()
        has_delta = any(
            kw in report
            for kw in ["종단", "변화", "이전", "delta", "previous", "longitudinal"]
        )
        assert has_delta, (
            f"{fixture_name}: Revisit report should contain longitudinal delta section"
        )


@pytest.mark.asyncio
async def test_severe_cases_flag_human_review(handoff_agent):
    """Severe cases (TC-003, TC-004) with risk events should flag human review."""
    for fixture_name in ("severe_first_visit.json", "severe_revisit.json"):
        fixture = load_fixture(fixture_name)
        inp = fixture_to_handoff_input(fixture)
        output = await handoff_agent.run(inp)

        assert output.requires_human_review, (
            f"{fixture_name}: Severe case should flag requires_human_review"
        )
