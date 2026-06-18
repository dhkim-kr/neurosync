# Phase 2: Shared Contracts

> **Depends on**: Phase 1 (common types for reference)
> **Blocks**: Phase 5 (agents use contract types for route-level I/O)
> **Agent owner**: `developer`
> **Gate**: `critic` — interface review against PRD §7 API contracts

---

## Objective

Define the Platform↔AI interface Pydantic models in `packages/shared-contracts/python/src/contracts/`. These are the **single source of truth** for request/response shapes across both teams. All 6 endpoint contracts from PRD §7 must be represented.

## Success Criteria

- [ ] All 6 contract modules created: `chat.py`, `safety.py`, `stt.py`, `ocr.py`, `handoff.py`, `eval.py`
- [ ] `__init__.py` re-exports all request/response classes
- [ ] Every field from PRD §7.1–§7.6 is present in the matching model
- [ ] `from contracts import ChatRequest, ChatResponse, SafetyRequest, SafetyResponse` imports cleanly
- [ ] Round-trip `model_dump()` → `model_validate()` works for every model
- [ ] `ruff check src/contracts/` passes

---

## Step 2.1 — `contracts/chat.py`

**File**: `packages/shared-contracts/python/src/contracts/chat.py` (new)
**PRD reference**: §7.1 `POST /ai/chat/respond`

```python
"""Chat respond contract — POST /ai/chat/respond."""

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str  # "user" | "assistant" | "system"
    content: str
    created_at: str | None = None


class ConsentFlags(BaseModel):
    ai_processing: bool = False
    external_api: bool = False


class SessionContext(BaseModel):
    known_slots: dict = Field(default_factory=dict)
    risk_state: str = "none"
    consent_flags: ConsentFlags = Field(default_factory=ConsentFlags)


class ChatRequest(BaseModel):
    session_id: str
    patient_pseudo_id: str
    messages: list[ChatMessage]
    session_context: SessionContext = Field(default_factory=SessionContext)
    response_mode: str = "sync"  # "sync" | "stream"


class ChatResponse(BaseModel):
    text: str
    model_used: str = ""
    agent_trace_id: str = ""
    slot_updates: dict = Field(default_factory=dict)
    risk_level: str = "none"
    requires_human_review: bool = False
```

---

## Step 2.2 — `contracts/safety.py`

**File**: `packages/shared-contracts/python/src/contracts/safety.py` (new)
**PRD reference**: §7.2 `POST /ai/safety/classify`

```python
"""Safety classify contract — POST /ai/safety/classify."""

from pydantic import BaseModel, Field


class SafetyRequest(BaseModel):
    message: str
    prev_context: list[str] = Field(default_factory=list)
    locale: str = "ko-KR"


class SafetyResponse(BaseModel):
    risk_level: str  # none | low | medium | high | critical
    risk_categories: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    recommended_action: str = ""
    user_safe_message_template_id: str = ""
    model_used: str = ""
    requires_human_review: bool = False
```

---

## Step 2.3 — `contracts/stt.py`

**File**: `packages/shared-contracts/python/src/contracts/stt.py` (new)
**PRD reference**: §7.3 `POST /ai/stt/transcribe`

```python
"""STT transcribe contract — POST /ai/stt/transcribe."""

from pydantic import BaseModel, Field


class SttSegment(BaseModel):
    start_ms: int
    end_ms: int
    text: str


class SttRequest(BaseModel):
    audio_file_url: str
    audio_format: str = "wav"
    language: str = "ko-KR"
    prev_context_hint: str | None = None
    vendor: str = "skt-ak-stt"


class SttResponse(BaseModel):
    text: str
    confidence: float | None = None  # None when vendor doesn't provide (A.X STT)
    vendor: str = ""
    segments: list[SttSegment] = Field(default_factory=list)
    low_confidence_spans: list[SttSegment] = Field(default_factory=list)
    requires_user_confirmation: bool = True
```

---

## Step 2.4 — `contracts/ocr.py`

**File**: `packages/shared-contracts/python/src/contracts/ocr.py` (new)
**PRD reference**: §7.4 `POST /ai/ocr/parse`

```python
"""OCR parse contract — POST /ai/ocr/parse."""

from pydantic import BaseModel, Field


class StructuredBlock(BaseModel):
    block_id: str
    page: int = 1
    type: str = "text"  # text | table | image | chart
    content: str = ""
    confidence: float = 0.0


class MedicalEntity(BaseModel):
    entity_id: str = ""
    type: str  # medication | diagnosis | lab_result | date | institution | score
    value: str
    confidence: float = 0.0
    source_block_id: str = ""
    requires_human_review: bool = False


class OcrRequest(BaseModel):
    file_url: str
    doc_type: str | None = None  # prescription | diagnosis_note | lab_result | psych_scale | unknown
    requested_outputs: list[str] = Field(
        default_factory=lambda: ["markdown", "structured_blocks"]
    )
    vendor: str = "solar-document-parse"


class OcrResponse(BaseModel):
    doc_id: str = ""
    text_markdown: str = ""
    structured_blocks: list[StructuredBlock] = Field(default_factory=list)
    medical_entities: list[MedicalEntity] = Field(default_factory=list)
    vendor: str = "solar-document-parse"
    requires_human_review: bool = False
```

---

## Step 2.5 — `contracts/handoff.py`

**File**: `packages/shared-contracts/python/src/contracts/handoff.py` (new)
**PRD reference**: §7.5 `POST /ai/handoff/generate`

```python
"""Handoff generate contract — POST /ai/handoff/generate."""

from pydantic import BaseModel, Field


class ScaleScore(BaseModel):
    score: int
    severity: str = ""


class Citation(BaseModel):
    claim_id: str
    source_type: str  # message | scale | document_block | risk_event | prior_handoff
    source_id: str


class Verification(BaseModel):
    unsupported_claim_count: int = 0
    diagnosis_or_treatment_violation: bool = False
    requires_clinician_review: bool = True


class HandoffRequest(BaseModel):
    session_id: str
    patient_pseudo_id: str
    messages: list[dict] = Field(default_factory=list)
    phq9: ScaleScore | None = None
    gad7: ScaleScore | None = None
    doc_texts: list[dict] = Field(default_factory=list)
    risk_events: list[dict] = Field(default_factory=list)
    evidence_packets: list[dict] = Field(default_factory=list)


class HandoffResponse(BaseModel):
    report_markdown: str
    citations: list[Citation] = Field(default_factory=list)
    model_used: str = ""
    verification: Verification = Field(default_factory=Verification)
```

---

## Step 2.6 — `contracts/eval.py`

**File**: `packages/shared-contracts/python/src/contracts/eval.py` (new)
**PRD reference**: §7.6 `POST /ai/eval/model-comparison`

```python
"""Eval model-comparison contract — POST /ai/eval/model-comparison."""

from pydantic import BaseModel, Field


class ModelMetrics(BaseModel):
    recall_high_critical: float | None = None
    precision_high_critical: float | None = None
    latency_p95_ms: float | None = None
    json_validity: float | None = None
    unsupported_claim_rate: float | None = None
    slot_f1: float | None = None
    clinician_score: float | None = None


class EvalRequest(BaseModel):
    agent_name: str
    task_name: str
    candidate_models: list[str] = Field(default_factory=list)
    dataset_version: str = ""
    metrics: list[str] = Field(default_factory=list)


class EvalResponse(BaseModel):
    agent_name: str
    winner: str = ""
    secondary: str = ""
    fallback: str = ""
    metrics: dict[str, ModelMetrics] = Field(default_factory=dict)
    release_gate_passed: bool = False
```

---

## Step 2.7 — Update `contracts/__init__.py`

**File**: `packages/shared-contracts/python/src/contracts/__init__.py` (modify)

```python
"""Neuro-Sync shared contracts (Python).

6 AI interface Pydantic models — single source of truth.
PRD §0.3 + docs/ai/PRD_ai_v.0.0.0.0.md §7 동기 갱신 필수.
"""

__version__ = "0.2.0"

from contracts.chat import ChatMessage, ChatRequest, ChatResponse, ConsentFlags, SessionContext
from contracts.eval import EvalRequest, EvalResponse, ModelMetrics
from contracts.handoff import (
    Citation,
    HandoffRequest,
    HandoffResponse,
    ScaleScore,
    Verification,
)
from contracts.ocr import MedicalEntity, OcrRequest, OcrResponse, StructuredBlock
from contracts.safety import SafetyRequest, SafetyResponse
from contracts.stt import SttRequest, SttResponse, SttSegment

__all__ = [
    # chat
    "ChatMessage", "ChatRequest", "ChatResponse", "ConsentFlags", "SessionContext",
    # safety
    "SafetyRequest", "SafetyResponse",
    # stt
    "SttRequest", "SttResponse", "SttSegment",
    # ocr
    "OcrRequest", "OcrResponse", "StructuredBlock", "MedicalEntity",
    # handoff
    "HandoffRequest", "HandoffResponse", "Citation", "Verification", "ScaleScore",
    # eval
    "EvalRequest", "EvalResponse", "ModelMetrics",
]
```

---

## Test Requirements

**File**: `packages/shared-contracts/python/tests/test_contracts.py` (new)

Test every request/response pair:
1. Construct with required fields only — defaults fill correctly
2. Construct with all fields — no validation error
3. `model_dump()` → `model_validate()` round-trip produces equal model
4. JSON serialization → deserialization works (`model_dump_json()` → `model_validate_json()`)

---

## Checklist

- [ ] `contracts/chat.py` created with `ChatRequest`, `ChatResponse`
- [ ] `contracts/safety.py` created with `SafetyRequest`, `SafetyResponse`
- [ ] `contracts/stt.py` created with `SttRequest`, `SttResponse`
- [ ] `contracts/ocr.py` created with `OcrRequest`, `OcrResponse`
- [ ] `contracts/handoff.py` created with `HandoffRequest`, `HandoffResponse`
- [ ] `contracts/eval.py` created with `EvalRequest`, `EvalResponse`
- [ ] `contracts/__init__.py` re-exports all models, version bumped to `0.2.0`
- [ ] Round-trip serialization tests pass for all 12 models
- [ ] `ruff check src/contracts/` passes
- [ ] `critic` review confirms all PRD §7 fields are present
