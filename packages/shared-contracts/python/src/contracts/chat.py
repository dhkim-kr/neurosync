"""POST /ai/chat/respond — request / response schema.

Single source of truth between apps/api (consumer, WS gateway) and
apps/ai-server (producer, LLM dialogue). PRD §0.3 contract — change requires
both PRDs updated simultaneously. SLA: 첫 토큰 < 800ms (PRD §4.1).

Separation of concerns:
- AI server generates the assistant reply AND decides which of the structured
  intake items have been collected so far (`progress.collected_items`). The
  13-item taxonomy is an AI-domain decision; the platform only displays the
  ratio and persists it on the session.
- Streaming (`ai:token`) is deferred until the AI server exposes SSE; this
  contract is the non-streaming full-reply shape consumed for `ai:complete`.
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ChatMessage(BaseModel):
    role: str = Field(description="'user' | 'ai' | 'system'")
    content: str

    model_config = ConfigDict(extra="forbid")


class ChatProgress(BaseModel):
    """Intake completeness — drives the patient-facing progress bar (FR-004).

    `ratio` is AI-computed (collected / total) and is the value the platform
    trusts for display + the §5.5 flow gate (≥0.7 → questionnaire step).
    """

    collected_items: list[str] = Field(
        default_factory=list,
        description="Keys of the structured items gathered so far (e.g. "
        "'chief_complaint', 'onset'). Cumulative across the conversation.",
    )
    total_items: int = Field(default=13, ge=1)
    ratio: float = Field(ge=0.0, le=1.0)

    model_config = ConfigDict(extra="forbid")


class GroundingCase(BaseModel):
    """RAG: 유사 심리상담 사례 (남의 사례, grounding)."""

    disease_class: str = Field(description="DEPRESSION | ANXIETY | ADDICTION")
    situation: str
    score: float = Field(ge=0.0, le=1.0)

    model_config = ConfigDict(extra="forbid")


class GroundingPast(BaseModel):
    """RAG: 환자 본인의 과거 세션 요약 (개인화). 플랫폼이 patient_id로 필터·복호화."""

    disease_class: str | None = None
    situation: str
    score: float = Field(ge=0.0, le=1.0)

    model_config = ConfigDict(extra="forbid")


class GroundingKnowledge(BaseModel):
    """RAG: 정신과 지식 QA."""

    question: str
    answer: str
    score: float = Field(ge=0.0, le=1.0)

    model_config = ConfigDict(extra="forbid")


class GroundingFollowup(BaseModel):
    """RAG: disease_symptom 그래프 기반 후보 질병 + 미확인 증상(추가질문 후보)."""

    candidate_disease: str
    follow_up_symptoms: list[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


class Grounding(BaseModel):
    """플랫폼(apps/api)이 pgvector RAG로 만들어 AI에 주입하는 컨텍스트.

    docs/ai §3.2: Platform이 context를 먹이고 AI는 순수 LLM 함수. AI는 DB 미접근.
    AI 서버는 이 grounding을 프롬프트(정신과 EMR 주입)로 활용한다.
    """

    similar_cases: list[GroundingCase] = Field(default_factory=list)
    my_past: list[GroundingPast] = Field(default_factory=list)
    knowledge: list[GroundingKnowledge] = Field(default_factory=list)
    mentioned_symptoms: list[str] = Field(default_factory=list)
    follow_up: GroundingFollowup | None = None

    model_config = ConfigDict(extra="forbid")


class ChatRequest(BaseModel):
    session_id: UUID
    messages: list[ChatMessage] = Field(
        default_factory=list,
        description="Conversation so far, oldest-first (decrypted by platform).",
    )
    grounding: Grounding | None = Field(
        default=None,
        description="RAG 컨텍스트 (apps/api가 pgvector로 검색해 주입). None이면 미사용.",
    )

    model_config = ConfigDict(extra="forbid")


class ChatResponse(BaseModel):
    reply: str = Field(min_length=1)
    model_used: str = Field(description="e.g. 'claude-opus-4-8', 'solar-pro-3'")
    progress: ChatProgress
    latency_ms: int = Field(ge=0, description="Server-measured wall-clock")

    model_config = ConfigDict(extra="forbid")
