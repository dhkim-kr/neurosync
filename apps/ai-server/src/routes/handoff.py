"""POST /ai/handoff/generate — Handoff report generation endpoint."""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException

from src.agents.evidence_verifier import (
    EvidenceVerifierAgent,
    EvidenceVerifierInput,
    VerifierAction,
)
from src.agents.handoff_generator import HandoffGeneratorAgent
from src.dependencies import get_model_router, get_prompt_loader
from src.prompts.loader import PromptLoader
from src.routing.model_router import ModelRouter
from src.schemas.handoff import HandoffInput, HandoffOutput

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai/handoff", tags=["handoff"])

_MAX_REGENERATE_ATTEMPTS = 2


def _get_handoff_agent(
    model_router: ModelRouter = Depends(get_model_router),
    prompt_loader: PromptLoader = Depends(get_prompt_loader),
) -> HandoffGeneratorAgent:
    return HandoffGeneratorAgent(model_router=model_router, prompt_loader=prompt_loader)


def _get_verifier_agent() -> EvidenceVerifierAgent:
    return EvidenceVerifierAgent()


@router.post("/generate", response_model=HandoffOutput)
async def generate(
    body: HandoffInput,
    handoff_agent: HandoffGeneratorAgent = Depends(_get_handoff_agent),
    verifier: EvidenceVerifierAgent = Depends(_get_verifier_agent),
) -> HandoffOutput:
    """Generate a handoff report, then verify evidence integrity.

    If the verifier says ``regenerate``, the report is regenerated up to
    ``_MAX_REGENERATE_ATTEMPTS`` times. If it says ``reject``, a 422 is returned.
    """
    if not body.request_id:
        body.request_id = str(uuid.uuid4())

    logger.info(
        "Handoff generate request_id=%s session_id=%s",
        body.request_id,
        body.session_id,
    )

    last_result: HandoffOutput | None = None

    for attempt in range(1 + _MAX_REGENERATE_ATTEMPTS):
        try:
            result = await handoff_agent.run(body)
        except Exception as exc:
            logger.error("Handoff generation failed: %s", exc, exc_info=True)
            raise HTTPException(
                status_code=500, detail="Handoff report generation failed"
            ) from exc

        last_result = result

        # Verify
        verifier_input = EvidenceVerifierInput(
            session_id=body.session_id,
            request_id=body.request_id,
            report_markdown=result.report_markdown,
            evidence_packets=result.evidence_packets,
        )

        try:
            verification = await verifier.run(verifier_input)
        except Exception as exc:
            logger.warning("Evidence verification failed, returning unverified: %s", exc)
            break

        if verification.action == VerifierAction.passed:
            logger.info(
                "Handoff verified (attempt %d): latency=%.0fms",
                attempt + 1,
                result.latency_ms,
            )
            return result

        if verification.action == VerifierAction.reject:
            logger.warning(
                "Handoff REJECTED: %d issues — %s",
                len(verification.issues),
                [i.description for i in verification.issues],
            )
            raise HTTPException(
                status_code=422,
                detail={
                    "message": "Handoff report rejected by evidence verifier",
                    "issues": [i.model_dump() for i in verification.issues],
                },
            )

        # regenerate
        logger.info(
            "Handoff needs regeneration (attempt %d/%d): %d issues",
            attempt + 1,
            1 + _MAX_REGENERATE_ATTEMPTS,
            len(verification.issues),
        )

    # Exhausted regeneration attempts — return the last result with a warning
    if last_result:
        last_result.requires_human_review = True
        last_result.reason_summary += " [WARNING: verification issues remain after regeneration]"
        return last_result

    raise HTTPException(status_code=500, detail="Handoff generation failed unexpectedly")
