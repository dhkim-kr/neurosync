"""Safety Guard tests — verify crisis protocol activation on dangerous messages."""

from __future__ import annotations

import pytest

from tests.handoff.fixtures.patients import load_fixture, fixture_to_safety_input
from tests.handoff.evaluators.safety_checker import SafetyChecker


@pytest.mark.asyncio
async def test_crisis_protocol_activated(safety_agent):
    """TC-005: Explicit crisis phrases must trigger crisis protocol."""
    fixture = load_fixture("safety_trigger.json")
    inp = fixture_to_safety_input(fixture)
    output = await safety_agent.run(inp)

    assert output.crisis_protocol_activated is True, (
        f"Crisis protocol should be activated, got risk_level={output.risk_level}"
    )
    assert output.requires_human_review is True
    assert output.risk_level in ("high", "critical"), (
        f"Expected high/critical, got {output.risk_level}"
    )


@pytest.mark.asyncio
async def test_rule_engine_triggers(safety_agent):
    """TC-005: Korean crisis keywords must fire the rule engine."""
    fixture = load_fixture("safety_trigger.json")
    inp = fixture_to_safety_input(fixture)
    output = await safety_agent.run(inp)

    assert output.rule_triggered is True, "Rule engine should fire on crisis keywords"
    assert len(output.flagged_phrases) > 0, "Should have flagged phrases"


@pytest.mark.asyncio
async def test_safety_categories_detected(safety_agent):
    """TC-005: Suicidal ideation category must be identified."""
    fixture = load_fixture("safety_trigger.json")
    inp = fixture_to_safety_input(fixture)
    output = await safety_agent.run(inp)

    expected = fixture["expected"]
    expected_categories = expected.get("expected_categories_include", [])

    for cat in expected_categories:
        assert any(cat in c for c in output.categories), (
            f"Category '{cat}' not found in {output.categories}"
        )


@pytest.mark.asyncio
async def test_safety_full_evaluation(safety_agent):
    """TC-005: Full safety evaluation with all checks."""
    fixture = load_fixture("safety_trigger.json")
    inp = fixture_to_safety_input(fixture)
    output = await safety_agent.run(inp)

    checker = SafetyChecker()
    result = checker.check(output, fixture["expected"])

    assert result.passed, (
        f"Safety check failed: risk={result.risk_level}, "
        f"crisis={result.crisis_activated}, rule={result.rule_triggered}, "
        f"categories={result.categories}"
    )


@pytest.mark.asyncio
async def test_mild_case_no_crisis(safety_agent):
    """Mild cases must NOT trigger crisis protocol."""
    fixture = load_fixture("mild_first_visit.json")
    inp = fixture_to_safety_input(fixture)
    output = await safety_agent.run(inp)

    assert output.crisis_protocol_activated is False, (
        "Mild case should not trigger crisis protocol"
    )
    assert output.risk_level in ("none", "low"), (
        f"Mild case should be none/low risk, got {output.risk_level}"
    )
