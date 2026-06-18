"""Safety output checker for handoff health reports."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from src.schemas.safety import SafetyOutput


# Risk ordering (duplicated here to avoid import-time dependency on ai-server)
_RISK_ORDER: dict[str, int] = {
    "none": 0,
    "low": 1,
    "medium": 2,
    "high": 3,
    "critical": 4,
}


class SafetyCheckResult(BaseModel):
    """Result of checking safety classification output."""

    risk_level: str = Field(default="none", description="Actual risk level from safety output")
    crisis_activated: bool = Field(default=False, description="Whether crisis protocol was activated")
    rule_triggered: bool = Field(default=False, description="Whether rule-based classifier fired")
    categories: list[str] = Field(default_factory=list, description="Detected risk categories")
    expected_categories: list[str] = Field(
        default_factory=list, description="Expected risk categories from test case"
    )
    passed: bool = Field(default=False, description="Overall pass status")


class SafetyChecker:
    """Validates SafetyOutput against expected test case criteria.

    Checks:
    - risk_level >= expected minimum
    - crisis_protocol_activated matches expected value
    - detected categories overlap with expected categories
    """

    def check(
        self,
        safety_output: Any | None,
        expected: dict | None,
    ) -> SafetyCheckResult:
        """Validate the safety output against expectations.

        Args:
            safety_output: SafetyOutput instance (or None if safety was not run).
            expected: Dict with optional keys:
                - "risk_level_min": minimum risk level string
                - "crisis_protocol_activated": expected bool
                - "categories": list of expected category strings

        Returns:
            SafetyCheckResult with comparison details.
        """
        expected = expected or {}

        if safety_output is None:
            # No safety output provided -- pass only if no expectations
            has_expectations = bool(expected)
            return SafetyCheckResult(
                risk_level="none",
                crisis_activated=False,
                rule_triggered=False,
                categories=[],
                expected_categories=expected.get("categories", []),
                passed=not has_expectations,
            )

        # Extract fields from safety output (defensive attribute access)
        actual_risk = str(getattr(safety_output, "risk_level", "none")).lower().strip()
        crisis_activated = bool(getattr(safety_output, "crisis_protocol_activated", False))
        rule_triggered = bool(getattr(safety_output, "rule_triggered", False))
        categories = list(getattr(safety_output, "categories", []))

        expected_categories = expected.get("categories", [])
        passed = True

        # Check 1: Risk level meets minimum
        expected_min_risk = expected.get("risk_level_min")
        if expected_min_risk is not None:
            min_val = expected_min_risk.lower().strip()
            actual_ord = _RISK_ORDER.get(actual_risk, -1)
            min_ord = _RISK_ORDER.get(min_val, -1)
            if actual_ord < min_ord:
                passed = False

        # Check 2: Crisis protocol activation matches
        expected_crisis = expected.get("crisis_protocol_activated")
        if expected_crisis is not None:
            if crisis_activated != bool(expected_crisis):
                passed = False

        # Check 3: Category overlap -- all expected categories must be present
        if expected_categories:
            actual_set = {c.lower().strip() for c in categories}
            expected_set = {c.lower().strip() for c in expected_categories}
            if not expected_set.issubset(actual_set):
                passed = False

        return SafetyCheckResult(
            risk_level=actual_risk,
            crisis_activated=crisis_activated,
            rule_triggered=rule_triggered,
            categories=categories,
            expected_categories=expected_categories,
            passed=passed,
        )
