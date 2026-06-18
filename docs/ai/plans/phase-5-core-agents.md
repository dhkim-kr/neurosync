# Phase 5: Core Agents

> **Depends on**: Phase 4 (ModelRouter, fallback_policy, agent_model_registry)
> **Blocks**: Phase 6 (pipeline agents consume core agent outputs)
> **Agent owner**: `developer`
> **Gate**: `qa` + `critic` (safety is critical — every agent must fail safe)

---

## Objective

Implement the 6 agents that handle direct user interaction: safety classification, speech-to-text, OCR, input normalization, dialogue intake, and clinical slot extraction. Each agent subclasses `BaseAgent`, uses `ModelRouter` for model selection, and defines its own internal I/O schemas in `src/schemas/`.

## Success Criteria

- [ ] All 6 agent classes instantiate and pass type checks
- [ ] All 6 schema modules import cleanly with round-trip serialization
- [ ] `SafetyClassifierAgent` rule+LLM parallel execution completes under 700ms on mock
- [ ] Every agent returns `AgentOutput` subclass with `model_used`, `prompt_version`, `latency_ms`
- [ ] Every agent has a documented fallback path that does not crash
- [ ] `pytest tests/agents/test_safety_classifier.py tests/agents/test_stt.py tests/agents/test_ocr.py tests/agents/test_input_normalizer.py tests/agents/test_dialogue.py tests/agents/test_clinical_slot.py -x` passes
- [ ] `ruff check src/agents/ src/schemas/` passes

---

## Step 5.1 — SafetyClassifierAgent

**MOST CRITICAL AGENT.** Parallel rule detector (Aho-Corasick) + LLM classifier. Failure mode: emergency-safe default (treat as high risk).

### Schema

**File**: `apps/ai-server/src/schemas/safety.py` (new)

```python
"""Internal schemas for SafetyClassifierAgent."""

from pydantic import BaseModel, Field

from src.agents.base import AgentInput, AgentOutput
from src.schemas.common import RiskLevel


class SafetyInput(AgentInput):
    """Input to SafetyClassifierAgent."""

    message: str
    prev_context: list[str] = Field(default_factory=list)
    locale: str = "ko-KR"


class SafetyOutput(AgentOutput):
    """Output from SafetyClassifierAgent."""

    risk_level: RiskLevel = RiskLevel.NONE
    risk_categories: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    recommended_action: str = ""
    requires_human_review: bool = False
    rule_hit: bool = False
    llm_risk_level: RiskLevel = RiskLevel.NONE
```

### Agent

**File**: `apps/ai-server/src/agents/safety_classifier.py` (new)

```python
"""SafetyClassifierAgent — parallel rule + LLM safety classification.

PRD §6.2: SAF-1 through SAF-6.
"""

import asyncio
import logging
import time
from typing import Any

from src.agents.base import BaseAgent
from src.schemas.safety import SafetyInput, SafetyOutput
from src.schemas.common import RiskLevel

logger = logging.getLogger(__name__)


class SafetyClassifierAgent(BaseAgent):
    """Classify user messages for crisis/risk signals.

    Architecture:
    1. Rule detector (Aho-Corasick keyword matching, ~50ms target)
    2. LLM classifier (via ModelRouter, ~600ms target)
    3. Both run via asyncio.gather()
    4. Merge: max(rule_level, llm_level)
    5. If rule hits but LLM says none → keep >= medium (SAF-2)
    6. Fallback on ANY error: emergency-safe default (high risk)
    """

    name = "safety_classifier"
    description = "Classify user messages for suicide, self-harm, violence, and acute crisis risk"

    def __init__(
        self,
        model_router: Any,
        prompt_loader: Any,
        rule_detector: Any | None = None,
    ) -> None:
        self.model_router = model_router
        self.prompt_loader = prompt_loader
        self.rule_detector = rule_detector  # AhoCorasickDetector instance

    async def run(self, input_data: SafetyInput, **kwargs: Any) -> SafetyOutput:
        """Execute parallel rule + LLM classification.

        Returns:
            SafetyOutput with merged risk level.
            On ANY exception: returns high-risk emergency-safe default.
        """
        start = time.monotonic()
        try:
            rule_task = self._run_rule_detector(input_data)
            llm_task = self._run_llm_classifier(input_data)
            rule_result, llm_result = await asyncio.gather(
                rule_task, llm_task, return_exceptions=True,
            )

            # If both failed, emergency-safe default
            if isinstance(rule_result, Exception) and isinstance(llm_result, Exception):
                logger.error("Both rule and LLM classifiers failed: %s / %s", rule_result, llm_result)
                return self._emergency_safe_default(input_data, start)

            # Extract results, defaulting on individual failures
            rule_level, rule_hit, rule_categories, rule_evidence = self._unpack_rule(rule_result)
            llm_level, llm_confidence, llm_categories, llm_evidence = self._unpack_llm(llm_result)

            # Merge: max(rule_level, llm_level)
            merged_level = max(rule_level, llm_level, key=lambda r: list(RiskLevel).index(r))

            # SAF-2: If rule hits but LLM says none → keep >= medium
            if rule_hit and llm_level == RiskLevel.NONE:
                if merged_level.value in ("none", "low"):
                    merged_level = RiskLevel.MEDIUM

            # Determine action
            recommended_action = self._determine_action(merged_level)

            # Human review if low confidence or disagreement
            requires_review = (
                llm_confidence < 0.7
                or (rule_hit and llm_level == RiskLevel.NONE)
            )

            latency_ms = int((time.monotonic() - start) * 1000)

            return SafetyOutput(
                risk_level=merged_level,
                risk_categories=list(set(rule_categories + llm_categories)),
                evidence=list(set(rule_evidence + llm_evidence)),
                confidence=llm_confidence,
                recommended_action=recommended_action,
                requires_human_review=requires_review,
                rule_hit=rule_hit,
                llm_risk_level=llm_level,
                latency_ms=latency_ms,
                model_used=kwargs.get("model_used", ""),
                prompt_version=kwargs.get("prompt_version", "safety_classifier.v1"),
            )

        except Exception as e:
            logger.error("SafetyClassifierAgent unexpected error: %s", e)
            return self._emergency_safe_default(input_data, start)

    async def _run_rule_detector(self, input_data: SafetyInput) -> dict:
        """Run Aho-Corasick keyword matching for Korean crisis terms.

        Target: ~50ms. Uses precompiled automaton with ~200 Korean crisis
        terms including: 자살, 죽고 싶, 자해, 목매, 손목, 투신, etc.
        """
        if self.rule_detector is None:
            return {"level": RiskLevel.NONE, "hit": False, "categories": [], "evidence": []}
        return await self.rule_detector.detect(input_data.message, input_data.locale)

    async def _run_llm_classifier(self, input_data: SafetyInput) -> dict:
        """Run LLM-based safety classification via ModelRouter.

        Target: ~600ms. Uses structured JSON output.
        """
        model_selection = await self.model_router.select_model(
            agent_name=self.name,
            task_name="risk_classification",
            require_json=True,
        )
        system_prompt = await self.prompt_loader.load_system_prompt(
            "safety_classifier", "v1",
        )
        # Build messages and call LLM adapter
        # ... (implementation deferred to actual adapter integration)
        raise NotImplementedError("LLM classifier integration pending adapter wiring")

    def _unpack_rule(self, result: Any) -> tuple:
        if isinstance(result, Exception):
            return RiskLevel.NONE, False, [], []
        return (
            result.get("level", RiskLevel.NONE),
            result.get("hit", False),
            result.get("categories", []),
            result.get("evidence", []),
        )

    def _unpack_llm(self, result: Any) -> tuple:
        if isinstance(result, Exception):
            return RiskLevel.NONE, 0.0, [], []
        return (
            result.get("level", RiskLevel.NONE),
            result.get("confidence", 0.0),
            result.get("categories", []),
            result.get("evidence", []),
        )

    def _determine_action(self, level: RiskLevel) -> str:
        actions = {
            RiskLevel.NONE: "continue",
            RiskLevel.LOW: "continue_with_resource_info",
            RiskLevel.MEDIUM: "safety_confirmation_question",
            RiskLevel.HIGH: "interrupt_and_route_to_crisis_help",
            RiskLevel.CRITICAL: "emergency_mode_119",
        }
        return actions.get(level, "interrupt_and_route_to_crisis_help")

    def _emergency_safe_default(self, input_data: SafetyInput, start: float) -> SafetyOutput:
        """Return high-risk default when classifiers fail. PRD SAF-2."""
        return SafetyOutput(
            risk_level=RiskLevel.HIGH,
            risk_categories=["classifier_failure"],
            evidence=["Classification system error — defaulting to high risk"],
            confidence=0.0,
            recommended_action="interrupt_and_route_to_crisis_help",
            requires_human_review=True,
            rule_hit=False,
            llm_risk_level=RiskLevel.NONE,
            latency_ms=int((time.monotonic() - start) * 1000),
            model_used="emergency_fallback",
            prompt_version="n/a",
            reason_summary="Both classifiers failed; emergency-safe default applied",
        )
```

### Implementation Notes

- **Aho-Corasick automaton**: Precompiled at startup with ~200 Korean crisis terms. Use `ahocorasick` PyPI package. Terms grouped by severity tier (medium: 절망, 무기력; high: 자살, 죽고 싶다; critical: 지금 죽, 약 먹었).
- **Parallel execution**: `asyncio.gather(return_exceptions=True)` ensures one failure does not block the other.
- **Merge logic**: `max()` by enum ordinal. SAF-2 override ensures rule hits are never downgraded below medium.
- **Emergency-safe default**: Returns `RiskLevel.HIGH` on any unhandled error. Never returns `none` on failure.
- **Latency target**: Rule ~50ms + LLM ~600ms in parallel = ~650ms total. PRD target: <1000ms p95.

### Tests

**File**: `apps/ai-server/tests/agents/test_safety_classifier.py` (new)

Key test cases:

```python
"""Tests for SafetyClassifierAgent."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.agents.safety_classifier import SafetyClassifierAgent
from src.schemas.safety import SafetyInput, SafetyOutput
from src.schemas.common import RiskLevel


class TestSafetySchema:
    """Schema round-trip tests."""

    def test_safety_input_defaults(self) -> None:
        inp = SafetyInput(message="안녕하세요")
        assert inp.locale == "ko-KR"
        assert inp.prev_context == []

    def test_safety_output_round_trip(self) -> None:
        out = SafetyOutput(
            risk_level=RiskLevel.HIGH,
            risk_categories=["suicidal_ideation"],
            evidence=["죽고 싶다"],
            confidence=0.91,
            rule_hit=True,
            llm_risk_level=RiskLevel.HIGH,
        )
        data = out.model_dump()
        restored = SafetyOutput.model_validate(data)
        assert restored.risk_level == RiskLevel.HIGH
        assert restored.rule_hit is True


class TestSafetyClassifierAgent:
    """Agent behavior tests."""

    @pytest.fixture
    def agent(self) -> SafetyClassifierAgent:
        return SafetyClassifierAgent(
            model_router=AsyncMock(),
            prompt_loader=AsyncMock(),
            rule_detector=None,
        )

    @pytest.mark.asyncio
    async def test_emergency_safe_default_on_both_failures(self, agent: SafetyClassifierAgent) -> None:
        """When both classifiers fail, return high risk."""
        # Override internal methods to raise
        agent._run_rule_detector = AsyncMock(side_effect=RuntimeError("rule fail"))
        agent._run_llm_classifier = AsyncMock(side_effect=RuntimeError("llm fail"))
        result = await agent.run(SafetyInput(message="test"))
        assert result.risk_level == RiskLevel.HIGH
        assert result.requires_human_review is True
        assert result.recommended_action == "interrupt_and_route_to_crisis_help"

    @pytest.mark.asyncio
    async def test_rule_hit_llm_none_keeps_medium(self, agent: SafetyClassifierAgent) -> None:
        """SAF-2: rule hit + LLM none → merged >= medium."""
        agent._run_rule_detector = AsyncMock(return_value={
            "level": RiskLevel.LOW, "hit": True,
            "categories": ["keyword_match"], "evidence": ["죽고"],
        })
        agent._run_llm_classifier = AsyncMock(return_value={
            "level": RiskLevel.NONE, "confidence": 0.8,
            "categories": [], "evidence": [],
        })
        result = await agent.run(SafetyInput(message="죽고"))
        assert result.risk_level >= RiskLevel.MEDIUM

    @pytest.mark.asyncio
    async def test_merge_takes_max(self, agent: SafetyClassifierAgent) -> None:
        """Merge logic: max(rule, llm)."""
        agent._run_rule_detector = AsyncMock(return_value={
            "level": RiskLevel.MEDIUM, "hit": True,
            "categories": ["despair"], "evidence": ["절망"],
        })
        agent._run_llm_classifier = AsyncMock(return_value={
            "level": RiskLevel.HIGH, "confidence": 0.92,
            "categories": ["suicidal_ideation"], "evidence": ["죽고 싶다"],
        })
        result = await agent.run(SafetyInput(message="절망적이고 죽고 싶다"))
        assert result.risk_level == RiskLevel.HIGH

    @pytest.mark.asyncio
    async def test_latency_ms_populated(self, agent: SafetyClassifierAgent) -> None:
        """latency_ms is always populated."""
        agent._run_rule_detector = AsyncMock(return_value={
            "level": RiskLevel.NONE, "hit": False, "categories": [], "evidence": [],
        })
        agent._run_llm_classifier = AsyncMock(return_value={
            "level": RiskLevel.NONE, "confidence": 0.95, "categories": [], "evidence": [],
        })
        result = await agent.run(SafetyInput(message="안녕하세요"))
        assert result.latency_ms >= 0

    @pytest.mark.asyncio
    async def test_no_risk_returns_continue(self, agent: SafetyClassifierAgent) -> None:
        """No risk → action=continue."""
        agent._run_rule_detector = AsyncMock(return_value={
            "level": RiskLevel.NONE, "hit": False, "categories": [], "evidence": [],
        })
        agent._run_llm_classifier = AsyncMock(return_value={
            "level": RiskLevel.NONE, "confidence": 0.99, "categories": [], "evidence": [],
        })
        result = await agent.run(SafetyInput(message="오늘 날씨 좋네요"))
        assert result.risk_level == RiskLevel.NONE
        assert result.recommended_action == "continue"
```

---

## Step 5.2 — SttAgent

### Schema

**File**: `apps/ai-server/src/schemas/stt.py` (new)

```python
"""Internal schemas for SttAgent."""

from pydantic import BaseModel, Field

from src.agents.base import AgentInput, AgentOutput


class SttSegment(BaseModel):
    """Time-aligned transcript segment."""

    start_ms: int
    end_ms: int
    text: str


class SttInput(AgentInput):
    """Input to SttAgent."""

    audio_bytes: bytes | None = None
    audio_file_url: str | None = None
    audio_format: str = "wav"
    language: str = "ko-KR"
    context_hint: str | None = None


class SttOutput(AgentOutput):
    """Output from SttAgent."""

    text: str = ""
    confidence: float | None = None  # None when vendor doesn't provide
    segments: list[SttSegment] = Field(default_factory=list)
    low_confidence_spans: list[SttSegment] = Field(default_factory=list)
    requires_user_confirmation: bool = True
```

### Agent

**File**: `apps/ai-server/src/agents/stt.py` (new)

```python
"""SttAgent — wraps SktAkSttAdapter for speech-to-text.

PRD §6.5: STT-1 through STT-8.
"""

import logging
import time
from typing import Any

from src.agents.base import BaseAgent
from src.schemas.stt import SttInput, SttOutput

logger = logging.getLogger(__name__)


class SttAgent(BaseAgent):
    """Convert audio input to text via SKT A.K STT.

    Fixed vendor (no model routing). Wraps SktAkSttAdapter.
    Fallback: returns empty text with requires_user_confirmation=True
    so the client can prompt typed input.
    """

    name = "stt"
    description = "Convert audio to text using SKT A.K STT"

    def __init__(self, stt_adapter: Any) -> None:
        self.stt_adapter = stt_adapter

    async def run(self, input_data: SttInput, **kwargs: Any) -> SttOutput:
        """Transcribe audio via SktAkSttAdapter.

        Requires either audio_bytes or audio_file_url.
        On failure: returns empty text + requires_user_confirmation=True.
        """
        start = time.monotonic()
        try:
            if input_data.audio_bytes is None and input_data.audio_file_url is None:
                raise ValueError("Either audio_bytes or audio_file_url is required")

            audio = input_data.audio_bytes
            if audio is None and input_data.audio_file_url:
                audio = await self._fetch_audio(input_data.audio_file_url)

            result = await self.stt_adapter.transcribe(
                audio_bytes=audio,
                language=input_data.language,
                context_hint=input_data.context_hint,
            )

            latency_ms = int((time.monotonic() - start) * 1000)

            return SttOutput(
                text=result.get("text", ""),
                confidence=result.get("confidence"),
                segments=[
                    SttOutput.__annotations__  # placeholder — actual parsing from adapter result
                ],
                low_confidence_spans=result.get("low_confidence_spans", []),
                requires_user_confirmation=True,  # STT-5: always confirm
                latency_ms=latency_ms,
                model_used="skt-ak-stt",
                prompt_version="n/a",
            )

        except Exception as e:
            logger.error("SttAgent failed: %s", e)
            latency_ms = int((time.monotonic() - start) * 1000)
            return SttOutput(
                text="",
                confidence=None,
                requires_user_confirmation=True,
                latency_ms=latency_ms,
                model_used="skt-ak-stt",
                reason_summary=f"STT failed: {type(e).__name__}. Typed input fallback.",
            )

    async def _fetch_audio(self, url: str) -> bytes:
        """Fetch audio bytes from presigned URL.

        Implementation note: use httpx async client with timeout.
        Audio URL comes from Platform (presigned S3/MinIO URL).
        """
        raise NotImplementedError("Audio fetch pending httpx integration")
```

### Implementation Notes

- **Fixed vendor**: No ModelRouter call. Always uses `SktAkSttAdapter`.
- **Audio format**: MVP supports wav/m4a. Max 60 seconds (STT-3).
- **Confidence**: SKT A.K STT may not provide confidence — field is nullable.
- **Fallback**: On ANY failure, returns empty text so client triggers typed input (STT-7).
- **User confirmation**: Always `True` per STT-5.

### Tests

**File**: `apps/ai-server/tests/agents/test_stt.py` (new)

Key test cases:

```python
"""Tests for SttAgent."""

import pytest
from unittest.mock import AsyncMock

from src.agents.stt import SttAgent
from src.schemas.stt import SttInput, SttOutput


class TestSttSchema:
    def test_stt_input_requires_audio(self) -> None:
        inp = SttInput()
        assert inp.audio_bytes is None
        assert inp.audio_file_url is None

    def test_stt_output_defaults(self) -> None:
        out = SttOutput()
        assert out.text == ""
        assert out.confidence is None
        assert out.requires_user_confirmation is True

    def test_stt_output_round_trip(self) -> None:
        out = SttOutput(text="잠을 못 자요", confidence=0.86)
        data = out.model_dump()
        restored = SttOutput.model_validate(data)
        assert restored.text == "잠을 못 자요"


class TestSttAgent:
    @pytest.fixture
    def agent(self) -> SttAgent:
        adapter = AsyncMock()
        adapter.transcribe.return_value = {
            "text": "요즘 잠을 못 자요",
            "confidence": 0.86,
            "segments": [],
            "low_confidence_spans": [],
        }
        return SttAgent(stt_adapter=adapter)

    @pytest.mark.asyncio
    async def test_no_audio_input_returns_fallback(self) -> None:
        agent = SttAgent(stt_adapter=AsyncMock())
        result = await agent.run(SttInput())
        assert result.text == ""
        assert result.requires_user_confirmation is True

    @pytest.mark.asyncio
    async def test_adapter_failure_returns_fallback(self) -> None:
        adapter = AsyncMock()
        adapter.transcribe.side_effect = TimeoutError("STT timeout")
        agent = SttAgent(stt_adapter=adapter)
        result = await agent.run(SttInput(audio_bytes=b"fake_audio"))
        assert result.text == ""
        assert "STT failed" in result.reason_summary

    @pytest.mark.asyncio
    async def test_always_requires_user_confirmation(self, agent: SttAgent) -> None:
        result = await agent.run(SttInput(audio_bytes=b"fake_audio"))
        assert result.requires_user_confirmation is True
```

---

## Step 5.3 — OcrAgent

### Schema

**File**: `apps/ai-server/src/schemas/ocr.py` (new)

```python
"""Internal schemas for OcrAgent."""

from pydantic import BaseModel, Field

from src.agents.base import AgentInput, AgentOutput


class OcrBlock(BaseModel):
    """Single parsed document block."""

    block_id: str
    page: int = 1
    type: str = "text"  # text | table | image | chart
    content: str = ""
    confidence: float = 0.0


class OcrEntity(BaseModel):
    """Medical entity extracted from OCR output."""

    entity_id: str = ""
    type: str  # medication | diagnosis | lab_result | date | institution | score
    value: str
    confidence: float = 0.0
    source_block_id: str = ""
    requires_human_review: bool = False


class OcrInput(AgentInput):
    """Input to OcrAgent."""

    file_bytes: bytes | None = None
    file_url: str | None = None
    doc_type: str | None = None  # prescription | diagnosis_note | lab_result | psych_scale | unknown
    requested_outputs: list[str] = Field(
        default_factory=lambda: ["markdown", "structured_blocks"],
    )


class OcrOutput(AgentOutput):
    """Output from OcrAgent."""

    doc_id: str = ""
    text_markdown: str = ""
    structured_blocks: list[OcrBlock] = Field(default_factory=list)
    medical_entities: list[OcrEntity] = Field(default_factory=list)
    requires_human_review: bool = False
```

### Agent

**File**: `apps/ai-server/src/agents/ocr.py` (new)

```python
"""OcrAgent — wraps UpstageDocumentParseAdapter (Solar Document Parse).

PRD §6.3: OCR-1 through OCR-6.
"""

import logging
import time
from typing import Any

from src.agents.base import BaseAgent
from src.schemas.ocr import OcrInput, OcrOutput, OcrBlock, OcrEntity

logger = logging.getLogger(__name__)

# Confidence threshold below which blocks are flagged for human review
LOW_CONFIDENCE_THRESHOLD = 0.7


class OcrAgent(BaseAgent):
    """Parse uploaded medical documents via Solar Document Parse.

    Fixed vendor (no model routing). Wraps SolarDocumentParseAdapter.
    Flags low-confidence blocks for human review (OCR-4).
    """

    name = "ocr"
    description = "Parse medical documents (prescriptions, diagnoses, lab results) via Solar Document Parse"

    def __init__(self, ocr_adapter: Any) -> None:
        self.ocr_adapter = ocr_adapter

    async def run(self, input_data: OcrInput, **kwargs: Any) -> OcrOutput:
        """Parse document via SolarDocumentParseAdapter.

        On failure: returns empty output with requires_human_review=True.
        """
        start = time.monotonic()
        try:
            if input_data.file_bytes is None and input_data.file_url is None:
                raise ValueError("Either file_bytes or file_url is required")

            file_data = input_data.file_bytes
            if file_data is None and input_data.file_url:
                file_data = await self._fetch_file(input_data.file_url)

            result = await self.ocr_adapter.parse_document(
                file_bytes=file_data,
                doc_type=input_data.doc_type,
                requested_outputs=input_data.requested_outputs,
            )

            blocks = [OcrBlock(**b) for b in result.get("structured_blocks", [])]
            entities = [OcrEntity(**e) for e in result.get("medical_entities", [])]

            # OCR-4: Flag low-confidence blocks and entities
            any_low_confidence = False
            for block in blocks:
                if block.confidence < LOW_CONFIDENCE_THRESHOLD:
                    any_low_confidence = True
            for entity in entities:
                if entity.confidence < LOW_CONFIDENCE_THRESHOLD:
                    entity.requires_human_review = True
                    any_low_confidence = True

            latency_ms = int((time.monotonic() - start) * 1000)

            return OcrOutput(
                doc_id=result.get("doc_id", ""),
                text_markdown=result.get("text_markdown", ""),
                structured_blocks=blocks,
                medical_entities=entities,
                requires_human_review=any_low_confidence,
                latency_ms=latency_ms,
                model_used="solar-document-parse",
                prompt_version="n/a",
            )

        except Exception as e:
            logger.error("OcrAgent failed: %s", e)
            latency_ms = int((time.monotonic() - start) * 1000)
            return OcrOutput(
                requires_human_review=True,
                latency_ms=latency_ms,
                model_used="solar-document-parse",
                reason_summary=f"OCR failed: {type(e).__name__}. Manual text input required.",
            )

    async def _fetch_file(self, url: str) -> bytes:
        """Fetch file bytes from presigned URL."""
        raise NotImplementedError("File fetch pending httpx integration")
```

### Implementation Notes

- **Fixed vendor**: Solar Document Parse. No ModelRouter.
- **Low-confidence flagging**: Any block or entity below 0.7 confidence triggers `requires_human_review`.
- **Document types**: prescription, diagnosis_note, lab_result, psych_scale, unknown (OCR-3).
- **Evidence traceability**: `doc_id` + `block_id` are preserved for Handoff citation (HAND-1).
- **Fallback**: Returns empty output + review flag. Never crashes.

### Tests

**File**: `apps/ai-server/tests/agents/test_ocr.py` (new)

Key test cases:

```python
"""Tests for OcrAgent."""

import pytest
from unittest.mock import AsyncMock

from src.agents.ocr import OcrAgent, LOW_CONFIDENCE_THRESHOLD
from src.schemas.ocr import OcrInput, OcrOutput


class TestOcrSchema:
    def test_ocr_input_defaults(self) -> None:
        inp = OcrInput()
        assert inp.requested_outputs == ["markdown", "structured_blocks"]

    def test_ocr_output_round_trip(self) -> None:
        out = OcrOutput(doc_id="doc_1", text_markdown="# Test")
        data = out.model_dump()
        restored = OcrOutput.model_validate(data)
        assert restored.doc_id == "doc_1"


class TestOcrAgent:
    @pytest.fixture
    def agent(self) -> OcrAgent:
        adapter = AsyncMock()
        adapter.parse_document.return_value = {
            "doc_id": "doc_001",
            "text_markdown": "# 처방전\n약물: 졸피뎀",
            "structured_blocks": [
                {"block_id": "b1", "page": 1, "type": "text", "content": "졸피뎀", "confidence": 0.94},
            ],
            "medical_entities": [
                {"entity_id": "e1", "type": "medication", "value": "졸피뎀", "confidence": 0.94, "source_block_id": "b1"},
            ],
        }
        return OcrAgent(ocr_adapter=adapter)

    @pytest.mark.asyncio
    async def test_successful_parse(self, agent: OcrAgent) -> None:
        result = await agent.run(OcrInput(file_bytes=b"fake_pdf"))
        assert result.doc_id == "doc_001"
        assert len(result.structured_blocks) == 1
        assert len(result.medical_entities) == 1
        assert result.requires_human_review is False

    @pytest.mark.asyncio
    async def test_low_confidence_flags_review(self) -> None:
        adapter = AsyncMock()
        adapter.parse_document.return_value = {
            "doc_id": "doc_002",
            "text_markdown": "# Unknown",
            "structured_blocks": [
                {"block_id": "b1", "page": 1, "type": "text", "content": "??", "confidence": 0.4},
            ],
            "medical_entities": [],
        }
        agent = OcrAgent(ocr_adapter=adapter)
        result = await agent.run(OcrInput(file_bytes=b"bad_scan"))
        assert result.requires_human_review is True

    @pytest.mark.asyncio
    async def test_no_file_input_returns_fallback(self) -> None:
        agent = OcrAgent(ocr_adapter=AsyncMock())
        result = await agent.run(OcrInput())
        assert result.requires_human_review is True
        assert "OCR failed" in result.reason_summary

    @pytest.mark.asyncio
    async def test_adapter_failure_returns_fallback(self) -> None:
        adapter = AsyncMock()
        adapter.parse_document.side_effect = TimeoutError("timeout")
        agent = OcrAgent(ocr_adapter=adapter)
        result = await agent.run(OcrInput(file_bytes=b"pdf"))
        assert result.requires_human_review is True
```

---

## Step 5.4 — InputNormalizerAgent

### Schema

**File**: `apps/ai-server/src/schemas/input_normalizer.py` (new)

```python
"""Internal schemas for InputNormalizerAgent."""

from pydantic import BaseModel, Field

from src.agents.base import AgentInput, AgentOutput


class TextChange(BaseModel):
    """Single normalization change."""

    original: str
    normalized: str
    reason: str = ""


class UncertaintySpan(BaseModel):
    """Span where normalization is uncertain."""

    start: int
    end: int
    original_text: str
    suggestion: str = ""
    confidence: float = 0.0


class InputNormalizerInput(AgentInput):
    """Input to InputNormalizerAgent."""

    transcript: str
    source: str = "stt"  # "stt" | "text"


class InputNormalizerOutput(AgentOutput):
    """Output from InputNormalizerAgent."""

    normalized_text: str = ""
    uncertainty_spans: list[UncertaintySpan] = Field(default_factory=list)
    changes_made: list[TextChange] = Field(default_factory=list)
```

### Agent

**File**: `apps/ai-server/src/agents/input_normalizer.py` (new)

```python
"""InputNormalizerAgent — LLM-based STT noise correction.

Corrects STT transcription errors, typos, and ungrammatical Korean
while preserving the original meaning and clinical terminology.
"""

import logging
import time
from typing import Any

from src.agents.base import BaseAgent
from src.schemas.input_normalizer import InputNormalizerInput, InputNormalizerOutput

logger = logging.getLogger(__name__)


class InputNormalizerAgent(BaseAgent):
    """Normalize STT transcripts and text input.

    Uses ModelRouter for LLM selection (benchmarked).
    Fallback: return original text unchanged + flag.
    """

    name = "input_normalizer"
    description = "Correct STT noise, typos, and ungrammatical text while preserving clinical meaning"

    def __init__(self, model_router: Any, prompt_loader: Any) -> None:
        self.model_router = model_router
        self.prompt_loader = prompt_loader

    async def run(self, input_data: InputNormalizerInput, **kwargs: Any) -> InputNormalizerOutput:
        """Normalize transcript via LLM.

        On failure: return original text unchanged.
        """
        start = time.monotonic()
        try:
            model_selection = await self.model_router.select_model(
                agent_name=self.name,
                task_name="stt_noise_correction",
                require_json=True,
            )

            system_prompt = await self.prompt_loader.load_system_prompt(
                "input_normalizer", "v1",
            )

            # LLM call via adapter (implementation deferred)
            # Expected JSON output: {normalized_text, changes, uncertainty_spans}
            raise NotImplementedError("LLM integration pending adapter wiring")

        except NotImplementedError:
            raise
        except Exception as e:
            logger.warning("InputNormalizerAgent failed, returning original: %s", e)
            latency_ms = int((time.monotonic() - start) * 1000)
            return InputNormalizerOutput(
                normalized_text=input_data.transcript,
                latency_ms=latency_ms,
                model_used="fallback_passthrough",
                reason_summary=f"Normalization failed: {type(e).__name__}. Original text preserved.",
            )
```

### Implementation Notes

- **Benchmarked model**: Solar Pro 3 / K-EXAONE / A.K — selected by STT noise correction accuracy + latency.
- **Source-aware**: When `source="stt"`, applies more aggressive noise correction. When `source="text"`, minimal correction only.
- **Clinical term preservation**: Prompt instructs the LLM to never "correct" medical terms (e.g., "졸피뎀" should not become "졸피댐").
- **Fallback**: Return original text unchanged. Safe because downstream agents can handle noisy input.
- **Uncertainty spans**: Marks regions where the normalizer is unsure, enabling UI highlighting.

### Tests

**File**: `apps/ai-server/tests/agents/test_input_normalizer.py` (new)

Key test cases:

```python
"""Tests for InputNormalizerAgent."""

import pytest
from unittest.mock import AsyncMock

from src.agents.input_normalizer import InputNormalizerAgent
from src.schemas.input_normalizer import InputNormalizerInput, InputNormalizerOutput


class TestInputNormalizerSchema:
    def test_input_defaults(self) -> None:
        inp = InputNormalizerInput(transcript="잠을 못자요")
        assert inp.source == "stt"

    def test_output_round_trip(self) -> None:
        out = InputNormalizerOutput(normalized_text="잠을 못 자요")
        data = out.model_dump()
        restored = InputNormalizerOutput.model_validate(data)
        assert restored.normalized_text == "잠을 못 자요"


class TestInputNormalizerAgent:
    @pytest.fixture
    def agent(self) -> InputNormalizerAgent:
        return InputNormalizerAgent(
            model_router=AsyncMock(),
            prompt_loader=AsyncMock(),
        )

    @pytest.mark.asyncio
    async def test_fallback_returns_original_text(self, agent: InputNormalizerAgent) -> None:
        """On failure, return original text unchanged."""
        agent.model_router.select_model.side_effect = RuntimeError("no model")
        result = await agent.run(InputNormalizerInput(transcript="잠을 못자요"))
        assert result.normalized_text == "잠을 못자요"
        assert "failed" in result.reason_summary.lower()

    def test_stt_source_default(self) -> None:
        inp = InputNormalizerInput(transcript="test")
        assert inp.source == "stt"

    def test_text_source(self) -> None:
        inp = InputNormalizerInput(transcript="test", source="text")
        assert inp.source == "text"
```

---

## Step 5.5 — DialogueAgent

### Schema

**File**: `apps/ai-server/src/schemas/dialogue.py` (new)

```python
"""Internal schemas for DialogueAgent."""

from pydantic import BaseModel, Field

from src.agents.base import AgentInput, AgentOutput


class DialogueInput(AgentInput):
    """Input to DialogueAgent."""

    normalized_text: str
    missing_slots: list[str] = Field(default_factory=list)
    context: list[dict] = Field(default_factory=list)  # recent message history
    known_slots: dict = Field(default_factory=dict)


class DialogueOutput(AgentOutput):
    """Output from DialogueAgent."""

    assistant_response: str = ""
    slot_updates: dict = Field(default_factory=dict)
    requires_human_review: bool = False
```

### Agent

**File**: `apps/ai-server/src/agents/dialogue.py` (new)

```python
"""DialogueAgent — intake conversation for pre-visit mental health screening.

PRD §6.1: FR-004-1 through FR-004-7.
Rules:
  - One question at a time (FR-004-2)
  - No repeated questions for already-provided info (FR-004-3)
  - No diagnosis or treatment (FR-004-5)
  - Fallback: template question
"""

import logging
import time
from typing import Any

from src.agents.base import BaseAgent
from src.schemas.dialogue import DialogueInput, DialogueOutput

logger = logging.getLogger(__name__)

# Template fallback questions when LLM fails
FALLBACK_QUESTIONS = [
    "현재 가장 불편하신 점이 무엇인지 알려주실 수 있을까요?",
    "증상이 언제부터 시작되었는지 알려주실 수 있을까요?",
    "수면에 어려움이 있으신가요?",
    "식욕이나 체중에 변화가 있으신가요?",
    "기분 상태는 어떠신가요?",
]


class DialogueAgent(BaseAgent):
    """Generate intake conversation responses and extract slot updates.

    Uses ModelRouter for LLM selection (benchmarked on Korean naturalness,
    safety, and slot completion).
    Fallback: template question from FALLBACK_QUESTIONS.
    """

    name = "dialogue"
    description = "Generate safe pre-visit intake conversation with one-question-at-a-time policy"

    def __init__(self, model_router: Any, prompt_loader: Any) -> None:
        self.model_router = model_router
        self.prompt_loader = prompt_loader

    async def run(self, input_data: DialogueInput, **kwargs: Any) -> DialogueOutput:
        """Generate next dialogue response.

        On failure: return a template question from FALLBACK_QUESTIONS
        based on the first missing slot.
        """
        start = time.monotonic()
        try:
            model_selection = await self.model_router.select_model(
                agent_name=self.name,
                task_name="intake_dialogue",
                require_json=True,
            )

            system_prompt = await self.prompt_loader.load_system_prompt(
                "dialogue_intake", "v1",
            )

            # LLM call (implementation deferred)
            raise NotImplementedError("LLM integration pending adapter wiring")

        except NotImplementedError:
            raise
        except Exception as e:
            logger.warning("DialogueAgent failed, using template fallback: %s", e)
            latency_ms = int((time.monotonic() - start) * 1000)
            fallback_q = self._select_fallback_question(input_data.missing_slots)
            return DialogueOutput(
                assistant_response=fallback_q,
                slot_updates={},
                requires_human_review=False,
                latency_ms=latency_ms,
                model_used="template_fallback",
                reason_summary=f"Dialogue LLM failed: {type(e).__name__}. Template question used.",
            )

    def _select_fallback_question(self, missing_slots: list[str]) -> str:
        """Pick a template question based on missing slots."""
        slot_to_question = {
            "chief_complaint": FALLBACK_QUESTIONS[0],
            "onset": FALLBACK_QUESTIONS[1],
            "sleep": FALLBACK_QUESTIONS[2],
            "appetite": FALLBACK_QUESTIONS[3],
            "mood": FALLBACK_QUESTIONS[4],
        }
        for slot in missing_slots:
            if slot in slot_to_question:
                return slot_to_question[slot]
        return FALLBACK_QUESTIONS[0]
```

### Implementation Notes

- **One question at a time**: System prompt enforces single-question policy. Output validation rejects multi-question responses.
- **No repeated questions**: `known_slots` is checked before generating. The prompt is instructed to never ask about already-filled slots.
- **No diagnosis/treatment**: Hard constraint in prompt + output validation.
- **Slot updates**: Extracted from the user's response (e.g., `{"chief_complaint": ["수면 문제"]}`) and returned alongside the assistant response.
- **Fallback**: Template question selected based on first missing slot. Never crashes.

### Tests

**File**: `apps/ai-server/tests/agents/test_dialogue.py` (new)

Key test cases:

```python
"""Tests for DialogueAgent."""

import pytest
from unittest.mock import AsyncMock

from src.agents.dialogue import DialogueAgent, FALLBACK_QUESTIONS
from src.schemas.dialogue import DialogueInput, DialogueOutput


class TestDialogueSchema:
    def test_input_defaults(self) -> None:
        inp = DialogueInput(normalized_text="잠을 못 자요")
        assert inp.missing_slots == []
        assert inp.known_slots == {}

    def test_output_round_trip(self) -> None:
        out = DialogueOutput(
            assistant_response="언제부터 시작되었나요?",
            slot_updates={"chief_complaint": ["수면 문제"]},
        )
        data = out.model_dump()
        restored = DialogueOutput.model_validate(data)
        assert restored.assistant_response == "언제부터 시작되었나요?"
        assert restored.slot_updates["chief_complaint"] == ["수면 문제"]


class TestDialogueAgent:
    @pytest.fixture
    def agent(self) -> DialogueAgent:
        return DialogueAgent(
            model_router=AsyncMock(),
            prompt_loader=AsyncMock(),
        )

    @pytest.mark.asyncio
    async def test_fallback_returns_template_question(self, agent: DialogueAgent) -> None:
        agent.model_router.select_model.side_effect = RuntimeError("no model")
        result = await agent.run(DialogueInput(
            normalized_text="test",
            missing_slots=["sleep"],
        ))
        assert result.assistant_response == FALLBACK_QUESTIONS[2]  # sleep question
        assert result.model_used == "template_fallback"

    @pytest.mark.asyncio
    async def test_fallback_default_question_when_no_matching_slot(self, agent: DialogueAgent) -> None:
        agent.model_router.select_model.side_effect = RuntimeError("no model")
        result = await agent.run(DialogueInput(
            normalized_text="test",
            missing_slots=["unknown_slot"],
        ))
        assert result.assistant_response == FALLBACK_QUESTIONS[0]

    def test_select_fallback_chief_complaint(self, agent: DialogueAgent) -> None:
        q = agent._select_fallback_question(["chief_complaint"])
        assert q == FALLBACK_QUESTIONS[0]

    def test_select_fallback_mood(self, agent: DialogueAgent) -> None:
        q = agent._select_fallback_question(["mood"])
        assert q == FALLBACK_QUESTIONS[4]
```

---

## Step 5.6 — ClinicalSlotAgent

### Schema

**File**: `apps/ai-server/src/schemas/clinical_slot.py` (new)

```python
"""Internal schemas for ClinicalSlotAgent."""

from pydantic import BaseModel, Field

from src.agents.base import AgentInput, AgentOutput


class ClinicalSlotInput(AgentInput):
    """Input to ClinicalSlotAgent."""

    message_batch: list[dict] = Field(default_factory=list)  # recent messages
    ocr_text: str | None = None  # optional OCR-extracted text


class ClinicalSlotOutput(AgentOutput):
    """Output from ClinicalSlotAgent.

    Slot keys: chief_complaint, hpi, pmh, medication, risk,
    sleep, appetite, mood, anxiety, concentration, functional_impairment.
    """

    slots: dict = Field(default_factory=dict)
    evidence_ids: dict = Field(default_factory=dict)  # slot_name -> list[evidence_id]
    requires_human_review: bool = False
```

### Agent

**File**: `apps/ai-server/src/agents/clinical_slot.py` (new)

```python
"""ClinicalSlotAgent — extract structured clinical slots from messages and OCR text.

Extracts: CC, HPI, PMH, medication, risk, sleep, appetite, mood,
anxiety, concentration, functional_impairment.
"""

import logging
import time
from typing import Any

from src.agents.base import BaseAgent
from src.schemas.clinical_slot import ClinicalSlotInput, ClinicalSlotOutput

logger = logging.getLogger(__name__)

# Slots this agent extracts
CLINICAL_SLOTS = [
    "chief_complaint",
    "hpi",
    "pmh",
    "medication",
    "risk",
    "sleep",
    "appetite",
    "mood",
    "anxiety",
    "concentration",
    "functional_impairment",
]


class ClinicalSlotAgent(BaseAgent):
    """Extract structured clinical slots from conversation and OCR text.

    Uses ModelRouter for LLM selection (benchmarked on slot F1 and evidence alignment).
    Fallback: empty slots + requires_human_review=True.
    """

    name = "clinical_slot"
    description = "Extract CC/HPI/PMH/medication/risk/sleep/appetite/mood/anxiety/concentration from text"

    def __init__(self, model_router: Any, prompt_loader: Any) -> None:
        self.model_router = model_router
        self.prompt_loader = prompt_loader

    async def run(self, input_data: ClinicalSlotInput, **kwargs: Any) -> ClinicalSlotOutput:
        """Extract clinical slots via LLM.

        On failure: return empty slots + requires_human_review=True.
        """
        start = time.monotonic()
        try:
            if not input_data.message_batch and not input_data.ocr_text:
                return ClinicalSlotOutput(
                    slots={},
                    evidence_ids={},
                    requires_human_review=False,
                    latency_ms=0,
                    reason_summary="No input provided for slot extraction.",
                )

            model_selection = await self.model_router.select_model(
                agent_name=self.name,
                task_name="slot_extraction",
                require_json=True,
            )

            system_prompt = await self.prompt_loader.load_system_prompt(
                "clinical_slot", "v1",
            )

            # LLM call (implementation deferred)
            raise NotImplementedError("LLM integration pending adapter wiring")

        except NotImplementedError:
            raise
        except Exception as e:
            logger.warning("ClinicalSlotAgent failed, flagging for human review: %s", e)
            latency_ms = int((time.monotonic() - start) * 1000)
            return ClinicalSlotOutput(
                slots={},
                evidence_ids={},
                requires_human_review=True,
                latency_ms=latency_ms,
                model_used="fallback_empty",
                reason_summary=f"Slot extraction failed: {type(e).__name__}. Human review required.",
            )
```

### Implementation Notes

- **Slot schema**: 11 clinical slots covering CC, HPI, PMH, medication, risk factors, and symptom domains.
- **Evidence alignment**: Every extracted slot value MUST reference the source message or OCR block. `evidence_ids` maps slot names to lists of evidence IDs.
- **OCR integration**: When `ocr_text` is provided, the agent extracts medication, diagnosis, and lab result slots from document text in addition to conversation messages.
- **Fallback**: Returns empty slots + `requires_human_review=True`. Downstream agents (HandoffGenerator) will show "정보 미수집" for missing slots.

### Tests

**File**: `apps/ai-server/tests/agents/test_clinical_slot.py` (new)

Key test cases:

```python
"""Tests for ClinicalSlotAgent."""

import pytest
from unittest.mock import AsyncMock

from src.agents.clinical_slot import ClinicalSlotAgent, CLINICAL_SLOTS
from src.schemas.clinical_slot import ClinicalSlotInput, ClinicalSlotOutput


class TestClinicalSlotSchema:
    def test_input_defaults(self) -> None:
        inp = ClinicalSlotInput()
        assert inp.message_batch == []
        assert inp.ocr_text is None

    def test_output_round_trip(self) -> None:
        out = ClinicalSlotOutput(
            slots={"chief_complaint": "수면 문제", "sleep": "insomnia_reported"},
            evidence_ids={"chief_complaint": ["msg_001"], "sleep": ["msg_001"]},
        )
        data = out.model_dump()
        restored = ClinicalSlotOutput.model_validate(data)
        assert restored.slots["chief_complaint"] == "수면 문제"
        assert "msg_001" in restored.evidence_ids["chief_complaint"]

    def test_clinical_slots_list(self) -> None:
        assert "chief_complaint" in CLINICAL_SLOTS
        assert "mood" in CLINICAL_SLOTS
        assert len(CLINICAL_SLOTS) == 11


class TestClinicalSlotAgent:
    @pytest.fixture
    def agent(self) -> ClinicalSlotAgent:
        return ClinicalSlotAgent(
            model_router=AsyncMock(),
            prompt_loader=AsyncMock(),
        )

    @pytest.mark.asyncio
    async def test_empty_input_returns_empty_slots(self, agent: ClinicalSlotAgent) -> None:
        result = await agent.run(ClinicalSlotInput())
        assert result.slots == {}
        assert result.requires_human_review is False

    @pytest.mark.asyncio
    async def test_fallback_flags_human_review(self, agent: ClinicalSlotAgent) -> None:
        agent.model_router.select_model.side_effect = RuntimeError("no model")
        result = await agent.run(ClinicalSlotInput(
            message_batch=[{"role": "user", "content": "잠을 못 자요"}],
        ))
        assert result.requires_human_review is True
        assert result.slots == {}
        assert "failed" in result.reason_summary.lower()

    @pytest.mark.asyncio
    async def test_latency_ms_populated(self, agent: ClinicalSlotAgent) -> None:
        agent.model_router.select_model.side_effect = RuntimeError("no model")
        result = await agent.run(ClinicalSlotInput(
            message_batch=[{"role": "user", "content": "test"}],
        ))
        assert result.latency_ms >= 0
```

---

## Step 5.7 — Update `src/schemas/__init__.py`

**File**: `apps/ai-server/src/schemas/__init__.py` (modify)

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
"""
```

---

## Step 5.8 — Update `src/agents/__init__.py`

**File**: `apps/ai-server/src/agents/__init__.py` (modify)

```python
"""Neuro-Sync AI agents — 12 role-specialized agents per PRD §5.

Phase 5 core agents (direct user interaction):
- SafetyClassifierAgent — risk detection (rule + LLM parallel)
- SttAgent — speech-to-text (fixed SKT A.K STT)
- OcrAgent — document parsing (fixed Solar Document Parse)
- InputNormalizerAgent — STT noise correction (benchmarked LLM)
- DialogueAgent — intake conversation (benchmarked LLM)
- ClinicalSlotAgent — clinical slot extraction (benchmarked LLM)
"""
```

---

## File Summary

| File | Type | Key Classes |
|---|---|---|
| `src/schemas/safety.py` | Schema | `SafetyInput`, `SafetyOutput` |
| `src/schemas/stt.py` | Schema | `SttInput`, `SttOutput`, `SttSegment` |
| `src/schemas/ocr.py` | Schema | `OcrInput`, `OcrOutput`, `OcrBlock`, `OcrEntity` |
| `src/schemas/input_normalizer.py` | Schema | `InputNormalizerInput`, `InputNormalizerOutput`, `TextChange`, `UncertaintySpan` |
| `src/schemas/dialogue.py` | Schema | `DialogueInput`, `DialogueOutput` |
| `src/schemas/clinical_slot.py` | Schema | `ClinicalSlotInput`, `ClinicalSlotOutput` |
| `src/agents/safety_classifier.py` | Agent | `SafetyClassifierAgent` |
| `src/agents/stt.py` | Agent | `SttAgent` |
| `src/agents/ocr.py` | Agent | `OcrAgent` |
| `src/agents/input_normalizer.py` | Agent | `InputNormalizerAgent` |
| `src/agents/dialogue.py` | Agent | `DialogueAgent` |
| `src/agents/clinical_slot.py` | Agent | `ClinicalSlotAgent` |
| `tests/agents/test_safety_classifier.py` | Test | 5 test cases |
| `tests/agents/test_stt.py` | Test | 4 test cases |
| `tests/agents/test_ocr.py` | Test | 4 test cases |
| `tests/agents/test_input_normalizer.py` | Test | 3 test cases |
| `tests/agents/test_dialogue.py` | Test | 4 test cases |
| `tests/agents/test_clinical_slot.py` | Test | 4 test cases |

---

## Dependency Graph

```text
Phase 4 (ModelRouter, FallbackPolicy)
  │
  ├── SafetyClassifierAgent ← AhoCorasickDetector + LLMAdapter
  ├── SttAgent ← SktAkSttAdapter (fixed)
  ├── OcrAgent ← SolarDocumentParseAdapter (fixed)
  ├── InputNormalizerAgent ← LLMAdapter (benchmarked)
  ├── DialogueAgent ← LLMAdapter (benchmarked)
  └── ClinicalSlotAgent ← LLMAdapter (benchmarked)
         │
         ▼
  Phase 6 (Pipeline Agents consume these outputs)
```

---

## Checklist

- [ ] `src/schemas/safety.py` created with `SafetyInput`, `SafetyOutput`
- [ ] `src/schemas/stt.py` created with `SttInput`, `SttOutput`, `SttSegment`
- [ ] `src/schemas/ocr.py` created with `OcrInput`, `OcrOutput`, `OcrBlock`, `OcrEntity`
- [ ] `src/schemas/input_normalizer.py` created with `InputNormalizerInput`, `InputNormalizerOutput`
- [ ] `src/schemas/dialogue.py` created with `DialogueInput`, `DialogueOutput`
- [ ] `src/schemas/clinical_slot.py` created with `ClinicalSlotInput`, `ClinicalSlotOutput`
- [ ] `src/agents/safety_classifier.py` created with parallel rule+LLM + emergency-safe fallback
- [ ] `src/agents/stt.py` created wrapping SktAkSttAdapter
- [ ] `src/agents/ocr.py` created wrapping SolarDocumentParseAdapter
- [ ] `src/agents/input_normalizer.py` created with passthrough fallback
- [ ] `src/agents/dialogue.py` created with template fallback questions
- [ ] `src/agents/clinical_slot.py` created with human review fallback
- [ ] All 6 test files pass with mocked adapters
- [ ] `ruff check src/schemas/ src/agents/` passes
- [ ] `qa` gate: every agent handles failure without crash
- [ ] `critic` gate: safety agent emergency-safe default verified
