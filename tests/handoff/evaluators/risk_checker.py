"""Risk level checker for handoff health reports."""

from __future__ import annotations

from pydantic import BaseModel, Field


class RiskCheckResult(BaseModel):
    """Result of checking risk level in a handoff report."""

    expected_level: str = Field(default="", description="Expected risk level from test case")
    actual_level: str = Field(default="", description="Actual risk level from handoff output")
    matched: bool = Field(default=False, description="True if actual matches expected criteria")
    passed: bool = Field(default=False, description="Alias for matched (overall pass)")


class RiskChecker:
    """Checks that the risk level in a handoff output matches expectations.

    Supports two comparison modes via the expected dict:
    - "risk_level": exact match (actual == expected)
    - "risk_level_min": minimum threshold (actual >= expected in severity order)
    """

    RISK_ORDER: dict[str, int] = {
        "none": 0,
        "low": 1,
        "medium": 2,
        "high": 3,
        "critical": 4,
    }

    def check(
        self,
        actual_risk: str | None,
        expected: dict | None,
    ) -> RiskCheckResult:
        """Check whether the actual risk level meets expectations.

        Args:
            actual_risk: The risk level string from the handoff output.
            expected: Dict with "risk_level" (exact) and/or "risk_level_min" (>=).
                      If None or empty, the check passes by default.

        Returns:
            RiskCheckResult with comparison details.
        """
        actual = (actual_risk or "none").lower().strip()
        expected = expected or {}

        # If no risk expectations are defined, pass by default
        exact_expected = expected.get("risk_level")
        min_expected = expected.get("risk_level_min")

        if exact_expected is None and min_expected is None:
            return RiskCheckResult(
                expected_level="(not specified)",
                actual_level=actual,
                matched=True,
                passed=True,
            )

        matched = True
        expected_label_parts: list[str] = []

        # Exact match check
        if exact_expected is not None:
            exact_val = exact_expected.lower().strip()
            expected_label_parts.append(f"exact={exact_val}")
            if actual != exact_val:
                matched = False

        # Minimum threshold check
        if min_expected is not None:
            min_val = min_expected.lower().strip()
            expected_label_parts.append(f"min={min_val}")
            actual_ord = self.RISK_ORDER.get(actual, -1)
            min_ord = self.RISK_ORDER.get(min_val, -1)
            if actual_ord < min_ord:
                matched = False

        expected_label = ", ".join(expected_label_parts)

        return RiskCheckResult(
            expected_level=expected_label,
            actual_level=actual,
            matched=matched,
            passed=matched,
        )
