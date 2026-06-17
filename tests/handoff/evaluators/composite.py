"""Composite evaluator that orchestrates all individual checkers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

from .evidence_checker import EvidenceCheckResult, EvidenceChecker
from .longitudinal_checker import LongitudinalCheckResult, LongitudinalChecker
from .risk_checker import RiskCheckResult, RiskChecker
from .safety_checker import SafetyCheckResult, SafetyChecker
from .section_checker import SectionCheckResult, SectionChecker
from .violation_checker import ViolationCheckResult, ViolationChecker

if TYPE_CHECKING:
    from src.schemas.handoff import HandoffOutput
    from src.schemas.safety import SafetyOutput


class HandoffEvalResult(BaseModel):
    """Aggregate evaluation result for a single handoff test case."""

    case_id: str = Field(..., description="Unique test case identifier")
    case_name: str = Field(default="", description="Human-readable case name")
    sections: SectionCheckResult | None = Field(default=None)
    evidence: EvidenceCheckResult | None = Field(default=None)
    violations: ViolationCheckResult | None = Field(default=None)
    risk: RiskCheckResult | None = Field(default=None)
    safety: SafetyCheckResult | None = Field(default=None)
    longitudinal: LongitudinalCheckResult | None = Field(default=None)
    overall_pass: bool = Field(default=False)
    latency_ms: float = Field(default=0.0, description="Report generation latency in ms")
    model_used: str = Field(default="", description="Model that generated the report")

    def failures_summary(self) -> str:
        """Return a human-readable summary of all failing checks.

        Returns an empty string if all checks passed.
        """
        failures: list[str] = []

        if self.sections is not None and not self.sections.passed:
            missing = ", ".join(self.sections.missing) if self.sections.missing else "unknown"
            failures.append(
                f"sections: {len(self.sections.present)}/{self.sections.total} "
                f"(missing: {missing})"
            )

        if self.evidence is not None and not self.evidence.passed:
            failures.append(
                f"evidence: {self.evidence.citation_count} citations "
                f"(dangling={len(self.evidence.dangling_refs)}, "
                f"uncited_sections={len(self.evidence.uncited_sections)})"
            )

        if self.violations is not None and not self.violations.passed:
            diag_count = len(self.violations.diagnosis_violations)
            treat_count = len(self.violations.treatment_violations)
            failures.append(
                f"violations: {diag_count} diagnosis, {treat_count} treatment"
            )

        if self.risk is not None and not self.risk.passed:
            failures.append(
                f"risk: expected={self.risk.expected_level}, "
                f"actual={self.risk.actual_level}"
            )

        if self.safety is not None and not self.safety.passed:
            failures.append(
                f"safety: risk={self.safety.risk_level}, "
                f"crisis={self.safety.crisis_activated}, "
                f"categories={self.safety.categories}"
            )

        if self.longitudinal is not None and not self.longitudinal.passed:
            failures.append(
                f"longitudinal: delta_section={self.longitudinal.has_delta_section}, "
                f"direction={self.longitudinal.delta_direction}"
            )

        if not failures:
            return ""

        return f"[{self.case_id}] FAIL: " + "; ".join(failures)


class CompositeEvaluator:
    """Runs all individual checkers and produces a single HandoffEvalResult.

    Usage:
        evaluator = CompositeEvaluator()
        result = evaluator.evaluate(
            case_id="TC-001",
            case_name="Moderate depression",
            handoff_output=handoff_output,
            expected={"risk_level": "medium", "categories": ["depression"]},
        )
    """

    def __init__(self) -> None:
        self._section_checker = SectionChecker()
        self._evidence_checker = EvidenceChecker()
        self._violation_checker = ViolationChecker()
        self._risk_checker = RiskChecker()
        self._safety_checker = SafetyChecker()
        self._longitudinal_checker = LongitudinalChecker()

    def evaluate(
        self,
        case_id: str,
        case_name: str,
        handoff_output: Any,
        expected: dict | None = None,
        safety_output: Any | None = None,
        is_revisit: bool = False,
    ) -> HandoffEvalResult:
        """Run all evaluators on a handoff output and return aggregate results.

        Args:
            case_id: Unique test case identifier.
            case_name: Human-readable case description.
            handoff_output: HandoffOutput instance from the handoff generator.
            expected: Dict with expected values for comparison. Supported keys:
                - risk_level, risk_level_min: for RiskChecker
                - categories, crisis_protocol_activated, safety_risk_level_min: for SafetyChecker
                - has_delta, direction: for LongitudinalChecker
            safety_output: SafetyOutput instance (optional, for safety checks).
            is_revisit: Whether this is a revisit case (enables longitudinal checks).

        Returns:
            HandoffEvalResult with all check results and overall pass status.
        """
        expected = expected or {}

        # Extract fields defensively from handoff_output
        report_markdown = str(getattr(handoff_output, "report_markdown", "") or "")
        evidence_packets = list(getattr(handoff_output, "evidence_packets", []) or [])
        actual_risk = str(getattr(handoff_output, "risk_level", "none") or "none")
        latency_ms = float(getattr(handoff_output, "latency_ms", 0.0) or 0.0)
        model_used = str(getattr(handoff_output, "model_used", "") or "")
        prior_handoff = getattr(handoff_output, "prior_handoff", None)

        # If HandoffInput had prior_handoff, try to get it
        # (some pipelines store it on the output as well)
        if prior_handoff is None and is_revisit:
            # Mark as revisit even without prior handoff text
            prior_handoff = ""

        # 1. Section check
        sections_result = self._section_checker.check(report_markdown)

        # 2. Evidence check
        evidence_result = self._evidence_checker.check(
            report_markdown, evidence_packets
        )

        # 3. Violation check
        violations_result = self._violation_checker.check(report_markdown)

        # 4. Risk check
        risk_expected = {}
        if "risk_level" in expected:
            risk_expected["risk_level"] = expected["risk_level"]
        if "risk_level_min" in expected:
            risk_expected["risk_level_min"] = expected["risk_level_min"]
        risk_result = self._risk_checker.check(actual_risk, risk_expected)

        # 5. Safety check (optional)
        safety_result: SafetyCheckResult | None = None
        if safety_output is not None:
            safety_expected = {}
            if "safety_risk_level_min" in expected:
                safety_expected["risk_level_min"] = expected["safety_risk_level_min"]
            if "crisis_protocol_activated" in expected:
                safety_expected["crisis_protocol_activated"] = expected[
                    "crisis_protocol_activated"
                ]
            if "categories" in expected:
                safety_expected["categories"] = expected["categories"]
            safety_result = self._safety_checker.check(safety_output, safety_expected)

        # 6. Longitudinal check (only for revisit cases)
        longitudinal_result: LongitudinalCheckResult | None = None
        if is_revisit or prior_handoff is not None:
            longitudinal_expected = {}
            if "has_delta" in expected:
                longitudinal_expected["has_delta"] = expected["has_delta"]
            if "direction" in expected:
                longitudinal_expected["direction"] = expected["direction"]
            longitudinal_result = self._longitudinal_checker.check(
                report_markdown,
                prior_handoff=prior_handoff if prior_handoff else None,
                expected=longitudinal_expected,
            )

        # Overall pass: all executed checks must pass
        overall_pass = all([
            sections_result.passed,
            evidence_result.passed,
            violations_result.passed,
            risk_result.passed,
            safety_result is None or safety_result.passed,
            longitudinal_result is None or longitudinal_result.passed,
        ])

        return HandoffEvalResult(
            case_id=case_id,
            case_name=case_name,
            sections=sections_result,
            evidence=evidence_result,
            violations=violations_result,
            risk=risk_result,
            safety=safety_result,
            longitudinal=longitudinal_result,
            overall_pass=overall_pass,
            latency_ms=latency_ms,
            model_used=model_used,
        )
