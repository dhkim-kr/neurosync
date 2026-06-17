"""POST /ai/safety/classify — Safety classification endpoint."""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException

from src.agents.safety_classifier import SafetyClassifierAgent
from src.dependencies import get_model_router, get_prompt_loader
from src.prompts.loader import PromptLoader
from src.routing.model_router import ModelRouter
from src.schemas.safety import SafetyInput, SafetyOutput

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai/safety", tags=["safety"])


def _get_safety_agent(
    model_router: ModelRouter = Depends(get_model_router),
    prompt_loader: PromptLoader = Depends(get_prompt_loader),
) -> SafetyClassifierAgent:
    return SafetyClassifierAgent(model_router=model_router, prompt_loader=prompt_loader)


@router.post("/classify", response_model=SafetyOutput)
async def classify(
    body: SafetyInput,
    agent: SafetyClassifierAgent = Depends(_get_safety_agent),
) -> SafetyOutput:
    """Classify user message for safety risks (dual rule + LLM path)."""
    if not body.request_id:
        body.request_id = str(uuid.uuid4())

    logger.info(
        "Safety classify request_id=%s session_id=%s",
        body.request_id,
        body.session_id,
    )

    try:
        result = await agent.run(body)
    except Exception as exc:
        logger.error("Safety classification failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Safety classification failed") from exc

    logger.info(
        "Safety classify result: risk=%s rule=%s llm=%s latency=%.0fms",
        result.risk_level,
        result.rule_risk_level,
        result.llm_risk_level,
        result.latency_ms,
    )
    return result
