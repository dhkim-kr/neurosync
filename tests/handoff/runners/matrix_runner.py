"""Matrix runner — runs all 6 test cases, evaluates, and generates reports.

Usage:
    cd apps/ai-server
    python -m tests.handoff.runners.matrix_runner [--vendor solar-pro3] [--output-dir docs/]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Ensure project root is importable
PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "apps" / "ai-server"))

from src.config import Settings
from src.routing.model_router import ModelRouter
from src.prompts.loader import PromptLoader
from src.agents.handoff_generator import HandoffGeneratorAgent
from src.agents.safety_classifier import SafetyClassifierAgent
from src.agents.evidence_verifier import EvidenceVerifierAgent, EvidenceVerifierInput
from src.adapters.solar_pro3 import SolarPro3Adapter
from src.adapters.k_exaone import KExaoneAdapter
from src.adapters.ak_llm import AkLlmAdapter

from tests.handoff.fixtures.patients import (
    load_fixture,
    fixture_to_handoff_input,
    fixture_to_safety_input,
)
from tests.handoff.evaluators.composite import CompositeEvaluator, HandoffEvalResult
from tests.handoff.reports.generator import ReportGenerator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

CASE_MATRIX = [
    {"case_id": "TC-001", "fixture": "mild_first_visit.json", "label": "경증 초진", "type": "handoff"},
    {"case_id": "TC-002", "fixture": "mild_revisit.json", "label": "경증 재진", "type": "handoff"},
    {"case_id": "TC-003", "fixture": "severe_first_visit.json", "label": "중증 초진", "type": "handoff"},
    {"case_id": "TC-004", "fixture": "severe_revisit.json", "label": "중증 재진", "type": "handoff"},
    {"case_id": "TC-005", "fixture": "safety_trigger.json", "label": "Safety guard", "type": "safety"},
    {"case_id": "TC-006", "fixture": "longitudinal_pair.json", "label": "First vs longitudinal", "type": "longitudinal"},
]


def _bootstrap_agents() -> tuple[HandoffGeneratorAgent, SafetyClassifierAgent, EvidenceVerifierAgent]:
    """Create agent instances with real LLM adapters."""
    settings = Settings()
    router = ModelRouter(settings.resolve_registry_path())

    adapters = {}
    if settings.upstage_api_key:
        adapters["solar-pro3"] = SolarPro3Adapter(settings)
    if settings.lg_k_exaone_api_key:
        adapters["k-exaone"] = KExaoneAdapter(settings)
    if settings.skt_a_x_api_key:
        adapters["ak-llm"] = AkLlmAdapter(settings)

    if not adapters:
        logger.error("No LLM API keys configured. Set UPSTAGE_API_KEY or similar.")
        sys.exit(1)

    router.register_adapters(adapters)
    prompt_loader = PromptLoader(settings.resolve_prompts_dir())

    return (
        HandoffGeneratorAgent(model_router=router, prompt_loader=prompt_loader),
        SafetyClassifierAgent(model_router=router, prompt_loader=prompt_loader),
        EvidenceVerifierAgent(),
    )


async def run_handoff_case(
    fixture: dict[str, Any],
    handoff_agent: HandoffGeneratorAgent,
    evidence_verifier: EvidenceVerifierAgent,
    safety_agent: SafetyClassifierAgent,
    evaluator: CompositeEvaluator,
) -> HandoffEvalResult:
    """Run a standard handoff case (TC-001 to TC-004)."""
    inp = fixture_to_handoff_input(fixture)
    expected = fixture["expected"]

    # Optional safety pre-check
    safety_output = None
    if "safety_input" in fixture:
        try:
            safety_inp = fixture_to_safety_input(fixture)
            safety_output = await safety_agent.run(safety_inp)
        except Exception as e:
            logger.warning("Safety pre-check failed: %s", e)

    # Generate handoff
    output = await handoff_agent.run(inp)

    # Verify evidence
    verifier_inp = EvidenceVerifierInput(
        session_id=inp.session_id,
        report_markdown=output.report_markdown,
        evidence_packets=output.evidence_packets,
    )
    verifier_output = await evidence_verifier.run(verifier_inp)

    # Evaluate
    result = evaluator.evaluate(
        case_id=fixture["case_id"],
        case_name=fixture["case_name"],
        handoff_output=output,
        expected=expected,
        safety_output=safety_output,
        is_revisit=not inp.is_first_visit,
    )

    logger.info(
        "[%s] %s — pass=%s, sections=%d/%d, evidence=%d, violations=%d, latency=%.0fms",
        result.case_id, result.case_name, result.overall_pass,
        len(result.sections.present), result.sections.total,
        result.evidence.citation_count,
        len(result.violations.diagnosis_violations) + len(result.violations.treatment_violations),
        result.latency_ms,
    )
    return result


async def run_safety_case(
    fixture: dict[str, Any],
    safety_agent: SafetyClassifierAgent,
    evaluator: CompositeEvaluator,
) -> HandoffEvalResult:
    """Run safety guard test case (TC-005)."""
    safety_inp = fixture_to_safety_input(fixture)
    output = await safety_agent.run(safety_inp)

    from tests.handoff.evaluators.safety_checker import SafetyChecker
    checker = SafetyChecker()
    safety_result = checker.check(output, fixture["expected"])

    return HandoffEvalResult(
        case_id=fixture["case_id"],
        case_name=fixture["case_name"],
        sections=None,
        evidence=None,
        violations=None,
        risk=None,
        safety=safety_result,
        longitudinal=None,
        overall_pass=safety_result.passed,
        latency_ms=output.latency_ms,
        model_used=output.model_used,
    )


async def run_longitudinal_case(
    fixture: dict[str, Any],
    handoff_agent: HandoffGeneratorAgent,
    evidence_verifier: EvidenceVerifierAgent,
    evaluator: CompositeEvaluator,
) -> HandoffEvalResult:
    """Run longitudinal comparison case (TC-006)."""
    from src.schemas.handoff import HandoffInput, SlotData, ScaleScore

    results = {}
    for key in ("first_chat_input", "longitudinal_input"):
        raw = fixture[key]
        inp = HandoffInput(
            session_id=raw["session_id"],
            slots=SlotData(**raw["slots"]),
            conversation_history=raw["conversation_history"],
            scale_scores=[ScaleScore(**s) for s in raw.get("scale_scores", [])],
            risk_events=raw.get("risk_events", []),
            ocr_documents=raw.get("ocr_documents", []),
            prior_handoff=raw.get("prior_handoff"),
            is_first_visit=raw.get("is_first_visit", True),
        )
        output = await handoff_agent.run(inp)
        results[key] = output

    first_out = results["first_chat_input"]
    longi_out = results["longitudinal_input"]

    expected = fixture["expected"]
    checks_passed = True
    failures = []

    if expected.get("longitudinal_has_more_evidence", True):
        if len(longi_out.evidence_packets) <= len(first_out.evidence_packets):
            checks_passed = False
            failures.append("Longitudinal should have more evidence")

    if expected.get("longitudinal_missing_slots_lt_first", True):
        if len(longi_out.missing_slots) >= len(first_out.missing_slots):
            checks_passed = False
            failures.append("Longitudinal should have fewer missing slots")

    if expected.get("longitudinal_has_delta_section", True):
        report = longi_out.report_markdown.lower()
        if not any(kw in report for kw in ["종단", "변화", "이전", "delta", "previous", "비교"]):
            checks_passed = False
            failures.append("Longitudinal report missing delta section")

    from tests.handoff.evaluators.longitudinal_checker import LongitudinalCheckResult
    longi_result = LongitudinalCheckResult(
        has_delta_section=any(
            kw in longi_out.report_markdown.lower()
            for kw in ["종단", "변화", "이전", "delta", "previous", "비교"]
        ),
        delta_direction=None,
        score_comparison_found=False,
        first_evidence_count=len(first_out.evidence_packets),
        longitudinal_evidence_count=len(longi_out.evidence_packets),
        first_missing_slots=len(first_out.missing_slots),
        longitudinal_missing_slots=len(longi_out.missing_slots),
        passed=checks_passed,
    )

    return HandoffEvalResult(
        case_id=fixture["case_id"],
        case_name=fixture["case_name"],
        sections=None,
        evidence=None,
        violations=None,
        risk=None,
        safety=None,
        longitudinal=longi_result,
        overall_pass=checks_passed,
        latency_ms=first_out.latency_ms + longi_out.latency_ms,
        model_used=longi_out.model_used,
    )


async def run_matrix() -> list[HandoffEvalResult]:
    """Run the full 6-case test matrix."""
    handoff_agent, safety_agent, evidence_verifier = _bootstrap_agents()
    evaluator = CompositeEvaluator()
    results: list[HandoffEvalResult] = []

    for case in CASE_MATRIX:
        logger.info("=" * 60)
        logger.info("Running %s: %s", case["case_id"], case["label"])
        logger.info("=" * 60)

        fixture = load_fixture(case["fixture"])
        started = time.monotonic()

        try:
            if case["type"] == "handoff":
                result = await run_handoff_case(
                    fixture, handoff_agent, evidence_verifier, safety_agent, evaluator,
                )
            elif case["type"] == "safety":
                result = await run_safety_case(fixture, safety_agent, evaluator)
            elif case["type"] == "longitudinal":
                result = await run_longitudinal_case(
                    fixture, handoff_agent, evidence_verifier, evaluator,
                )
            else:
                raise ValueError(f"Unknown case type: {case['type']}")

            results.append(result)

        except Exception as e:
            elapsed = (time.monotonic() - started) * 1000
            logger.error("[%s] FAILED: %s", case["case_id"], e, exc_info=True)
            results.append(HandoffEvalResult(
                case_id=case["case_id"],
                case_name=case["label"],
                sections=None,
                evidence=None,
                violations=None,
                risk=None,
                safety=None,
                longitudinal=None,
                overall_pass=False,
                latency_ms=elapsed,
                model_used="error",
            ))

    return results


def main():
    parser = argparse.ArgumentParser(description="Handoff Report Test Matrix Runner")
    parser.add_argument(
        "--output-dir",
        default=str(PROJECT_ROOT / "docs"),
        help="Directory for report output files (default: docs/)",
    )
    args = parser.parse_args()

    results = asyncio.run(run_matrix())

    # Summary table
    print("\n" + "=" * 80)
    print("MATRIX RESULTS SUMMARY")
    print("=" * 80)
    print(f"{'Case':<10} {'Label':<25} {'Pass':<6} {'Latency':<10} {'Model'}")
    print("-" * 80)
    for r in results:
        status = "PASS" if r.overall_pass else "FAIL"
        print(f"{r.case_id:<10} {r.case_name:<25} {status:<6} {r.latency_ms:>7.0f}ms  {r.model_used}")

    passed = sum(1 for r in results if r.overall_pass)
    total = len(results)
    print("-" * 80)
    print(f"Total: {passed}/{total} passed")

    # Generate report files
    output_dir = Path(args.output_dir)
    generator = ReportGenerator(results, {
        "run_timestamp": datetime.now(timezone.utc).isoformat(),
        "total_cases": total,
        "passed_cases": passed,
    })
    generator.write_all(output_dir)
    print(f"\nReports written to {output_dir}/")

    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
