"""POST /ai/chat/respond — Dialogue endpoint with safety gate."""

from __future__ import annotations

import json
import logging
import time
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from src.adapters.base import ChatMessage, LLMAdapter
from src.agents.safety_classifier import SafetyClassifierAgent
from src.dependencies import get_model_router, get_prompt_loader
from src.prompts.loader import PromptLoader
from src.routing.model_router import ModelRouter
from src.schemas.common import RiskLevel
from src.schemas.dialogue import DialogueInput, DialogueLLMResponse, DialogueOutput
from src.schemas.safety import SafetyInput, SafetyOutput

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai/chat", tags=["chat"])

_DIALOGUE_AGENT_NAME = "dialogue"
_PROMPT_VERSION = "v1"

# Risk levels that block normal dialogue and trigger crisis protocol
_CRISIS_LEVELS = {RiskLevel.high, RiskLevel.critical}

_CRISIS_RESPONSE = (
    "지금 많이 힘드시군요. 당신의 이야기를 듣고 있습니다. "
    "혼자 감당하지 않으셔도 됩니다. "
    "지금 바로 전문 상담원과 이야기하실 수 있습니다. "
    "자살예방상담전화 1393, 정신건강위기상담전화 1577-0199로 연락해 주세요."
)


def _get_safety_agent(
    model_router: ModelRouter = Depends(get_model_router),
    prompt_loader: PromptLoader = Depends(get_prompt_loader),
) -> SafetyClassifierAgent:
    return SafetyClassifierAgent(model_router=model_router, prompt_loader=prompt_loader)


@router.post("/respond", response_model=DialogueOutput)
async def respond(
    body: DialogueInput,
    model_router: ModelRouter = Depends(get_model_router),
    prompt_loader: PromptLoader = Depends(get_prompt_loader),
    safety_agent: SafetyClassifierAgent = Depends(_get_safety_agent),
) -> DialogueOutput:
    """Process a user chat message: safety gate -> dialogue LLM -> response.

    If the safety gate detects high/critical risk, the normal dialogue is
    bypassed and a crisis protocol response is returned immediately.
    """
    start = time.perf_counter()

    if not body.request_id:
        body.request_id = str(uuid.uuid4())

    logger.info(
        "Chat respond request_id=%s session_id=%s",
        body.request_id,
        body.session_id,
    )

    # ── Step 1: Safety gate ──────────────────────────────────────────
    safety_input = SafetyInput(
        session_id=body.session_id,
        request_id=body.request_id,
        user_message=body.user_message,
        conversation_history=body.conversation_history,
    )

    try:
        safety_result: SafetyOutput = await safety_agent.run(safety_input)
    except Exception as exc:
        logger.error("Safety gate failed: %s", exc, exc_info=True)
        # Safety failure is non-negotiable — do not proceed without classification
        raise HTTPException(
            status_code=500, detail="Safety classification unavailable"
        ) from exc

    # Crisis path — bypass dialogue
    if safety_result.risk_level in _CRISIS_LEVELS:
        logger.warning(
            "Crisis detected (risk=%s) — bypassing dialogue",
            safety_result.risk_level,
        )
        latency_ms = (time.perf_counter() - start) * 1000
        return DialogueOutput(
            model_used=safety_result.model_used,
            prompt_version=_PROMPT_VERSION,
            latency_ms=latency_ms,
            reason_summary=f"Crisis protocol activated: {safety_result.risk_level}",
            assistant_response=_CRISIS_RESPONSE,
            slot_updates={},
            risk_level=safety_result.risk_level,
            requires_human_review=True,
            all_slots=dict(body.filled_slots),
        )

    # ── Step 2: Dialogue LLM ────────────────────────────────────────
    try:
        system_prompt = prompt_loader.load_system_prompt(_DIALOGUE_AGENT_NAME, _PROMPT_VERSION)
    except FileNotFoundError:
        logger.warning("Dialogue prompt not found, using minimal fallback")
        system_prompt = (
            "당신은 Neuro-Sync 정신건강 사전 문진 AI입니다. "
            "환자의 이야기를 경청하고, 100자 이내의 따뜻한 한국어로 응답합니다. "
            "JSON으로 응답하세요: {assistant_response, slot_updates, risk_level, requires_human_review, reason_summary}"
        )

    # Build context about filled slots
    slot_context = ""
    if body.filled_slots:
        filled = ", ".join(f"{k}={v}" for k, v in body.filled_slots.items())
        slot_context = f"\n\n[이미 수집된 슬롯: {filled}]"

    messages: list[ChatMessage] = [
        ChatMessage(role="system", content=system_prompt + slot_context),
    ]

    for turn in body.conversation_history[-8:]:
        messages.append(
            ChatMessage(role=turn.get("role", "user"), content=turn["content"])
        )

    messages.append(ChatMessage(role="user", content=body.user_message))

    selection = model_router.select_model(_DIALOGUE_AGENT_NAME, require_json=True)
    adapter = model_router.get_adapter(selection.adapter_name)
    assert isinstance(adapter, LLMAdapter)

    response_format: dict[str, Any] | None = None
    if selection.supports_json_schema or selection.supports_json_object:
        response_format = {"type": "json_object"}

    try:
        resp = await adapter.chat_timed(
            messages,
            model=selection.model_id,
            temperature=0.4,
            max_tokens=1024,
            response_format=response_format,
        )
        model_router.record_success(selection.adapter_name)
    except Exception as exc:
        logger.error("Dialogue LLM failed on %s: %s", selection.adapter_name, exc)
        model_router.record_failure(selection.adapter_name, exc)

        # Try fallback
        fallback = model_router.get_fallback(
            _DIALOGUE_AGENT_NAME, selection.adapter_name, str(exc)
        )
        if fallback is None:
            raise HTTPException(
                status_code=500, detail="Dialogue generation failed"
            ) from exc

        fb_adapter = model_router.get_adapter(fallback.adapter_name)
        assert isinstance(fb_adapter, LLMAdapter)
        fb_format: dict[str, Any] | None = None
        if fallback.supports_json_schema or fallback.supports_json_object:
            fb_format = {"type": "json_object"}

        resp = await fb_adapter.chat_timed(
            messages,
            model=fallback.model_id,
            temperature=0.4,
            max_tokens=1024,
            response_format=fb_format,
        )
        model_router.record_success(fallback.adapter_name)

    # ── Step 3: Parse dialogue response ──────────────────────────────
    try:
        data = json.loads(resp.content)
        llm_resp = DialogueLLMResponse.model_validate(data)
    except (json.JSONDecodeError, Exception) as parse_exc:
        logger.warning("Failed to parse dialogue response as JSON: %s", parse_exc)
        # Graceful degradation: use raw content as response
        llm_resp = DialogueLLMResponse(
            assistant_response=resp.content[:200],
            reason_summary="JSON parse failed — using raw response",
        )

    # Merge slots
    merged_slots = dict(body.filled_slots)
    merged_slots.update(llm_resp.slot_updates)

    latency_ms = (time.perf_counter() - start) * 1000

    return DialogueOutput(
        model_used=resp.model,
        prompt_version=_PROMPT_VERSION,
        latency_ms=latency_ms,
        reason_summary=llm_resp.reason_summary,
        assistant_response=llm_resp.assistant_response,
        slot_updates=llm_resp.slot_updates,
        risk_level=llm_resp.risk_level,
        requires_human_review=llm_resp.requires_human_review,
        all_slots=merged_slots,
    )
