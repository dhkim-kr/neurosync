"""Generate result.md, discussion.md, version.md, error.md from matrix results."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tests.handoff.evaluators.composite import HandoffEvalResult


class ReportGenerator:
    """Generates markdown report files from matrix runner results."""

    def __init__(self, results: list[HandoffEvalResult], metadata: dict[str, Any]):
        self.results = results
        self.meta = metadata
        self.timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        self.failures = [r for r in results if not r.overall_pass]
        self.passes = [r for r in results if r.overall_pass]

    def write_all(self, output_dir: Path) -> None:
        """Write all report files to output_dir."""
        output_dir.mkdir(parents=True, exist_ok=True)

        (output_dir / "result.md").write_text(self.generate_result_md(), encoding="utf-8")
        (output_dir / "discussion.md").write_text(self.generate_discussion_md(), encoding="utf-8")
        (output_dir / "version.md").write_text(self.generate_version_md(), encoding="utf-8")

        if self.failures:
            (output_dir / "error.md").write_text(self.generate_error_md(), encoding="utf-8")

    def generate_result_md(self) -> str:
        """EXP entry with results table."""
        lines = [
            f"# Handoff Report Test Matrix — Results",
            "",
            f"> **Run**: {self.timestamp}",
            f"> **Pass rate**: {len(self.passes)}/{len(self.results)} "
            f"({len(self.passes)/len(self.results)*100:.0f}%)",
            "",
            "## Matrix Results",
            "",
            "| Case | Label | Pass | Sections | Evidence | Violations | Latency | Model |",
            "|------|-------|------|----------|----------|------------|---------|-------|",
        ]

        for r in self.results:
            status = "✅" if r.overall_pass else "❌"
            sections = f"{len(r.sections.present)}/{r.sections.total}" if r.sections else "N/A"
            evidence = str(r.evidence.citation_count) if r.evidence else "N/A"
            violations = "0" if r.violations and r.violations.passed else (
                str(len(r.violations.diagnosis_violations) + len(r.violations.treatment_violations))
                if r.violations else "N/A"
            )
            lines.append(
                f"| {r.case_id} | {r.case_name} | {status} | {sections} | "
                f"{evidence} | {violations} | {r.latency_ms:.0f}ms | {r.model_used} |"
            )

        lines.extend([
            "",
            "## Per-Case Details",
            "",
        ])

        for r in self.results:
            lines.append(f"### {r.case_id}: {r.case_name}")
            lines.append("")

            if r.sections:
                lines.append(f"- **Sections**: {len(r.sections.present)}/{r.sections.total}")
                if r.sections.missing:
                    lines.append(f"  - Missing: {', '.join(r.sections.missing)}")

            if r.evidence:
                lines.append(f"- **Evidence citations**: {r.evidence.citation_count}")
                if r.evidence.dangling_refs:
                    lines.append(f"  - Dangling: {', '.join(r.evidence.dangling_refs)}")

            if r.safety:
                lines.append(f"- **Safety**: risk={r.safety.risk_level}, "
                             f"crisis={r.safety.crisis_activated}, rule={r.safety.rule_triggered}")
                lines.append(f"  - Categories: {', '.join(r.safety.categories)}")

            if r.longitudinal:
                lines.append(f"- **Longitudinal**: delta_section={r.longitudinal.has_delta_section}")
                lines.append(f"  - First evidence: {r.longitudinal.first_evidence_count}, "
                             f"Longitudinal evidence: {r.longitudinal.longitudinal_evidence_count}")
                lines.append(f"  - First missing: {r.longitudinal.first_missing_slots}, "
                             f"Longitudinal missing: {r.longitudinal.longitudinal_missing_slots}")

            lines.append(f"- **Latency**: {r.latency_ms:.0f}ms | **Model**: {r.model_used}")
            lines.append("")

        return "\n".join(lines)

    def generate_discussion_md(self) -> str:
        """Analysis of findings, open issues, recommendations."""
        lines = [
            "# Handoff Report Test Matrix — Discussion",
            "",
            f"> **Run**: {self.timestamp}",
            "",
            "## Current State",
            "",
            f"- **Pass rate**: {len(self.passes)}/{len(self.results)} "
            f"({len(self.passes)/len(self.results)*100:.0f}%)",
            f"- **Failures**: {len(self.failures)}",
            "",
        ]

        # Safety analysis
        safety_results = [r for r in self.results if r.safety]
        if safety_results:
            lines.extend([
                "## Safety Guard Analysis",
                "",
            ])
            for r in safety_results:
                lines.append(f"- **{r.case_id}**: risk={r.safety.risk_level}, "
                             f"crisis={r.safety.crisis_activated}, "
                             f"passed={r.safety.passed}")
            lines.append("")

        # Longitudinal analysis
        longi_results = [r for r in self.results if r.longitudinal]
        if longi_results:
            lines.extend([
                "## First Chat vs Longitudinal Comparison",
                "",
            ])
            for r in longi_results:
                lines.append(f"- **{r.case_id}**: "
                             f"evidence {r.longitudinal.first_evidence_count} → "
                             f"{r.longitudinal.longitudinal_evidence_count}, "
                             f"missing {r.longitudinal.first_missing_slots} → "
                             f"{r.longitudinal.longitudinal_missing_slots}")
            lines.append("")

        # Failure analysis
        if self.failures:
            lines.extend([
                "## Failure Analysis",
                "",
            ])
            for r in self.failures:
                lines.append(f"### {r.case_id}: {r.case_name}")
                if r.sections and not r.sections.passed:
                    lines.append(f"- Section check failed — missing: {r.sections.missing}")
                if r.violations and not r.violations.passed:
                    lines.append(f"- Violations: {len(r.violations.diagnosis_violations)} diagnosis, "
                                 f"{len(r.violations.treatment_violations)} treatment")
                if r.safety and not r.safety.passed:
                    lines.append(f"- Safety check failed")
                lines.append("")

        # Recommendations
        lines.extend([
            "## Recommendations",
            "",
            "- [ ] Expand test matrix to include more virtual patients (target: 10+)",
            "- [ ] Add cross-vendor comparison (Solar Pro3 vs K-EXAONE vs A.X)",
            "- [ ] Integrate into CI pipeline as regression guard",
            "- [ ] Add latency SLA assertions (p95 < 30s for handoff)",
            "",
        ])

        return "\n".join(lines)

    def generate_version_md(self) -> str:
        """Archive entry for this test run."""
        lines = [
            "# Handoff Report Test Matrix — Version History",
            "",
            f"## VER-MATRIX-001 ({self.timestamp})",
            "",
            f"- **Pass rate**: {len(self.passes)}/{len(self.results)}",
            f"- **Test cases**: {', '.join(r.case_id for r in self.results)}",
            f"- **Models used**: {', '.join(set(r.model_used for r in self.results))}",
            "",
            "### Results Summary",
            "",
            "| Case | Pass | Latency |",
            "|------|------|---------|",
        ]
        for r in self.results:
            status = "PASS" if r.overall_pass else "FAIL"
            lines.append(f"| {r.case_id} {r.case_name} | {status} | {r.latency_ms:.0f}ms |")

        lines.extend([
            "",
            "### Architecture Decisions",
            "",
            "- ADR-MATRIX-001: Direct agent invocation (not HTTP) for typed I/O and full field access",
            "- ADR-MATRIX-002: Session-scoped fixtures to avoid per-test adapter cold starts",
            "- ADR-MATRIX-003: Composite evaluator pattern with independent checkers",
            "",
        ])

        return "\n".join(lines)

    def generate_error_md(self) -> str:
        """Bug entries for failures."""
        lines = [
            "# Handoff Report Test Matrix — Errors",
            "",
            f"> **Run**: {self.timestamp}",
            "",
        ]

        for i, r in enumerate(self.failures, start=1):
            lines.extend([
                f"## BUG-MATRIX-{i:03d}: {r.case_id} {r.case_name} — FAIL",
                "",
                f"- **Case**: {r.case_id}",
                f"- **Model**: {r.model_used}",
                f"- **Latency**: {r.latency_ms:.0f}ms",
                "",
            ])

            if r.sections and not r.sections.passed:
                lines.append(f"### Section Check Failure")
                lines.append(f"Missing sections: {', '.join(r.sections.missing)}")
                lines.append("")

            if r.violations and not r.violations.passed:
                lines.append(f"### Violation Check Failure")
                for v in r.violations.diagnosis_violations:
                    lines.append(f"- DIAGNOSIS: `{v.get('matched_text', '')}` in {v.get('location', '?')}")
                for v in r.violations.treatment_violations:
                    lines.append(f"- TREATMENT: `{v.get('matched_text', '')}` in {v.get('location', '?')}")
                lines.append("")

            if r.safety and not r.safety.passed:
                lines.append(f"### Safety Check Failure")
                lines.append(f"- Expected crisis={r.safety.crisis_activated}, risk={r.safety.risk_level}")
                lines.append("")

            lines.append("---")
            lines.append("")

        return "\n".join(lines)
