"""Evidence citation checker for handoff health reports."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from src.schemas.common import EvidencePacket


class EvidenceCheckResult(BaseModel):
    """Result of checking evidence citations in a handoff report."""

    citation_count: int = Field(default=0, description="Total evidence citations found")
    dangling_refs: list[str] = Field(
        default_factory=list,
        description="Evidence IDs cited in report but absent from evidence_packets",
    )
    uncited_sections: list[str] = Field(
        default_factory=list,
        description="Content sections that contain no evidence citations",
    )
    passed: bool = Field(default=False, description="True if citation_count >= min_citations")


class EvidenceChecker:
    """Checks that evidence citations in a handoff report are valid and sufficient.

    Verifies:
    - Total citation count meets minimum threshold
    - All cited evidence IDs exist in the provided evidence packets
    - Content sections include at least one citation
    """

    EVIDENCE_PATTERN: re.Pattern[str] = re.compile(r"\[ev_\w+_\d{3}\]")

    # Sections that are expected to have evidence citations
    _CLINICAL_SECTION_KEYWORDS: list[str] = [
        "주호소",
        "현병력",
        "주요 증상",
        "위험",
        "약물",
    ]

    # Sections that do not need citations (metadata / structural)
    _SKIP_SECTION_KEYWORDS: set[str] = {
        "누락",
        "missing",
        "근거",
        "evidence",
        "종단",
        "문서",
        "uploaded",
    }

    # Header regex for splitting report into sections
    _HEADER_RE: re.Pattern[str] = re.compile(r"(?m)^#{1,4}\s+")

    def check(
        self,
        report_markdown: str,
        evidence_packets: list[EvidencePacket] | None = None,
        min_citations: int = 3,
    ) -> EvidenceCheckResult:
        """Check evidence citation integrity in the report.

        Args:
            report_markdown: The handoff report in markdown format.
            evidence_packets: List of EvidencePacket objects from the handoff output.
            min_citations: Minimum number of citations required to pass.

        Returns:
            EvidenceCheckResult with citation stats, dangling refs, and uncited sections.
        """
        if not report_markdown or not report_markdown.strip():
            return EvidenceCheckResult(
                citation_count=0,
                dangling_refs=[],
                uncited_sections=[],
                passed=False,
            )

        evidence_packets = evidence_packets or []

        # Find all cited evidence IDs in the report
        all_citations = self.EVIDENCE_PATTERN.findall(report_markdown)
        unique_citations = set(all_citations)
        citation_count = len(all_citations)

        # Build set of known evidence IDs
        known_ids = {f"[{ep.evidence_id}]" for ep in evidence_packets}

        # Find dangling references: cited but not in evidence packets
        dangling_refs: list[str] = []
        if known_ids:  # Only check if evidence packets were provided
            for cited in sorted(unique_citations):
                if cited not in known_ids:
                    dangling_refs.append(cited)

        # Find uncited clinical sections
        uncited_sections = self._find_uncited_sections(report_markdown)

        return EvidenceCheckResult(
            citation_count=citation_count,
            dangling_refs=dangling_refs,
            uncited_sections=uncited_sections,
            passed=citation_count >= min_citations,
        )

    def _find_uncited_sections(self, report: str) -> list[str]:
        """Identify clinical sections that lack evidence citations."""
        uncited: list[str] = []
        sections = self._HEADER_RE.split(report)

        for section in sections:
            if not section.strip():
                continue

            lines = section.strip().split("\n")
            section_title = lines[0].strip() if lines else ""
            section_body = "\n".join(lines[1:]) if len(lines) > 1 else ""
            title_lower = section_title.lower()

            # Skip non-clinical / metadata sections
            if any(skip in title_lower for skip in self._SKIP_SECTION_KEYWORDS):
                continue

            # Only check sections that are expected to have citations
            is_clinical = any(kw in title_lower for kw in self._CLINICAL_SECTION_KEYWORDS)
            if not is_clinical:
                continue

            has_content = len(section_body.strip()) > 20
            has_citations = bool(self.EVIDENCE_PATTERN.search(section_body))

            if has_content and not has_citations:
                uncited.append(section_title)

        return uncited
