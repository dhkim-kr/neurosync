"""Schemas for the Handoff Generator agent."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from src.agents.base import AgentInput, AgentOutput
from src.schemas.common import EvidencePacket, RiskLevel


class SlotData(BaseModel):
    """Collected clinical slot data from the dialogue session.

    Fields map to ALL_SLOT_KEYS in clinical_slot.py.
    """

    chief_complaint: Optional[str] = None
    history_of_present_illness: Optional[str] = None
    onset: Optional[str] = None
    duration: Optional[str] = None
    triggers: Optional[str] = None
    sleep: Optional[str] = None
    appetite: Optional[str] = None
    mood: Optional[str] = None
    anxiety: Optional[str] = None
    concentration: Optional[str] = None
    energy: Optional[str] = None
    functional_impairment: Optional[str] = None
    medication: Optional[str] = None
    past_psychiatric_history: Optional[str] = None
    risk_factors: Optional[str] = None
    psychosocial_context: Optional[str] = None
    substance_use: Optional[str] = None


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
    report_json: Optional[dict] = Field(
        default=None,
        description="Structured JSON parsed from the 12-section report",
    )
    report_pdf_base64: Optional[str] = Field(
        default=None,
        description="Base64-encoded PDF of the report (None if unavailable)",
    )
    trend_plot_base64: Optional[str] = Field(
        default=None,
        description="Base64-encoded PNG of longitudinal trend line chart",
    )
    evidence_packets: list[EvidencePacket] = Field(default_factory=list)
    missing_slots: list[str] = Field(
        default_factory=list,
        description="Slot names that were not collected",
    )
    risk_level: RiskLevel = Field(default=RiskLevel.none)
    requires_human_review: bool = Field(default=False)
