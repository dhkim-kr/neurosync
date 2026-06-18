"""Schemas for the Handoff Generator agent."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from src.agents.base import AgentInput, AgentOutput
from src.schemas.common import EvidencePacket, RiskLevel


class SlotData(BaseModel):
    """Collected clinical slot data from the dialogue session."""

    chief_complaint: Optional[str] = None
    onset: Optional[str] = None
    duration: Optional[str] = None
    triggers: Optional[str] = None
    sleep: Optional[str] = None
    appetite: Optional[str] = None
    mood: Optional[str] = None
    anxiety: Optional[str] = None
    concentration: Optional[str] = None
    functional_impairment: Optional[str] = None
    medication: Optional[str] = None
    past_psychiatric_history: Optional[str] = None
    risk_factors: Optional[str] = None


class ScaleScore(BaseModel):
    """Standardized questionnaire score."""

    scale_name: str = Field(..., description="e.g. PHQ-9, GAD-7")
    total_score: int
    severity: str = Field(default="", description="e.g. mild, moderate, severe")


class HandoffInput(AgentInput):
    """Input to the handoff generator."""

    slots: SlotData = Field(default_factory=SlotData)
    conversation_history: list[dict[str, str]] = Field(default_factory=list)
    scale_scores: list[ScaleScore] = Field(default_factory=list)
    risk_events: list[dict[str, str]] = Field(
        default_factory=list,
        description="Safety events during the session",
    )
    ocr_documents: list[dict[str, str]] = Field(
        default_factory=list,
        description="OCR-parsed document blocks",
    )
    prior_handoff: Optional[str] = Field(
        default=None,
        description="Previous handoff report markdown (for longitudinal delta)",
    )
    is_first_visit: bool = Field(default=True)


class HandoffOutput(AgentOutput):
    """Output from the handoff generator agent."""

    report_markdown: str = Field(
        ...,
        description="Full handoff report in Markdown format",
    )
    evidence_packets: list[EvidencePacket] = Field(default_factory=list)
    missing_slots: list[str] = Field(
        default_factory=list,
        description="Slot names that were not collected",
    )
    risk_level: RiskLevel = Field(default=RiskLevel.none)
    requires_human_review: bool = Field(default=False)
