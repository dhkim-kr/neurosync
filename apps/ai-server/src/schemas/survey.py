"""Schemas for the survey scoring route."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SurveyScoreInput(BaseModel):
    """Input for deterministic survey scoring."""

    session_id: str = Field(default="", description="Optional session ID")
    scale_name: str = Field(..., description="PHQ-9, GAD-7, PHQ-4, WHO-5, or AUDIT-C")
    responses: list[int] = Field(..., description="Item responses")
    patient_sex: str = Field(default="unknown", description="male/female/unknown (for AUDIT-C)")


class SurveyScoreOutput(BaseModel):
    """Deterministic scoring result for a clinical survey scale."""

    scale_name: str
    total_score: int
    max_score: int
    severity: str
    critical_item_positive: bool = False
    critical_items: list[dict] = Field(default_factory=list)
    subscale_scores: dict[str, int] = Field(default_factory=dict)
    interpretation: str = ""
    recommended_action: str = ""
