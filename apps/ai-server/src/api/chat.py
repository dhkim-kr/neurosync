"""POST /ai/chat/respond — PRD §0.3 interface #1.

==================== 입력은 여기로 들어온다 ====================
apps/api 가 RAG까지 끝낸 뒤 ChatRequest 를 이 엔드포인트로 POST 한다.
  payload.messages   : 대화 (oldest-first, 복호화됨)
  payload.grounding  : ★ RAG 4슬롯 (apps/api/src/rag 가 채워서 보냄)
                       similar_cases / my_past / knowledge /
                       mentioned_symptoms / follow_up
  → ai-server는 grounding을 *받기만* 한다 (DB·검색 안 함).
  → 스키마: packages/shared-contracts/python/src/contracts/chat.py

==================== 오케스트레이션 담당이 할 일 ====================
  1. _call_llm()            ← ★ 진짜 LLM 연결 (지금 stub)
  2. chat/prompt.py         ← grounding → 프롬프트 문구 튜닝
  3. chat_respond 의 progress ← intake 진행도 계산 (지금 0 stub)
================================================================
"""

from __future__ import annotations

import time

from contracts.chat import ChatProgress, ChatRequest, ChatResponse
from fastapi import APIRouter, status

from src.chat.prompt import build_prompt_messages

router = APIRouter(prefix="/ai", tags=["ai"])


def _call_llm(prompt_messages: list[dict[str, str]]) -> tuple[str, str]:
    """★★ LLM 연결 지점 ★★  (reply, model_used) 반환.

    TODO(오케스트레이션): 여기에 실제 벤더 호출을 끼운다.
      - 입력 `prompt_messages`: OpenAI 형식 [{role, content}, ...]. system에 grounding 주입됨.
      - 벤더: Claude / Solar Pro 3 / A.X K1 / Mi:dm / K-EXAONE (docs/ai §5 결정 후).
    지금은 grounding이 프롬프트에 들어갔음을 확인하는 stub.
    """
    system = next((m["content"] for m in prompt_messages if m["role"] == "system"), "")
    has_rag = "참고 컨텍스트 (RAG" in system
    return (
        "[LLM 미연결 stub] 대화를 이어갑니다. "
        + ("RAG grounding이 프롬프트에 주입되었습니다." if has_rag else "RAG grounding 없음."),
        "stub-no-llm",
    )


@router.post(
    "/chat/respond",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate one assistant turn (RAG-grounded prompt)",
)
async def chat_respond(payload: ChatRequest) -> ChatResponse:
    # ★ 입력 진입점: payload = ChatRequest (apps/api가 RAG 끝내고 보냄).
    #   payload.messages = 대화,  payload.grounding = RAG 4슬롯.
    started = time.monotonic()

    # grounding → 프롬프트(system에 정신과 EMR 주입). 문구는 chat/prompt.py 에서 튜닝.
    prompt_messages = build_prompt_messages(payload.messages, payload.grounding)

    # ★ 여기서 실제 LLM 호출 (지금 stub — _call_llm 안을 채우면 됨).
    reply, model_used = _call_llm(prompt_messages)

    return ChatResponse(
        reply=reply,
        model_used=model_used,
        # TODO(오케스트레이션): intake 13항목 수집도 계산 (지금 0 stub).
        progress=ChatProgress(collected_items=[], total_items=13, ratio=0.0),
        latency_ms=int((time.monotonic() - started) * 1000),
    )
