"""Longitudinal delta checker for handoff health reports."""

from __future__ import annotations

import re

from pydantic import BaseModel, Field


class LongitudinalCheckResult(BaseModel):
    """Result of checking longitudinal (delta) information in a handoff report."""

    has_delta_section: bool = Field(
        default=False, description="Whether a delta/change section was found"
    )
    delta_direction: str | None = Field(
        default=None,
        description="Detected direction: 'improved', 'worsened', 'stable', or None",
    )
    score_comparison_found: bool = Field(
        default=False, description="Whether a score comparison (e.g. PHQ-9 change) was found"
    )
    first_evidence_count: int = Field(
        default=0, description="Evidence count from first-chat report (TC-006)"
    )
    longitudinal_evidence_count: int = Field(
        default=0, description="Evidence count from longitudinal report (TC-006)"
    )
    first_missing_slots: int = Field(
        default=0, description="Missing slot count from first-chat report (TC-006)"
    )
    longitudinal_missing_slots: int = Field(
        default=0, description="Missing slot count from longitudinal report (TC-006)"
    )
    passed: bool = Field(default=False, description="Overall pass status")


# Keywords for detecting delta/change sections
_DELTA_SECTION_KEYWORDS: list[str] = [
    "종단",       # longitudinal
    "변화",       # change / delta
    "delta",
    "longitudinal",
    "비교",       # comparison
    "추이",       # trend
]

# Direction keywords
_IMPROVED_KEYWORDS: list[str] = [
    "호전", "개선", "감소", "향상", "완화", "improved", "better", "decreased",
]
_WORSENED_KEYWORDS: list[str] = [
    "악화", "증가", "심화", "worsened", "worse", "increased", "deteriorat",
]
_STABLE_KEYWORDS: list[str] = [
    "유지", "동일", "변화 없", "stable", "unchanged", "no change",
]

# Score comparison patterns (e.g., "PHQ-9: 15 -> 12", "PHQ-9 15점에서 12점")
_SCORE_COMPARE_RE = re.compile(
    r"(PHQ-?9|GAD-?7|BDI|BAI)\s*:?\s*\d+\s*(->|→|에서|점\s*→)\s*\d+",
    re.IGNORECASE,
)


class LongitudinalChecker:
    """Checks that a revisit handoff report includes longitudinal comparison data.

    Only applies to revisit cases (is_revisit=True or prior_handoff provided).
    For first-visit cases, the check passes automatically.
    """

    def check(
        self,
        report_markdown: str,
        prior_handoff: str | None = None,
        expected: dict | None = None,
    ) -> LongitudinalCheckResult:
        """Check for longitudinal delta information in the report.

        Args:
            report_markdown: The handoff report in markdown format.
            prior_handoff: Previous handoff report markdown (None for first visit).
            expected: Dict with optional keys:
                - "has_delta": bool -- whether a delta section is expected
                - "direction": str -- expected direction (improved/worsened/stable)

        Returns:
            LongitudinalCheckResult with delta detection details.
        """
        expected = expected or {}

        # If no prior handoff, this is a first visit -- longitudinal check is N/A
        if prior_handoff is None:
            return LongitudinalCheckResult(
                has_delta_section=False,
                delta_direction=None,
                score_comparison_found=False,
                passed=True,  # N/A counts as pass for first visits
            )

        if not report_markdown or not report_markdown.strip():
            return LongitudinalCheckResult(
                has_delta_section=False,
                delta_direction=None,
                score_comparison_found=False,
                passed=False,
            )

        report_lower = report_markdown.lower()

        # 1. Check for delta section
        has_delta_section = any(kw in report_lower for kw in _DELTA_SECTION_KEYWORDS)

        # 2. Detect direction
        delta_direction = self._detect_direction(report_lower)

        # 3. Check for score comparisons
        score_comparison_found = bool(_SCORE_COMPARE_RE.search(report_markdown))

        # 4. Determine pass/fail
        passed = True

        expected_has_delta = expected.get("has_delta")
        if expected_has_delta is not None and has_delta_section != bool(expected_has_delta):
            passed = False

        expected_direction = expected.get("direction")
        if expected_direction is not None:
            if delta_direction != expected_direction.lower().strip():
                passed = False

        # Default expectation: revisit reports should at least have a delta section
        if expected_has_delta is None and expected_direction is None:
            passed = has_delta_section

        return LongitudinalCheckResult(
            has_delta_section=has_delta_section,
            delta_direction=delta_direction,
            score_comparison_found=score_comparison_found,
            passed=passed,
        )

    @staticmethod
    def _detect_direction(report_lower: str) -> str | None:
        """Detect the overall direction of change from keywords."""
        improved = any(kw in report_lower for kw in _IMPROVED_KEYWORDS)
        worsened = any(kw in report_lower for kw in _WORSENED_KEYWORDS)
        stable = any(kw in report_lower for kw in _STABLE_KEYWORDS)

        # If conflicting signals, prefer the more explicit one
        if improved and not worsened:
            return "improved"
        if worsened and not improved:
            return "worsened"
        if stable and not improved and not worsened:
            return "stable"
        if improved and worsened:
            # Mixed signals -- cannot determine
            return None

        return None
