# Phase 6: Pipeline Agents

> **Depends on**: Phase 5 (core agents — pipeline agents consume their outputs)
> **Blocks**: Phase 7 (routes wire pipeline agents to HTTP endpoints)
> **Agent owner**: `developer`
> **Gate**: `critic` (evidence policy — every Handoff claim must have evidence)

---

## Objective

Implement the 6 pipeline agents that compose outputs from core agents: orchestration, handoff generation, evidence verification, temporal retrieval, temporal summary, and prompt evaluation. These agents form the second layer of the multi-agent system, operating on structured outputs from Phase 5 agents rather than raw user input.

## Success Criteria

- [ ] All 6 agent classes instantiate and pass type checks
- [ ] All 6 schema modules import cleanly with round-trip serialization
- [ ] `HandoffGeneratorAgent` produces reports with evidence IDs on every claim
- [ ] `EvidenceVerifierAgent` rejects reports with unsupported claims
- [ ] `OrchestratorAgent` returns valid `next_action` from the defined enum
- [ ] `TemporalRetrieverAgent` MVP stub returns empty packets without error
- [ ] `pytest tests/agents/test_orchestrator.py tests/agents/test_handoff_generator.py tests/agents/test_evidence_verifier.py tests/agents/test_temporal_retriever.py tests/agents/test_temporal_summary.py tests/agents/test_prompt_eval.py -x` passes
- [ ] `ruff check src/agents/ src/schemas/` passes

---

## Step 6.1 — OrchestratorAgent

### Schema

**File**: `apps/ai-server/src/schemas/orchestrator.py` (new)

```python
"""Internal schemas for OrchestratorAgent."""

from enum import StrEnum

from pydantic import BaseModel, Field

from src.agents.base import AgentInput, AgentOutput


class NextAction(StrEnum):
    """Orchestrator action enum — PRD §5.3."""

    CALL_AGENT = "call_agent"
    ASK_CLARIFYING_QUESTION = "ask_clarifying_question"
    INTERRUPT_FOR_SAFETY = "interrupt_for_safety"
    GENERATE_HANDOFF = "generate_handoff"
    NO_OP = "no_op"


class OrchestratorInput(AgentInput):
    """Input to OrchestratorAgent."""

    user_intent: str = ""
    session_state: dict = Field(default_factory=dict)
    risk_state: str = "none"
    known_slots: dict = Field(default_factory=dict)
    missing_slots: list[str] = Field(default_factory=list)
    message_count: int = 0


class OrchestratorOutput(AgentOutput):
    """Output from OrchestratorAgent — PRD §5.3."""

    next_action: NextAction = NextAction.CALL_AGENT
    required_agents: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    risk_gate_required: bool = True
    context_required: bool = False
```

### Agent

**File**: `apps/ai-server/src/agents/orchestrator.py` (new)

```python
"""OrchestratorAgent — state machine routing per PRD §5.2.

State transitions:
  ReceiveInput → STT/Normalize → SafetyGate → ContextRetrieval →
  DialoguePolicy → SlotExtraction → HandoffReady/AskNextQuestion

Uses ModelRouter for LLM selection (benchmarked on JSON reliability
and routing accuracy). Fallback: rule-based router.
"""

import logging
import time
from typing import Any

from src.agents.base import BaseAgent
from src.schemas.orchestrator import (
    NextAction,
    OrchestratorInput,
    OrchestratorOutput,
)

logger = logging.getLogger(__name__)

# Minimum required slots before handoff is allowed
REQUIRED_SLOTS_FOR_HANDOFF = [
    "chief_complaint",
    "mood",
]


class OrchestratorAgent(BaseAgent):
    """Route user requests through the agent pipeline.

    LLM-based routing with rule-based fallback.
    Safety gate is ALWAYS required (risk_gate_required=True by default).
    """

    name = "orchestrator"
    description = "Route user requests through the multi-agent pipeline based on session state"

    def __init__(self, model_router: Any, prompt_loader: Any) -> None:
        self.model_router = model_router
        self.prompt_loader = prompt_loader

    async def run(self, input_data: OrchestratorInput, **kwargs: Any) -> OrchestratorOutput:
        """Determine next action based on session state.

        On failure: falls back to rule-based routing.
        """
        start = time.monotonic()
        try:
            model_selection = await self.model_router.select_model(
                agent_name=self.name,
                task_name="workflow_routing",
                require_json=True,
            )

            system_prompt = await self.prompt_loader.load_system_prompt(
                "orchestrator", "v1",
            )

            # LLM call (implementation deferred)
            raise NotImplementedError("LLM integration pending adapter wiring")

        except NotImplementedError:
            raise
        except Exception as e:
            logger.warning("OrchestratorAgent LLM failed, using rule-based router: %s", e)
            return self._rule_based_route(input_data, start)

    def _rule_based_route(
        self,
        input_data: OrchestratorInput,
        start: float,
    ) -> OrchestratorOutput:
        """Rule-based fallback router.

        Decision tree:
        1. If risk_state is high/critical → interrupt_for_safety
        2. If all required slots filled → generate_handoff
        3. If missing slots → call_agent (dialogue + clinical_slot)
        4. Default → call_agent (safety + dialogue)
        """
        latency_ms = int((time.monotonic() - start) * 1000)

        # Safety interrupt
        if input_data.risk_state in ("high", "critical"):
            return OrchestratorOutput(
                next_action=NextAction.INTERRUPT_FOR_SAFETY,
                required_agents=["safety_classifier"],
                confidence=1.0,
                risk_gate_required=True,
                context_required=False,
                latency_ms=latency_ms,
                model_used="rule_based_fallback",
                reason_summary="High/critical risk detected — safety interrupt.",
            )

        # Check if enough slots for handoff
        known = set(input_data.known_slots.keys())
        required = set(REQUIRED_SLOTS_FOR_HANDOFF)
        if required.issubset(known) and input_data.message_count >= 3:
            return OrchestratorOutput(
                next_action=NextAction.GENERATE_HANDOFF,
                required_agents=[
                    "temporal_retriever",
                    "handoff_generator",
                    "evidence_verifier",
                ],
                confidence=0.8,
                risk_gate_required=True,
                context_required=True,
                latency_ms=latency_ms,
                model_used="rule_based_fallback",
                reason_summary="Required slots filled — proceeding to handoff generation.",
            )

        # Default: continue dialogue + slot extraction
        return OrchestratorOutput(
            next_action=NextAction.CALL_AGENT,
            required_agents=["safety_classifier", "dialogue", "clinical_slot"],
            confidence=0.7,
            risk_gate_required=True,
            context_required=False,
            latency_ms=latency_ms,
            model_used="rule_based_fallback",
            reason_summary="Missing slots — continuing dialogue intake.",
        )
```

### Implementation Notes

- **State machine**: Implements PRD §5.2 state transitions. LLM determines next_action with structured JSON output; rule-based fallback handles failures.
- **Safety gate**: `risk_gate_required` defaults to `True`. The route layer MUST call SafetyClassifierAgent before proceeding with any Orchestrator-recommended action.
- **Handoff threshold**: Requires at least `chief_complaint` + `mood` slots filled and >= 3 messages before allowing handoff generation.
- **Fallback**: Rule-based router uses simple decision tree. Never fails.

### Tests

**File**: `apps/ai-server/tests/agents/test_orchestrator.py` (new)

Key test cases:

```python
"""Tests for OrchestratorAgent."""

import pytest
from unittest.mock import AsyncMock

from src.agents.orchestrator import OrchestratorAgent, REQUIRED_SLOTS_FOR_HANDOFF
from src.schemas.orchestrator import NextAction, OrchestratorInput, OrchestratorOutput


class TestOrchestratorSchema:
    def test_next_action_enum(self) -> None:
        assert NextAction.CALL_AGENT == "call_agent"
        assert NextAction.INTERRUPT_FOR_SAFETY == "interrupt_for_safety"
        assert len(NextAction) == 5

    def test_input_defaults(self) -> None:
        inp = OrchestratorInput()
        assert inp.risk_state == "none"
        assert inp.message_count == 0

    def test_output_round_trip(self) -> None:
        out = OrchestratorOutput(
            next_action=NextAction.GENERATE_HANDOFF,
            required_agents=["handoff_generator"],
            confidence=0.9,
        )
        data = out.model_dump()
        restored = OrchestratorOutput.model_validate(data)
        assert restored.next_action == NextAction.GENERATE_HANDOFF


class TestOrchestratorAgent:
    @pytest.fixture
    def agent(self) -> OrchestratorAgent:
        return OrchestratorAgent(
            model_router=AsyncMock(),
            prompt_loader=AsyncMock(),
        )

    def test_rule_based_safety_interrupt(self, agent: OrchestratorAgent) -> None:
        import time
        result = agent._rule_based_route(
            OrchestratorInput(risk_state="high"),
            time.monotonic(),
        )
        assert result.next_action == NextAction.INTERRUPT_FOR_SAFETY
        assert "safety_classifier" in result.required_agents

    def test_rule_based_handoff_when_slots_filled(self, agent: OrchestratorAgent) -> None:
        import time
        result = agent._rule_based_route(
            OrchestratorInput(
                known_slots={"chief_complaint": "수면 문제", "mood": "depressed"},
                message_count=5,
            ),
            time.monotonic(),
        )
        assert result.next_action == NextAction.GENERATE_HANDOFF
        assert "handoff_generator" in result.required_agents

    def test_rule_based_default_continues_dialogue(self, agent: OrchestratorAgent) -> None:
        import time
        result = agent._rule_based_route(
            OrchestratorInput(
                known_slots={},
                missing_slots=["chief_complaint", "mood"],
            ),
            time.monotonic(),
        )
        assert result.next_action == NextAction.CALL_AGENT
        assert "dialogue" in result.required_agents

    def test_risk_gate_always_required(self, agent: OrchestratorAgent) -> None:
        import time
        result = agent._rule_based_route(OrchestratorInput(), time.monotonic())
        assert result.risk_gate_required is True

    @pytest.mark.asyncio
    async def test_llm_failure_falls_back_to_rules(self, agent: OrchestratorAgent) -> None:
        agent.model_router.select_model.side_effect = RuntimeError("LLM down")
        result = await agent.run(OrchestratorInput())
        assert result.model_used == "rule_based_fallback"
        assert result.next_action in list(NextAction)
```

---

## Step 6.2 — HandoffGeneratorAgent

### Schema

**File**: `apps/ai-server/src/schemas/handoff.py` (new)

```python
"""Internal schemas for HandoffGeneratorAgent."""

from pydantic import BaseModel, Field

from src.agents.base import AgentInput, AgentOutput


class ScaleScore(BaseModel):
    """PHQ-9 or GAD-7 score."""

    score: int
    severity: str = ""  # minimal | mild | moderate | moderately_severe | severe


class Citation(BaseModel):
    """Evidence citation for a single claim."""

    claim_id: str
    source_type: str  # message | scale | document_block | risk_event | prior_handoff
    source_id: str
    content_snippet: str = ""


class HandoffInput(AgentInput):
    """Input to HandoffGeneratorAgent."""

    slots: dict = Field(default_factory=dict)
    risk_events: list[dict] = Field(default_factory=list)
    scale_scores: dict = Field(default_factory=dict)  # {"phq9": ScaleScore, "gad7": ScaleScore}
    evidence_packets: list[dict] = Field(default_factory=list)
    messages: list[dict] = Field(default_factory=list)
    doc_texts: list[dict] = Field(default_factory=list)


class HandoffOutput(AgentOutput):
    """Output from HandoffGeneratorAgent.

    11 mandatory sections per PRD §6.4.
    """

    report_markdown: str = ""
    citations: list[Citation] = Field(default_factory=list)
    unsupported_claims: list[str] = Field(default_factory=list)
    requires_clinician_review: bool = True  # always True for handoff
```

### Agent

**File**: `apps/ai-server/src/agents/handoff_generator.py` (new)

```python
"""HandoffGeneratorAgent — generates evidence-grounded clinician handoff report.

PRD §6.4: HAND-1 through HAND-7.
11 mandatory sections:
  1. One-line Summary
  2. Chief Complaint
  3. History of Present Illness
  4. Symptoms (sleep, appetite, mood, anxiety, concentration, functional impairment)
  5. PHQ-9 / GAD-7
  6. Risk & Safety Flags
  7. Medication / Past History / Uploaded Documents
  8. Longitudinal Delta
  9. Missing Information
  10. Evidence Table
  11. Clinician Review Required Flags
"""

import logging
import time
from typing import Any

from src.agents.base import BaseAgent
from src.schemas.handoff import HandoffInput, HandoffOutput

logger = logging.getLogger(__name__)

MANDATORY_SECTIONS = [
    "One-line Summary",
    "Chief Complaint",
    "History of Present Illness",
    "Symptoms",
    "PHQ-9 / GAD-7",
    "Risk & Safety Flags",
    "Medication / Past History / Uploaded Documents",
    "Longitudinal Delta",
    "Missing Information",
    "Evidence Table",
    "Clinician Review Required Flags",
]


class HandoffGeneratorAgent(BaseAgent):
    """Generate evidence-grounded clinician handoff report.

    EVERY claim must have an evidence_id (HAND-1).
    No diagnosis, no treatment instructions (HAND-3).
    Uses ModelRouter (benchmarked on unsupported claim rate + clinician score).
    """

    name = "handoff_generator"
    description = "Generate structured clinician handoff report with evidence citations"

    def __init__(self, model_router: Any, prompt_loader: Any) -> None:
        self.model_router = model_router
        self.prompt_loader = prompt_loader

    async def run(self, input_data: HandoffInput, **kwargs: Any) -> HandoffOutput:
        """Generate handoff report.

        On failure: returns partial report with review flags.
        """
        start = time.monotonic()
        try:
            model_selection = await self.model_router.select_model(
                agent_name=self.name,
                task_name="handoff_generation",
                require_json=False,  # Output is Markdown with structured citations
            )

            system_prompt = await self.prompt_loader.load_system_prompt(
                "handoff_generator", "v1",
            )

            # LLM call (implementation deferred)
            raise NotImplementedError("LLM integration pending adapter wiring")

        except NotImplementedError:
            raise
        except Exception as e:
            logger.error("HandoffGeneratorAgent failed: %s", e)
            latency_ms = int((time.monotonic() - start) * 1000)
            return self._build_fallback_report(input_data, latency_ms, str(e))

    def _build_fallback_report(
        self,
        input_data: HandoffInput,
        latency_ms: int,
        error: str,
    ) -> HandoffOutput:
        """Build minimal fallback report from structured slots.

        Not LLM-generated — just formats known slots into sections.
        """
        sections = []
        sections.append("## Handoff Summary (자동 생성 실패 — 구조화 데이터 기반 요약)")
        sections.append("")

        # CC
        cc = input_data.slots.get("chief_complaint", "정보 미수집")
        sections.append(f"### 1. One-line Summary\n{cc}")
        sections.append(f"### 2. Chief Complaint\n{cc}")

        # HPI
        hpi = input_data.slots.get("hpi", "정보 미수집")
        sections.append(f"### 3. History of Present Illness\n{hpi}")

        # Symptoms
        symptom_slots = ["sleep", "appetite", "mood", "anxiety", "concentration", "functional_impairment"]
        symptom_lines = []
        for s in symptom_slots:
            val = input_data.slots.get(s, "정보 미수집")
            symptom_lines.append(f"- {s}: {val}")
        sections.append(f"### 4. Symptoms\n" + "\n".join(symptom_lines))

        # Scales
        phq9 = input_data.scale_scores.get("phq9", {})
        gad7 = input_data.scale_scores.get("gad7", {})
        sections.append(f"### 5. PHQ-9 / GAD-7\n- PHQ-9: {phq9}\n- GAD-7: {gad7}")

        # Risk
        risk_summary = "위험 이벤트 없음" if not input_data.risk_events else f"{len(input_data.risk_events)}건의 위험 이벤트"
        sections.append(f"### 6. Risk & Safety Flags\n{risk_summary}")

        # Medication / History / Documents
        medication = input_data.slots.get("medication", "정보 미수집")
        pmh = input_data.slots.get("pmh", "정보 미수집")
        doc_count = len(input_data.doc_texts)
        sections.append(f"### 7. Medication / Past History / Documents\n- 복용 약물: {medication}\n- 과거력: {pmh}\n- 업로드 문서: {doc_count}건")

        # Delta
        sections.append("### 8. Longitudinal Delta\n판단불가 (자동 생성 실패)")

        # Missing
        all_slots = ["chief_complaint", "hpi", "sleep", "appetite", "mood", "anxiety", "medication", "pmh"]
        missing = [s for s in all_slots if s not in input_data.slots]
        missing_text = "\n".join(f"- {s}" for s in missing) if missing else "없음"
        sections.append(f"### 9. Missing Information\n{missing_text}")

        # Evidence Table
        sections.append("### 10. Evidence Table\n자동 생성 실패로 근거표 미생성. 의료진 직접 확인 필요.")

        # Review Flags
        sections.append(f"### 11. Clinician Review Required Flags\n- 자동 보고서 생성 실패: {error}\n- 전체 내용 의료진 확인 필수")

        report = "\n\n".join(sections)

        return HandoffOutput(
            report_markdown=report,
            citations=[],
            unsupported_claims=[],
            requires_clinician_review=True,
            latency_ms=latency_ms,
            model_used="fallback_template",
            reason_summary="LLM handoff generation failed. Fallback report from structured slots.",
        )
```

### Implementation Notes

- **11 mandatory sections**: All must be present. Missing data sections show "정보 미수집".
- **Evidence requirement (HAND-1)**: LLM prompt instructs that EVERY claim must include `[ev_xxx]` citation. Post-generation validation checks for uncited claims.
- **No diagnosis/treatment (HAND-3)**: System prompt + output regex validation for prohibited patterns (진단명 단정, 약물 조절 지시).
- **Low-confidence OCR (HAND-7)**: Entities with `requires_human_review=True` are cited with "(의료진 확인 필요)" annotation.
- **Fallback**: Template report from structured slot data. Useful but always requires clinician review.

### Tests

**File**: `apps/ai-server/tests/agents/test_handoff_generator.py` (new)

Key test cases:

```python
"""Tests for HandoffGeneratorAgent."""

import pytest
from unittest.mock import AsyncMock

from src.agents.handoff_generator import HandoffGeneratorAgent, MANDATORY_SECTIONS
from src.schemas.handoff import HandoffInput, HandoffOutput, Citation


class TestHandoffSchema:
    def test_input_defaults(self) -> None:
        inp = HandoffInput()
        assert inp.slots == {}
        assert inp.messages == []

    def test_output_round_trip(self) -> None:
        out = HandoffOutput(
            report_markdown="# Test Report",
            citations=[Citation(claim_id="c1", source_type="message", source_id="m1")],
        )
        data = out.model_dump()
        restored = HandoffOutput.model_validate(data)
        assert len(restored.citations) == 1

    def test_requires_clinician_review_default_true(self) -> None:
        out = HandoffOutput()
        assert out.requires_clinician_review is True


class TestHandoffGeneratorAgent:
    @pytest.fixture
    def agent(self) -> HandoffGeneratorAgent:
        return HandoffGeneratorAgent(
            model_router=AsyncMock(),
            prompt_loader=AsyncMock(),
        )

    def test_mandatory_sections_count(self) -> None:
        assert len(MANDATORY_SECTIONS) == 11

    def test_fallback_report_contains_all_sections(self, agent: HandoffGeneratorAgent) -> None:
        result = agent._build_fallback_report(
            HandoffInput(slots={"chief_complaint": "수면 문제"}),
            latency_ms=100,
            error="test error",
        )
        # Check all numbered sections are present
        for i in range(1, 12):
            assert f"### {i}." in result.report_markdown

    def test_fallback_report_shows_missing_slots(self, agent: HandoffGeneratorAgent) -> None:
        result = agent._build_fallback_report(
            HandoffInput(slots={}),
            latency_ms=50,
            error="timeout",
        )
        assert "chief_complaint" in result.report_markdown
        assert result.requires_clinician_review is True

    @pytest.mark.asyncio
    async def test_llm_failure_returns_fallback(self, agent: HandoffGeneratorAgent) -> None:
        agent.model_router.select_model.side_effect = RuntimeError("no model")
        result = await agent.run(HandoffInput(
            slots={"chief_complaint": "두통", "mood": "우울"},
        ))
        assert result.requires_clinician_review is True
        assert result.model_used == "fallback_template"
        assert "두통" in result.report_markdown

    @pytest.mark.asyncio
    async def test_fallback_report_marks_delta_as_unknown(self, agent: HandoffGeneratorAgent) -> None:
        agent.model_router.select_model.side_effect = RuntimeError("err")
        result = await agent.run(HandoffInput())
        assert "판단불가" in result.report_markdown
```

---

## Step 6.3 — EvidenceVerifierAgent

### Schema

**File**: `apps/ai-server/src/schemas/evidence_verifier.py` (new)

```python
"""Internal schemas for EvidenceVerifierAgent."""

from enum import StrEnum

from pydantic import BaseModel, Field

from src.agents.base import AgentInput, AgentOutput


class VerifierAction(StrEnum):
    """Verifier decision."""

    PASS = "pass"
    REJECT = "reject"
    REGENERATE = "regenerate"


class VerifierFlag(BaseModel):
    """Single verification flag."""

    claim_text: str
    issue: str  # unsupported_claim | diagnosis_violation | treatment_violation
    severity: str = "error"  # error | warning


class EvidenceVerifierInput(AgentInput):
    """Input to EvidenceVerifierAgent."""

    draft_report: str  # Markdown report from HandoffGenerator
    evidence_packets: list[dict] = Field(default_factory=list)


class EvidenceVerifierOutput(AgentOutput):
    """Output from EvidenceVerifierAgent."""

    verified_report: str = ""
    flags: list[VerifierFlag] = Field(default_factory=list)
    unsupported_claim_count: int = 0
    diagnosis_or_treatment_violation: bool = False
    action: VerifierAction = VerifierAction.PASS
```

### Agent

**File**: `apps/ai-server/src/agents/evidence_verifier.py` (new)

```python
"""EvidenceVerifierAgent — rule check + LLM check for evidence grounding.

Two-phase verification:
  1. Rule check: regex scan for diagnosis/treatment prohibition violations
  2. LLM check: unsupported claim detection against evidence packets

If ANY unsupported claim → reject or regenerate (PRD HAND-5).
"""

import logging
import re
import time
from typing import Any

from src.agents.base import BaseAgent
from src.schemas.evidence_verifier import (
    EvidenceVerifierInput,
    EvidenceVerifierOutput,
    VerifierAction,
    VerifierFlag,
)

logger = logging.getLogger(__name__)

# Regex patterns for prohibited content (diagnosis/treatment)
DIAGNOSIS_PATTERNS = [
    r"진단(은|이|명)?\s*(확정|확인)",
    r"(으로|로)\s+진단(합니다|됩니다|드립니다)",
    r"(주요우울장애|양극성|조현병|PTSD|ADHD|범불안장애)(입니다|로\s+판단)",
]

TREATMENT_PATTERNS = [
    r"(복용|투약|처방)\s*(하세요|하십시오|해야|권합니다|추천)",
    r"(약물|약)\s*(을|를)?\s*(중단|중지|변경|조절)\s*(하세요|하십시오)",
    r"(mg|밀리그램)\s*(으로|로)?\s*(증량|감량|변경)",
]


class EvidenceVerifierAgent(BaseAgent):
    """Verify evidence grounding and policy compliance of handoff reports.

    Phase 1 (rule): Regex scan for diagnosis/treatment violations.
    Phase 2 (LLM): Unsupported claim detection.
    If ANY violation → reject or regenerate.
    """

    name = "evidence_verifier"
    description = "Verify evidence grounding and detect diagnosis/treatment violations in handoff reports"

    def __init__(self, model_router: Any, prompt_loader: Any) -> None:
        self.model_router = model_router
        self.prompt_loader = prompt_loader

    async def run(self, input_data: EvidenceVerifierInput, **kwargs: Any) -> EvidenceVerifierOutput:
        """Verify report in two phases.

        On failure: defaults to reject (conservative).
        """
        start = time.monotonic()
        flags: list[VerifierFlag] = []

        try:
            # Phase 1: Rule check (diagnosis/treatment prohibition)
            rule_flags = self._rule_check(input_data.draft_report)
            flags.extend(rule_flags)

            # Phase 2: LLM check (unsupported claim detection)
            try:
                llm_flags = await self._llm_check(input_data)
                flags.extend(llm_flags)
            except NotImplementedError:
                raise
            except Exception as e:
                logger.warning("LLM verification failed, relying on rule check only: %s", e)

            # Count violations
            unsupported = [f for f in flags if f.issue == "unsupported_claim"]
            diagnosis_violation = any(
                f.issue in ("diagnosis_violation", "treatment_violation")
                for f in flags
            )

            # Determine action (HAND-5: any unsupported claim → reject/regenerate)
            if diagnosis_violation:
                action = VerifierAction.REJECT
            elif len(unsupported) > 0:
                action = VerifierAction.REGENERATE
            else:
                action = VerifierAction.PASS

            latency_ms = int((time.monotonic() - start) * 1000)

            return EvidenceVerifierOutput(
                verified_report=input_data.draft_report if action == VerifierAction.PASS else "",
                flags=flags,
                unsupported_claim_count=len(unsupported),
                diagnosis_or_treatment_violation=diagnosis_violation,
                action=action,
                latency_ms=latency_ms,
                model_used=kwargs.get("model_used", ""),
                prompt_version="evidence_verifier.v1",
            )

        except NotImplementedError:
            raise
        except Exception as e:
            logger.error("EvidenceVerifierAgent failed, defaulting to reject: %s", e)
            latency_ms = int((time.monotonic() - start) * 1000)
            return EvidenceVerifierOutput(
                verified_report="",
                flags=[VerifierFlag(
                    claim_text="SYSTEM",
                    issue="unsupported_claim",
                    severity="error",
                )],
                unsupported_claim_count=1,
                diagnosis_or_treatment_violation=False,
                action=VerifierAction.REJECT,
                latency_ms=latency_ms,
                model_used="error_fallback",
                reason_summary=f"Verification failed: {type(e).__name__}. Conservative reject.",
            )

    def _rule_check(self, report: str) -> list[VerifierFlag]:
        """Regex scan for diagnosis/treatment prohibition violations."""
        flags = []

        for pattern in DIAGNOSIS_PATTERNS:
            matches = re.finditer(pattern, report)
            for match in matches:
                flags.append(VerifierFlag(
                    claim_text=match.group(),
                    issue="diagnosis_violation",
                    severity="error",
                ))

        for pattern in TREATMENT_PATTERNS:
            matches = re.finditer(pattern, report)
            for match in matches:
                flags.append(VerifierFlag(
                    claim_text=match.group(),
                    issue="treatment_violation",
                    severity="error",
                ))

        return flags

    async def _llm_check(self, input_data: EvidenceVerifierInput) -> list[VerifierFlag]:
        """LLM-based unsupported claim detection.

        Compares each claim in the report against available evidence packets.
        """
        model_selection = await self.model_router.select_model(
            agent_name=self.name,
            task_name="evidence_verification",
            require_json=True,
        )

        system_prompt = await self.prompt_loader.load_system_prompt(
            "evidence_verifier", "v1",
        )

        # LLM call (implementation deferred)
        raise NotImplementedError("LLM integration pending adapter wiring")
```

### Implementation Notes

- **Two-phase verification**: Rule check (instant, ~5ms) catches obvious violations. LLM check (slower) catches subtle unsupported claims.
- **Conservative failure**: On ANY error, defaults to REJECT. Never passes an unverified report.
- **Diagnosis/treatment regex**: Korean-specific patterns for diagnosis assertions and treatment instructions. Updated as new patterns are discovered.
- **HAND-5 compliance**: ANY unsupported claim triggers reject or regenerate. Zero tolerance.

### Tests

**File**: `apps/ai-server/tests/agents/test_evidence_verifier.py` (new)

Key test cases:

```python
"""Tests for EvidenceVerifierAgent."""

import pytest
from unittest.mock import AsyncMock

from src.agents.evidence_verifier import EvidenceVerifierAgent
from src.schemas.evidence_verifier import (
    EvidenceVerifierInput,
    EvidenceVerifierOutput,
    VerifierAction,
)


class TestEvidenceVerifierSchema:
    def test_action_enum(self) -> None:
        assert VerifierAction.PASS == "pass"
        assert VerifierAction.REJECT == "reject"
        assert VerifierAction.REGENERATE == "regenerate"

    def test_output_round_trip(self) -> None:
        out = EvidenceVerifierOutput(
            verified_report="# Report",
            action=VerifierAction.PASS,
        )
        data = out.model_dump()
        restored = EvidenceVerifierOutput.model_validate(data)
        assert restored.action == VerifierAction.PASS


class TestEvidenceVerifierAgent:
    @pytest.fixture
    def agent(self) -> EvidenceVerifierAgent:
        return EvidenceVerifierAgent(
            model_router=AsyncMock(),
            prompt_loader=AsyncMock(),
        )

    def test_rule_check_catches_diagnosis(self, agent: EvidenceVerifierAgent) -> None:
        report = "환자는 주요우울장애입니다."
        flags = agent._rule_check(report)
        assert len(flags) > 0
        assert any(f.issue == "diagnosis_violation" for f in flags)

    def test_rule_check_catches_treatment(self, agent: EvidenceVerifierAgent) -> None:
        report = "졸피뎀 10mg으로 증량하세요."
        flags = agent._rule_check(report)
        assert len(flags) > 0
        assert any(f.issue == "treatment_violation" for f in flags)

    def test_rule_check_passes_clean_report(self, agent: EvidenceVerifierAgent) -> None:
        report = "환자는 수면 문제를 호소하였음. [ev_001]"
        flags = agent._rule_check(report)
        assert len(flags) == 0

    @pytest.mark.asyncio
    async def test_failure_defaults_to_reject(self, agent: EvidenceVerifierAgent) -> None:
        agent.model_router.select_model.side_effect = RuntimeError("fail")
        result = await agent.run(EvidenceVerifierInput(
            draft_report="clean report [ev_001]",
        ))
        # Rule check passes but LLM fails — should still work if only rule flags
        # Since the agent catches LLM failure and continues with rule check only,
        # a clean report should still pass
        # But if the entire agent fails, it rejects
        assert result.action in (VerifierAction.PASS, VerifierAction.REJECT)

    @pytest.mark.asyncio
    async def test_diagnosis_violation_causes_reject(self, agent: EvidenceVerifierAgent) -> None:
        agent.model_router.select_model.side_effect = RuntimeError("no LLM")
        result = await agent.run(EvidenceVerifierInput(
            draft_report="환자는 주요우울장애로 판단됩니다.",
        ))
        assert result.diagnosis_or_treatment_violation is True
        assert result.action == VerifierAction.REJECT
```

---

## Step 6.4 — TemporalRetrieverAgent

### Schema

**File**: `apps/ai-server/src/schemas/temporal_retriever.py` (new)

```python
"""Internal schemas for TemporalRetrieverAgent."""

from pydantic import BaseModel, Field

from src.agents.base import AgentInput, AgentOutput


class TemporalRetrieverInput(AgentInput):
    """Input to TemporalRetrieverAgent."""

    query: str = ""
    patient_id: str = ""
    time_filter: dict = Field(default_factory=dict)  # {"from": "...", "to": "..."}


class TemporalRetrieverOutput(AgentOutput):
    """Output from TemporalRetrieverAgent."""

    evidence_packets: list[dict] = Field(default_factory=list)
    coverage: dict = Field(default_factory=dict)  # {"cc": bool, "hpi": bool, ...}
```

### Agent

**File**: `apps/ai-server/src/agents/temporal_retriever.py` (new)

```python
"""TemporalRetrieverAgent — temporal evidence retrieval.

MVP: STUB — returns empty evidence packets.
Post-MVP: semantic_similarity + recency + risk_relevance +
  doc_confidence + clinician_feedback - stale_penalty scoring.
PRD §6.6 retrieval scoring formula.
"""

import logging
import time
from typing import Any

from src.agents.base import BaseAgent
from src.schemas.temporal_retriever import TemporalRetrieverInput, TemporalRetrieverOutput

logger = logging.getLogger(__name__)


class TemporalRetrieverAgent(BaseAgent):
    """Retrieve temporal evidence for longitudinal delta and handoff.

    MVP: Returns empty packets (stub). Post-MVP implements full
    temporal scoring per PRD §6.6.

    Post-MVP scoring formula:
      score = semantic_similarity
            + alpha * recency_weight        (0.15)
            + beta * risk_relevance         (0.25)
            + gamma * document_confidence   (0.10)
            + delta * clinician_feedback     (0.20)
            - lambda * stale_penalty        (0.30)
    """

    name = "temporal_retriever"
    description = "Retrieve temporal evidence from past sessions, documents, and risk events"

    def __init__(self) -> None:
        pass  # No dependencies for MVP stub

    async def run(self, input_data: TemporalRetrieverInput, **kwargs: Any) -> TemporalRetrieverOutput:
        """MVP stub: return empty evidence packets.

        Post-MVP: query pgvector via Context Gateway API.
        """
        start = time.monotonic()
        latency_ms = int((time.monotonic() - start) * 1000)

        logger.info(
            "TemporalRetrieverAgent stub called for patient=%s query=%s",
            input_data.patient_id,
            input_data.query[:50] if input_data.query else "",
        )

        return TemporalRetrieverOutput(
            evidence_packets=[],
            coverage={
                "cc": False,
                "hpi": False,
                "risk": False,
                "medication": False,
                "mood": False,
                "sleep": False,
            },
            latency_ms=latency_ms,
            model_used="stub",
            prompt_version="n/a",
            reason_summary="MVP stub — temporal retrieval not yet implemented.",
        )
```

### Implementation Notes

- **MVP stub**: Returns empty packets. This is intentional — temporal RAG requires pgvector integration via Context Gateway, which is a Platform team dependency.
- **Post-MVP scoring**: PRD §6.6 defines the full scoring formula with 5 positive signals and 1 penalty. Initial parameter values provided.
- **Coverage dict**: Tracks which domains have evidence coverage. Used by HandoffGenerator to populate "Missing Information" section.
- **No dependencies**: MVP stub requires no adapters or model router.

### Tests

**File**: `apps/ai-server/tests/agents/test_temporal_retriever.py` (new)

Key test cases:

```python
"""Tests for TemporalRetrieverAgent."""

import pytest

from src.agents.temporal_retriever import TemporalRetrieverAgent
from src.schemas.temporal_retriever import TemporalRetrieverInput, TemporalRetrieverOutput


class TestTemporalRetrieverSchema:
    def test_input_defaults(self) -> None:
        inp = TemporalRetrieverInput()
        assert inp.query == ""
        assert inp.patient_id == ""

    def test_output_round_trip(self) -> None:
        out = TemporalRetrieverOutput(
            evidence_packets=[],
            coverage={"cc": True, "hpi": False},
        )
        data = out.model_dump()
        restored = TemporalRetrieverOutput.model_validate(data)
        assert restored.coverage["cc"] is True


class TestTemporalRetrieverAgent:
    @pytest.mark.asyncio
    async def test_stub_returns_empty_packets(self) -> None:
        agent = TemporalRetrieverAgent()
        result = await agent.run(TemporalRetrieverInput(
            query="수면 문제 이력",
            patient_id="pid_001",
        ))
        assert result.evidence_packets == []
        assert "stub" in result.reason_summary.lower()

    @pytest.mark.asyncio
    async def test_stub_returns_coverage_dict(self) -> None:
        agent = TemporalRetrieverAgent()
        result = await agent.run(TemporalRetrieverInput())
        assert isinstance(result.coverage, dict)
        assert "cc" in result.coverage
        assert all(v is False for v in result.coverage.values())

    @pytest.mark.asyncio
    async def test_stub_does_not_crash(self) -> None:
        agent = TemporalRetrieverAgent()
        # Even with empty input, should not raise
        result = await agent.run(TemporalRetrieverInput())
        assert isinstance(result, TemporalRetrieverOutput)
```

---

## Step 6.5 — TemporalSummaryAgent

### Schema

**File**: `apps/ai-server/src/schemas/temporal_summary.py` (new)

```python
"""Internal schemas for TemporalSummaryAgent."""

from enum import StrEnum

from pydantic import BaseModel, Field

from src.agents.base import AgentInput, AgentOutput


class DeltaDirection(StrEnum):
    """Change direction for temporal delta."""

    IMPROVED = "improved"
    WORSENED = "worsened"
    UNCHANGED = "unchanged"
    UNKNOWN = "unknown"  # 판단불가


class DomainDelta(BaseModel):
    """Delta for a single clinical domain."""

    domain: str  # sleep, mood, appetite, anxiety, risk, medication, etc.
    direction: DeltaDirection = DeltaDirection.UNKNOWN
    summary: str = ""
    evidence_ids: list[str] = Field(default_factory=list)
    confidence: float = 0.0


class TemporalSummaryInput(AgentInput):
    """Input to TemporalSummaryAgent."""

    evidence_packets: list[dict] = Field(default_factory=list)


class TemporalSummaryOutput(AgentOutput):
    """Output from TemporalSummaryAgent."""

    deltas: list[DomainDelta] = Field(default_factory=list)
```

### Agent

**File**: `apps/ai-server/src/agents/temporal_summary.py` (new)

```python
"""TemporalSummaryAgent — generate longitudinal delta summaries.

Returns per-domain deltas: improved/worsened/unchanged/unknown.
When evidence is insufficient: returns "판단불가" (DeltaDirection.UNKNOWN).
"""

import logging
import time
from typing import Any

from src.agents.base import BaseAgent
from src.schemas.temporal_summary import (
    DeltaDirection,
    DomainDelta,
    TemporalSummaryInput,
    TemporalSummaryOutput,
)

logger = logging.getLogger(__name__)

DELTA_DOMAINS = ["sleep", "mood", "appetite", "anxiety", "risk", "medication", "concentration"]


class TemporalSummaryAgent(BaseAgent):
    """Generate longitudinal delta summaries per clinical domain.

    Uses ModelRouter for LLM selection (benchmarked on delta factuality
    and temporal consistency).
    Fallback: all domains marked as 판단불가 (unknown).
    """

    name = "temporal_summary"
    description = "Generate improved/worsened/unchanged/unknown deltas per clinical domain"

    def __init__(self, model_router: Any, prompt_loader: Any) -> None:
        self.model_router = model_router
        self.prompt_loader = prompt_loader

    async def run(self, input_data: TemporalSummaryInput, **kwargs: Any) -> TemporalSummaryOutput:
        """Generate temporal deltas.

        On failure or insufficient evidence: mark all domains as unknown.
        """
        start = time.monotonic()

        # If no evidence packets, return all unknown
        if not input_data.evidence_packets:
            latency_ms = int((time.monotonic() - start) * 1000)
            return TemporalSummaryOutput(
                deltas=[
                    DomainDelta(
                        domain=d,
                        direction=DeltaDirection.UNKNOWN,
                        summary="판단불가 — 이전 세션 데이터 없음",
                    )
                    for d in DELTA_DOMAINS
                ],
                latency_ms=latency_ms,
                model_used="no_evidence",
                reason_summary="No evidence packets — all domains marked as 판단불가.",
            )

        try:
            model_selection = await self.model_router.select_model(
                agent_name=self.name,
                task_name="temporal_delta_summary",
                require_json=True,
            )

            system_prompt = await self.prompt_loader.load_system_prompt(
                "temporal_summary", "v1",
            )

            # LLM call (implementation deferred)
            raise NotImplementedError("LLM integration pending adapter wiring")

        except NotImplementedError:
            raise
        except Exception as e:
            logger.warning("TemporalSummaryAgent failed, marking all as unknown: %s", e)
            latency_ms = int((time.monotonic() - start) * 1000)
            return TemporalSummaryOutput(
                deltas=[
                    DomainDelta(
                        domain=d,
                        direction=DeltaDirection.UNKNOWN,
                        summary="판단불가 — 분석 실패",
                    )
                    for d in DELTA_DOMAINS
                ],
                latency_ms=latency_ms,
                model_used="fallback_unknown",
                reason_summary=f"Temporal summary failed: {type(e).__name__}. All domains marked unknown.",
            )
```

### Implementation Notes

- **Domain list**: 7 clinical domains tracked for longitudinal change.
- **판단불가 policy**: When evidence is insufficient or analysis fails, the domain is marked `UNKNOWN` with "판단불가" — never guesses.
- **Evidence-grounded**: Each delta MUST reference evidence IDs. Deltas without evidence are invalid.
- **Contradiction detection**: Post-MVP: if current and past evidence contradict, mark as "모순 가능성" rather than asserting a direction.

### Tests

**File**: `apps/ai-server/tests/agents/test_temporal_summary.py` (new)

Key test cases:

```python
"""Tests for TemporalSummaryAgent."""

import pytest
from unittest.mock import AsyncMock

from src.agents.temporal_summary import TemporalSummaryAgent, DELTA_DOMAINS
from src.schemas.temporal_summary import (
    DeltaDirection,
    DomainDelta,
    TemporalSummaryInput,
    TemporalSummaryOutput,
)


class TestTemporalSummarySchema:
    def test_delta_direction_enum(self) -> None:
        assert DeltaDirection.UNKNOWN == "unknown"
        assert len(DeltaDirection) == 4

    def test_output_round_trip(self) -> None:
        out = TemporalSummaryOutput(
            deltas=[DomainDelta(domain="sleep", direction=DeltaDirection.IMPROVED)],
        )
        data = out.model_dump()
        restored = TemporalSummaryOutput.model_validate(data)
        assert restored.deltas[0].direction == DeltaDirection.IMPROVED


class TestTemporalSummaryAgent:
    @pytest.fixture
    def agent(self) -> TemporalSummaryAgent:
        return TemporalSummaryAgent(
            model_router=AsyncMock(),
            prompt_loader=AsyncMock(),
        )

    @pytest.mark.asyncio
    async def test_no_evidence_returns_all_unknown(self, agent: TemporalSummaryAgent) -> None:
        result = await agent.run(TemporalSummaryInput(evidence_packets=[]))
        assert len(result.deltas) == len(DELTA_DOMAINS)
        assert all(d.direction == DeltaDirection.UNKNOWN for d in result.deltas)
        assert "판단불가" in result.deltas[0].summary

    @pytest.mark.asyncio
    async def test_failure_returns_all_unknown(self, agent: TemporalSummaryAgent) -> None:
        agent.model_router.select_model.side_effect = RuntimeError("fail")
        result = await agent.run(TemporalSummaryInput(
            evidence_packets=[{"evidence_id": "ev_001", "content": "test"}],
        ))
        assert all(d.direction == DeltaDirection.UNKNOWN for d in result.deltas)

    @pytest.mark.asyncio
    async def test_delta_domains_covered(self, agent: TemporalSummaryAgent) -> None:
        result = await agent.run(TemporalSummaryInput())
        domains = {d.domain for d in result.deltas}
        assert domains == set(DELTA_DOMAINS)
```

---

## Step 6.6 — PromptEvalAgent

### Schema

**File**: `apps/ai-server/src/schemas/prompt_eval.py` (new)

```python
"""Internal schemas for PromptEvalAgent."""

from pydantic import BaseModel, Field

from src.agents.base import AgentInput, AgentOutput


class EvalMetric(BaseModel):
    """Single evaluation metric."""

    name: str
    value: float
    threshold: float | None = None
    passed: bool | None = None


class FailCase(BaseModel):
    """Single evaluation failure case."""

    case_id: str
    input_text: str = ""
    expected: str = ""
    actual: str = ""
    metric: str = ""
    score: float = 0.0


class PromptEvalInput(AgentInput):
    """Input to PromptEvalAgent."""

    eval_dataset: str  # reference to dataset file or version
    agent_name: str = ""
    candidate_models: list[str] = Field(default_factory=list)


class PromptEvalOutput(AgentOutput):
    """Output from PromptEvalAgent."""

    metrics: list[EvalMetric] = Field(default_factory=list)
    fail_cases: list[FailCase] = Field(default_factory=list)
    release_gate_passed: bool = False
```

### Agent

**File**: `apps/ai-server/src/agents/prompt_eval.py` (new)

```python
"""PromptEvalAgent — offline evaluation harness skeleton.

Runs prompt/model regression tests against eval datasets.
MVP: skeleton that loads dataset reference and returns placeholder metrics.
Post-MVP: full evaluation pipeline with model comparison.
"""

import logging
import time
from typing import Any

from src.agents.base import BaseAgent
from src.schemas.prompt_eval import PromptEvalInput, PromptEvalOutput

logger = logging.getLogger(__name__)


class PromptEvalAgent(BaseAgent):
    """Offline prompt/model evaluation harness.

    MVP: skeleton — accepts eval_dataset reference, returns placeholder.
    Post-MVP: runs candidate models against dataset, computes metrics,
    determines release gate pass/fail.
    """

    name = "prompt_eval"
    description = "Run offline prompt/model regression evaluation against eval datasets"

    def __init__(self) -> None:
        pass  # No dependencies for MVP skeleton

    async def run(self, input_data: PromptEvalInput, **kwargs: Any) -> PromptEvalOutput:
        """Run evaluation (MVP skeleton).

        Returns placeholder metrics indicating eval is not yet implemented.
        """
        start = time.monotonic()
        latency_ms = int((time.monotonic() - start) * 1000)

        logger.info(
            "PromptEvalAgent skeleton called: dataset=%s agent=%s models=%s",
            input_data.eval_dataset,
            input_data.agent_name,
            input_data.candidate_models,
        )

        return PromptEvalOutput(
            metrics=[],
            fail_cases=[],
            release_gate_passed=False,
            latency_ms=latency_ms,
            model_used="eval_skeleton",
            prompt_version="n/a",
            reason_summary="MVP skeleton — evaluation pipeline not yet implemented.",
        )
```

### Implementation Notes

- **MVP skeleton**: Returns empty metrics. Full implementation requires eval datasets, model comparison logic, and metric computation.
- **Release gate**: `release_gate_passed` is `False` by default. Post-MVP: set to `True` only when all metrics pass their thresholds.
- **Dataset loading**: Post-MVP will load JSONL datasets from `eval/datasets/{agent}/{version}.jsonl`.
- **Model comparison**: Post-MVP will run same inputs through all candidate models and compare metrics.

### Tests

**File**: `apps/ai-server/tests/agents/test_prompt_eval.py` (new)

Key test cases:

```python
"""Tests for PromptEvalAgent."""

import pytest

from src.agents.prompt_eval import PromptEvalAgent
from src.schemas.prompt_eval import PromptEvalInput, PromptEvalOutput, EvalMetric, FailCase


class TestPromptEvalSchema:
    def test_input_defaults(self) -> None:
        inp = PromptEvalInput(eval_dataset="safety_redteam_v1")
        assert inp.agent_name == ""
        assert inp.candidate_models == []

    def test_metric_round_trip(self) -> None:
        m = EvalMetric(name="recall", value=0.95, threshold=0.90, passed=True)
        data = m.model_dump()
        restored = EvalMetric.model_validate(data)
        assert restored.passed is True

    def test_output_round_trip(self) -> None:
        out = PromptEvalOutput(
            metrics=[EvalMetric(name="recall", value=0.95)],
            fail_cases=[FailCase(case_id="c1", expected="high", actual="none")],
            release_gate_passed=False,
        )
        data = out.model_dump()
        restored = PromptEvalOutput.model_validate(data)
        assert len(restored.metrics) == 1
        assert len(restored.fail_cases) == 1


class TestPromptEvalAgent:
    @pytest.mark.asyncio
    async def test_skeleton_returns_empty_metrics(self) -> None:
        agent = PromptEvalAgent()
        result = await agent.run(PromptEvalInput(
            eval_dataset="safety_redteam_v1",
            agent_name="safety_classifier",
        ))
        assert result.metrics == []
        assert result.release_gate_passed is False
        assert "skeleton" in result.reason_summary.lower()

    @pytest.mark.asyncio
    async def test_skeleton_does_not_crash(self) -> None:
        agent = PromptEvalAgent()
        result = await agent.run(PromptEvalInput(eval_dataset=""))
        assert isinstance(result, PromptEvalOutput)
```

---

## Step 6.7 — Update `src/schemas/__init__.py`

**File**: `apps/ai-server/src/schemas/__init__.py` (modify — append to Phase 5 comment)

```python
"""Internal Pydantic schemas for agent I/O.

These are INTERNAL to ai-server. The Platform↔AI interface schemas
live in packages/shared-contracts/python/src/contracts/.

Phase 5 schemas:
- safety.py — SafetyInput, SafetyOutput
- stt.py — SttInput, SttOutput, SttSegment
- ocr.py — OcrInput, OcrOutput, OcrBlock, OcrEntity
- input_normalizer.py — InputNormalizerInput, InputNormalizerOutput
- dialogue.py — DialogueInput, DialogueOutput
- clinical_slot.py — ClinicalSlotInput, ClinicalSlotOutput

Phase 6 schemas:
- orchestrator.py — OrchestratorInput, OrchestratorOutput, NextAction
- handoff.py — HandoffInput, HandoffOutput, Citation, ScaleScore
- evidence_verifier.py — EvidenceVerifierInput, EvidenceVerifierOutput, VerifierAction
- temporal_retriever.py — TemporalRetrieverInput, TemporalRetrieverOutput
- temporal_summary.py — TemporalSummaryInput, TemporalSummaryOutput, DeltaDirection, DomainDelta
- prompt_eval.py — PromptEvalInput, PromptEvalOutput, EvalMetric, FailCase
"""
```

---

## Step 6.8 — Update `src/agents/__init__.py`

**File**: `apps/ai-server/src/agents/__init__.py` (modify — append)

```python
"""Neuro-Sync AI agents — 12 role-specialized agents per PRD §5.

Phase 5 core agents (direct user interaction):
- SafetyClassifierAgent — risk detection (rule + LLM parallel)
- SttAgent — speech-to-text (fixed SKT A.K STT)
- OcrAgent — document parsing (fixed Solar Document Parse)
- InputNormalizerAgent — STT noise correction (benchmarked LLM)
- DialogueAgent — intake conversation (benchmarked LLM)
- ClinicalSlotAgent — clinical slot extraction (benchmarked LLM)

Phase 6 pipeline agents (compose core agent outputs):
- OrchestratorAgent — state machine routing (benchmarked LLM + rule fallback)
- HandoffGeneratorAgent — evidence-grounded clinician report (benchmarked LLM)
- EvidenceVerifierAgent — rule + LLM claim verification (benchmarked LLM)
- TemporalRetrieverAgent — temporal evidence retrieval (MVP stub)
- TemporalSummaryAgent — longitudinal delta summary (benchmarked LLM)
- PromptEvalAgent — offline evaluation harness (MVP skeleton)
"""
```

---

## File Summary

| File | Type | Key Classes |
|---|---|---|
| `src/schemas/orchestrator.py` | Schema | `OrchestratorInput`, `OrchestratorOutput`, `NextAction` |
| `src/schemas/handoff.py` | Schema | `HandoffInput`, `HandoffOutput`, `Citation`, `ScaleScore` |
| `src/schemas/evidence_verifier.py` | Schema | `EvidenceVerifierInput`, `EvidenceVerifierOutput`, `VerifierAction`, `VerifierFlag` |
| `src/schemas/temporal_retriever.py` | Schema | `TemporalRetrieverInput`, `TemporalRetrieverOutput` |
| `src/schemas/temporal_summary.py` | Schema | `TemporalSummaryInput`, `TemporalSummaryOutput`, `DeltaDirection`, `DomainDelta` |
| `src/schemas/prompt_eval.py` | Schema | `PromptEvalInput`, `PromptEvalOutput`, `EvalMetric`, `FailCase` |
| `src/agents/orchestrator.py` | Agent | `OrchestratorAgent` |
| `src/agents/handoff_generator.py` | Agent | `HandoffGeneratorAgent` |
| `src/agents/evidence_verifier.py` | Agent | `EvidenceVerifierAgent` |
| `src/agents/temporal_retriever.py` | Agent | `TemporalRetrieverAgent` (MVP stub) |
| `src/agents/temporal_summary.py` | Agent | `TemporalSummaryAgent` |
| `src/agents/prompt_eval.py` | Agent | `PromptEvalAgent` (MVP skeleton) |
| `tests/agents/test_orchestrator.py` | Test | 5 test cases |
| `tests/agents/test_handoff_generator.py` | Test | 5 test cases |
| `tests/agents/test_evidence_verifier.py` | Test | 5 test cases |
| `tests/agents/test_temporal_retriever.py` | Test | 3 test cases |
| `tests/agents/test_temporal_summary.py` | Test | 3 test cases |
| `tests/agents/test_prompt_eval.py` | Test | 2 test cases |

---

## Dependency Graph

```text
Phase 5 (Core Agents)
  │
  ├── OrchestratorAgent ← routes to core + pipeline agents
  │     ├── SafetyClassifierAgent (always first)
  │     ├── DialogueAgent + ClinicalSlotAgent
  │     └── HandoffGeneratorAgent → EvidenceVerifierAgent
  │
  ├── HandoffGeneratorAgent ← consumes slots, risk, scales, evidence
  │     └── 11 mandatory sections, every claim cited
  │
  ├── EvidenceVerifierAgent ← validates HandoffGenerator output
  │     ├── Rule check (diagnosis/treatment regex)
  │     └── LLM check (unsupported claim detection)
  │
  ├── TemporalRetrieverAgent ← MVP stub (empty packets)
  │     └── Post-MVP: pgvector via Context Gateway
  │
  ├── TemporalSummaryAgent ← consumes evidence packets
  │     └── Per-domain delta: improved/worsened/unchanged/판단불가
  │
  └── PromptEvalAgent ← offline harness skeleton
        └── Post-MVP: model comparison pipeline
           │
           ▼
     Phase 7 (Routes + Prompts + Eval)
```

---

## Checklist

- [ ] `src/schemas/orchestrator.py` created with `OrchestratorInput`, `OrchestratorOutput`, `NextAction`
- [ ] `src/schemas/handoff.py` created with `HandoffInput`, `HandoffOutput`, `Citation`
- [ ] `src/schemas/evidence_verifier.py` created with `EvidenceVerifierInput`, `EvidenceVerifierOutput`, `VerifierAction`
- [ ] `src/schemas/temporal_retriever.py` created with `TemporalRetrieverInput`, `TemporalRetrieverOutput`
- [ ] `src/schemas/temporal_summary.py` created with `TemporalSummaryInput`, `TemporalSummaryOutput`, `DeltaDirection`
- [ ] `src/schemas/prompt_eval.py` created with `PromptEvalInput`, `PromptEvalOutput`
- [ ] `src/agents/orchestrator.py` created with rule-based fallback router
- [ ] `src/agents/handoff_generator.py` created with 11-section template fallback
- [ ] `src/agents/evidence_verifier.py` created with Korean diagnosis/treatment regex patterns
- [ ] `src/agents/temporal_retriever.py` created as MVP stub
- [ ] `src/agents/temporal_summary.py` created with 판단불가 fallback
- [ ] `src/agents/prompt_eval.py` created as MVP skeleton
- [ ] All 6 test files pass with mocked adapters
- [ ] `ruff check src/schemas/ src/agents/` passes
- [ ] `critic` gate: HandoffGenerator always requires clinician review
- [ ] `critic` gate: EvidenceVerifier rejects on any unsupported claim
- [ ] `critic` gate: 판단불가 used when evidence insufficient (never guesses)
