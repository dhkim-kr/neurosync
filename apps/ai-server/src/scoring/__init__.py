"""Rule-based survey scoring — no LLM, pure computation."""

from src.scoring.survey_scorer import ScoreResult, score_survey

__all__ = ["ScoreResult", "score_survey"]
