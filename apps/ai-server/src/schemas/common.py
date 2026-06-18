"""Shared schema primitives used across all agents."""

from __future__ import annotations

from enum import StrEnum
from typing import Optional

from pydantic import BaseModel, Field


class RiskLevel(StrEnum):
    """Risk severity tiers — used by safety classifier and downstream gates."""

    none = "none"
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class EvidenceSource(StrEnum):
    """Allowed evidence types for clinical claims."""

    message = "message"
    scale = "scale"
    document_block = "document_block"
    risk_event = "risk_event"
    prior_handoff = "prior_handoff"


class EvidencePacket(BaseModel):
    """Single evidence citation linking a claim to its source."""

    evidence_id: str = Field(..., description="e.g. ev_msg_001")
    source_type: EvidenceSource
    source_ref: str = Field(..., description="Human-readable source reference")
    content_summary: str = Field(..., description="Short summary of the evidence")


class ModelSelection(BaseModel):
    """Result of model routing — tells the caller which adapter/model to use."""

    adapter_name: str = Field(..., description="Registered adapter key, e.g. 'solar-pro3'")
    model_id: str = Field(..., description="Model identifier to pass to the API")
    tier: str = Field(default="primary", description="primary | secondary | fallback")
    supports_json_schema: bool = Field(
        default=False,
        description="Whether the adapter natively supports JSON schema response_format",
    )
    supports_json_object: bool = Field(
        default=False,
        description="Whether the adapter supports {type: json_object} response_format",
    )
    max_tokens: Optional[int] = Field(default=None, description="Override max tokens if needed")
