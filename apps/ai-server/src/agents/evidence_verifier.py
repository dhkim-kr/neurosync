"""Evidence Verifier agent — checks handoff reports for unsupported claims and violations."""

from __future__ import annotations

import logging
import re
import time
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from src.agents.base import AgentInput, AgentOutput, BaseAgent
from src.schemas.common import EvidencePacket

logger = logging.getLogger(__name__)


class VerifierAction(StrEnum):
    """Outcome of evidence verification."""

    passed = "pass"
    reject = "reject"
    regenerate = "regenerate"


class VerifierIssue(BaseModel):
    """A single issue found during verification."""

    issue_type: str = Field(..., description="unsupported_claim | diagnosis_violation | treatment_violation")
    description: str
    location: str = Field(default="", description="Section or line reference in the report")
    severity: str = Field(default="warning", description="warning | error")


class EvidenceVerifierInput(AgentInput):
    """Input to the evidence verifier."""

    report_markdown: str = Field(..., description="The handoff report to verify")
    evidence_packets: list[EvidencePacket] = Field(default_factory=list)


class EvidenceVerifierOutput(AgentOutput):
    """Output from the evidence verifier."""

    action: VerifierAction = Field(default=VerifierAction.passed)
    issues: list[VerifierIssue] = Field(default_factory=list)
    unsupported_claim_count: int = Field(default=0)
    diagnosis_violation_count: int = Field(default=0)
    treatment_violation_count: int = Field(default=0)


# ── Diagnosis / treatment violation patterns ──────────────────────────

_DIAGNOSIS_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"우울증\s*(입니다|이[시세]|으로\s*판단|으로\s*진단)", re.IGNORECASE),
    re.compile(r"조현병\s*(입니다|이[시세]|으로\s*판단|으로\s*진단)", re.IGNORECASE),
    re.compile(r"불안장애\s*(입니다|이[시세]|으로\s*판단|으로\s*진단)", re.IGNORECASE),
    re.compile(r"(진단|확진)\s*(합니다|됩니다|내립니다)", re.IGNORECASE),
    re.compile(r"diagnosed\s+with", re.IGNORECASE),
]

_TREATMENT_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"(복용|투약|처방)\s*(하세요|하십시오|해야\s*합니다|을\s*권고)", re.IGNORECASE),
    re.compile(r"(용량|mg|밀리그램)\s*(을\s*)?(늘리|줄이|조절|변경)", re.IGNORECASE),
    re.compile(r"(치료법|요법)\s*(을\s*)?(추천|권고|제안)", re.IGNORECASE),
    re.compile(r"prescri(be|ption)", re.IGNORECASE),
]

# Evidence ID pattern: [ev_xxx_nnn]
_EVIDENCE_REF_RE = re.compile(r"\[ev_\w+_\d{3}\]")


class EvidenceVerifierAgent(BaseAgent):
    """Verifies handoff reports for evidence integrity and policy compliance.

    Checks:
    1. Unsupported claims — clinical statements without evidence IDs
    2. Diagnosis violations — asserting a diagnosis (forbidden)
    3. Treatment violations — prescribing or recommending treatment (forbidden)
    """

    @property
    def agent_name(self) -> str:
        return "evidence_verifier"

    async def run(self, inp: AgentInput, **kwargs: Any) -> EvidenceVerifierOutput:
        start = time.perf_counter()

        if not isinstance(inp, EvidenceVerifierInput):
            raise TypeError(f"Expected EvidenceVerifierInput, got {type(inp).__name__}")

        issues: list[VerifierIssue] = []
        known_ids = {ep.evidence_id for ep in inp.evidence_packets}

        # ── Check 1: Unsupported claims ──────────────────────────────
        unsupported = self._check_unsupported_claims(inp.report_markdown, known_ids)
        issues.extend(unsupported)

        # ── Check 2: Diagnosis violations ────────────────────────────
        diag_violations = self._check_diagnosis_violations(inp.report_markdown)
        issues.extend(diag_violations)

        # ── Check 3: Treatment violations ────────────────────────────
        treat_violations = self._check_treatment_violations(inp.report_markdown)
        issues.extend(treat_violations)

        # ── Determine action ─────────────────────────────────────────
        error_count = sum(1 for i in issues if i.severity == "error")
        warning_count = sum(1 for i in issues if i.severity == "warning")

        if error_count > 0:
            action = VerifierAction.reject
        elif warning_count >= 3:
            action = VerifierAction.regenerate
        else:
            action = VerifierAction.passed

        latency_ms = (time.perf_counter() - start) * 1000

        return EvidenceVerifierOutput(
            model_used="rule-engine",
            prompt_version="v1",
            latency_ms=latency_ms,
            reason_summary=f"Verification: {action.value} ({error_count} errors, {warning_count} warnings)",
            action=action,
            issues=issues,
            unsupported_claim_count=len(unsupported),
            diagnosis_violation_count=len(diag_violations),
            treatment_violation_count=len(treat_violations),
        )

    def _check_unsupported_claims(
        self, report: str, known_ids: set[str]
    ) -> list[VerifierIssue]:
        """Find sections with clinical content but no evidence citations."""
        issues: list[VerifierIssue] = []

        # Split by section headers
        sections = re.split(r"(?m)^###?\s+", report)

        for section in sections:
            if not section.strip():
                continue

            lines = section.strip().split("\n")
            section_title = lines[0].strip() if lines else "unknown"
            section_body = "\n".join(lines[1:]) if len(lines) > 1 else ""

            # Skip sections that don't need evidence (metadata sections)
            skip_sections = {"missing information", "evidence table", "누락", "근거 표"}
            if any(skip in section_title.lower() for skip in skip_sections):
                continue

            # Check if section has substantive content but no evidence refs
            has_content = len(section_body.strip()) > 20
            has_refs = bool(_EVIDENCE_REF_RE.search(section_body))

            if has_content and not has_refs:
                issues.append(
                    VerifierIssue(
                        issue_type="unsupported_claim",
                        description=f"Section '{section_title}' contains clinical content without evidence citations",
                        location=section_title,
                        severity="warning",
                    )
                )

        # Also check for dangling references (cited IDs not in evidence packets)
        cited_ids = set(_EVIDENCE_REF_RE.findall(report))
        for cited in cited_ids:
            clean_id = cited.strip("[]")
            if clean_id not in known_ids:
                issues.append(
                    VerifierIssue(
                        issue_type="unsupported_claim",
                        description=f"Evidence ID {cited} referenced but not found in evidence packets",
                        location="report",
                        severity="warning",
                    )
                )

        return issues

    def _check_diagnosis_violations(self, report: str) -> list[VerifierIssue]:
        """Check for forbidden diagnostic assertions."""
        issues: list[VerifierIssue] = []
        for pattern in _DIAGNOSIS_PATTERNS:
            for match in pattern.finditer(report):
                issues.append(
                    VerifierIssue(
                        issue_type="diagnosis_violation",
                        description=f"Diagnostic assertion detected: '{match.group()}'",
                        location=f"near: ...{report[max(0,match.start()-20):match.end()+20]}...",
                        severity="error",
                    )
                )
        return issues

    def _check_treatment_violations(self, report: str) -> list[VerifierIssue]:
        """Check for forbidden treatment/prescription recommendations."""
        issues: list[VerifierIssue] = []
        for pattern in _TREATMENT_PATTERNS:
            for match in pattern.finditer(report):
                issues.append(
                    VerifierIssue(
                        issue_type="treatment_violation",
                        description=f"Treatment recommendation detected: '{match.group()}'",
                        location=f"near: ...{report[max(0,match.start()-20):match.end()+20]}...",
                        severity="error",
                    )
                )
        return issues
