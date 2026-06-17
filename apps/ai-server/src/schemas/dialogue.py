"""Schemas for the Dialogue agent."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from src.agents.base import AgentInput, AgentOutput
from src.schemas.common import RiskLevel


class DialogueInput(AgentInput):
    """Input to the dialogue agent."""

    user_message: str = Field(..., description="Current user message")
    conversation_history: list[dict[str, str]] = Field(
        default_factory=list,
        description="Previous turns [{role, content}, ...]",
    )
    filled_slots: dict[str, str] = Field(
        default_factory=dict,
        description="Already-collected slot values",
    )
    safety_result: Optional[dict[str, str]] = Field(
        default=None,
        description="Latest safety classification if available",
    )


class DialogueLLMResponse(BaseModel):
    """Expected JSON structure from the Dialogue LLM call."""

    assistant_response: str = Field(..., description="Patient-facing response text")
    slot_updates: dict[str, str] = Field(
        default_factory=dict,
        description="Newly extracted slot values from this turn",
    )
    risk_level: RiskLevel = Field(default=RiskLevel.none)
    requires_human_review: bool = Field(default=False)
    reason_summary: str = Field(default="")


class DialogueOutput(AgentOutput):
    """Output from the dialogue agent."""

    assistant_response: str = Field(..., description="Patient-facing response")
    slot_updates: dict[str, str] = Field(default_factory=dict)
    risk_level: RiskLevel = Field(default=RiskLevel.none)
    requires_human_review: bool = Field(default=False)
    all_slots: dict[str, str] = Field(
        default_factory=dict,
        description="Merged slot state after this turn",
    )
