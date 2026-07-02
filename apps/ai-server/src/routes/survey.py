"""POST /ai/survey/score — Deterministic survey scoring (no LLM)."""

from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, HTTPException

from src.schemas.survey import SurveyScoreInput, SurveyScoreOutput
from src.scoring.survey_scorer import score_survey

router = APIRouter(prefix="/ai/survey", tags=["survey"])


@router.post("/score", response_model=SurveyScoreOutput)
async def score(body: SurveyScoreInput) -> SurveyScoreOutput:
    """Score a clinical survey scale using deterministic rules."""
    try:
        result = score_survey(body.scale_name, body.responses, patient_sex=body.patient_sex)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return SurveyScoreOutput(**asdict(result))
