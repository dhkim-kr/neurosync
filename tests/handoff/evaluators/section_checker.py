"""Section presence checker for handoff health reports."""

from __future__ import annotations

import re

from pydantic import BaseModel, Field


class SectionCheckResult(BaseModel):
    """Result of checking required sections in a handoff report."""

    present: list[str] = Field(default_factory=list, description="Sections found in the report")
    missing: list[str] = Field(default_factory=list, description="Sections not found in the report")
    total: int = Field(default=0, description="Total required sections checked")
    passed: bool = Field(default=False, description="True if present >= expected minimum")


class SectionChecker:
    """Checks that a handoff report contains the required section headers.

    Uses flexible Korean keyword matching against markdown headers.
    """

    REQUIRED_SECTIONS: list[str] = [
        "요약",        # Summary / One-line Summary
        "주호소",      # Chief Complaint
        "현병력",      # History of Present Illness
        "주요 증상",   # Key Symptoms
        "PHQ-9",       # PHQ-9 score section
        "위험",        # Risk & Safety Flags
        "약물",        # Medication
        "문서",        # Uploaded Documents
        "종단",        # Longitudinal Delta
        "누락",        # Missing Information
        "근거",        # Evidence Table
    ]

    # Header pattern: lines starting with one or more '#' characters
    _HEADER_RE = re.compile(r"(?m)^#{1,4}\s+(.+)$")

    def check(
        self,
        report_markdown: str,
        min_sections: int = 9,
    ) -> SectionCheckResult:
        """Check which required sections are present in the report.

        Args:
            report_markdown: The handoff report in markdown format.
            min_sections: Minimum number of sections required to pass.

        Returns:
            SectionCheckResult with present/missing lists and pass status.
        """
        if not report_markdown or not report_markdown.strip():
            return SectionCheckResult(
                present=[],
                missing=list(self.REQUIRED_SECTIONS),
                total=len(self.REQUIRED_SECTIONS),
                passed=False,
            )

        # Extract all header texts from the report
        headers = self._HEADER_RE.findall(report_markdown)
        # Also check the full report text for inline mentions (some reports
        # use bold or other formatting instead of proper headers)
        search_text = report_markdown.lower()

        present: list[str] = []
        missing: list[str] = []

        for section_keyword in self.REQUIRED_SECTIONS:
            keyword_lower = section_keyword.lower()
            found = False

            # Check headers first
            for header in headers:
                if keyword_lower in header.lower():
                    found = True
                    break

            # Fallback: check if keyword appears anywhere in the report
            if not found and keyword_lower in search_text:
                found = True

            if found:
                present.append(section_keyword)
            else:
                missing.append(section_keyword)

        return SectionCheckResult(
            present=present,
            missing=missing,
            total=len(self.REQUIRED_SECTIONS),
            passed=len(present) >= min_sections,
        )
