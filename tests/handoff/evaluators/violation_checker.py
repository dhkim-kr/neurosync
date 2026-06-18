"""Diagnosis and treatment violation checker for handoff health reports.

Reuses the regex patterns from the evidence_verifier agent to detect
forbidden diagnostic assertions and treatment recommendations.
"""

from __future__ import annotations

import re

from pydantic import BaseModel, Field


# ── Diagnosis violation patterns (from evidence_verifier.py) ─────────────
_DIAGNOSIS_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"우울증\s*(입니다|이[시세]|으로\s*판단|으로\s*진단)", re.IGNORECASE),
    re.compile(r"조현병\s*(입니다|이[시세]|으로\s*판단|으로\s*진단)", re.IGNORECASE),
    re.compile(r"불안장애\s*(입니다|이[시세]|으로\s*판단|으로\s*진단)", re.IGNORECASE),
    re.compile(r"(진단|확진)\s*(합니다|됩니다|내립니다)", re.IGNORECASE),
    re.compile(r"diagnosed\s+with", re.IGNORECASE),
]

# ── Treatment violation patterns (from evidence_verifier.py) ─────────────
_TREATMENT_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"(복용|투약|처방)\s*(하세요|하십시오|해야\s*합니다|을\s*권고)", re.IGNORECASE),
    re.compile(r"(용량|mg|밀리그램)\s*(을\s*)?(늘리|줄이|조절|변경)", re.IGNORECASE),
    re.compile(r"(치료법|요법)\s*(을\s*)?(추천|권고|제안)", re.IGNORECASE),
    re.compile(r"prescri(be|ption)", re.IGNORECASE),
]


class ViolationCheckResult(BaseModel):
    """Result of checking for diagnosis and treatment violations."""

    diagnosis_violations: list[dict] = Field(
        default_factory=list,
        description="List of {pattern, matched_text, location} for diagnosis violations",
    )
    treatment_violations: list[dict] = Field(
        default_factory=list,
        description="List of {pattern, matched_text, location} for treatment violations",
    )
    passed: bool = Field(default=True, description="True if both violation counts are 0")


class ViolationChecker:
    """Checks handoff reports for forbidden diagnostic and treatment statements.

    A handoff report must NOT:
    - Assert a definitive diagnosis (e.g. "우울증입니다")
    - Prescribe or recommend treatment (e.g. "복용하세요")
    """

    def check(self, report_markdown: str) -> ViolationCheckResult:
        """Check the report for diagnosis and treatment violations.

        Args:
            report_markdown: The handoff report in markdown format.

        Returns:
            ViolationCheckResult with any detected violations.
        """
        if not report_markdown or not report_markdown.strip():
            return ViolationCheckResult(
                diagnosis_violations=[],
                treatment_violations=[],
                passed=True,
            )

        diagnosis_violations = self._find_violations(
            report_markdown, _DIAGNOSIS_PATTERNS, "diagnosis"
        )
        treatment_violations = self._find_violations(
            report_markdown, _TREATMENT_PATTERNS, "treatment"
        )

        return ViolationCheckResult(
            diagnosis_violations=diagnosis_violations,
            treatment_violations=treatment_violations,
            passed=(len(diagnosis_violations) == 0 and len(treatment_violations) == 0),
        )

    @staticmethod
    def _find_violations(
        report: str,
        patterns: list[re.Pattern[str]],
        violation_type: str,
    ) -> list[dict]:
        """Find all matches for a list of regex patterns in the report.

        Returns a list of dicts with pattern, matched_text, and location context.
        """
        violations: list[dict] = []
        for pattern in patterns:
            for match in pattern.finditer(report):
                # Extract surrounding context for location
                start = max(0, match.start() - 30)
                end = min(len(report), match.end() + 30)
                context = report[start:end].replace("\n", " ").strip()

                violations.append({
                    "pattern": pattern.pattern,
                    "matched_text": match.group(),
                    "location": f"...{context}...",
                })
        return violations
