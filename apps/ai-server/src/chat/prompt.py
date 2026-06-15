"""RAG grounding → 프롬프트 주입 (정신과 EMR 주입).

★ 입력 = `grounding: Grounding` — apps/api가 ChatRequest에 실어 보낸 RAG 결과.
   여기선 *받아서 프롬프트로 녹이기만* 한다 (검색·DB 없음).
   - grounding 정의(스키마): packages/shared-contracts/python/src/contracts/chat.py
   - grounding을 뭐가 채우나(참고만): apps/api/src/rag/retrieval.py
   - 이 함수를 부르는 곳: ../api/chat.py (chat_respond → build_prompt_messages)

신뢰도 차등(프롬프트 톤 — 여기 문구를 튜닝):
  - 남의 사례(similar_cases): 참고만, 복붙 금지.
  - 내 과거(my_past): 사실, 직접 반영.
  - 지식(knowledge): 사실 근거.
  - 추가질문(follow_up): 미확인 증상을 자연스럽게 물어볼 후보.
"""

from __future__ import annotations

from contracts.chat import ChatMessage, Grounding

SYSTEM_BASE = (
    "당신은 정신건강 사전 진료를 돕는 한국어 상담 AI입니다. 공감적이고 안전하게 대화하며, "
    "진단을 단정하지 말고 의료진 연계를 전제로 정보를 수집하세요. 자살·자해 위험 신호가 보이면 "
    "안전을 최우선으로 반응하세요."
)


def render_grounding(g: Grounding | None) -> str:
    """★ 입력 grounding(apps/api RAG 결과)이 프롬프트 텍스트가 되는 곳 — 여기 문구를 튜닝.

    grounding 4슬롯을 프롬프트 블록 텍스트로. 비어있으면 빈 문자열."""
    if g is None:
        return ""
    parts: list[str] = []

    if g.similar_cases:
        parts.append("## 유사 상담 사례 (참고용 — 그대로 인용하지 말 것)")
        for c in g.similar_cases:
            parts.append(f"- [{c.disease_class}] {c.situation[:200]}")

    if g.my_past:
        parts.append("## 이 환자의 과거 세션 (사실 — 연속성 있게 반영)")
        for p in g.my_past:
            tag = f"[{p.disease_class}] " if p.disease_class else ""
            parts.append(f"- {tag}{p.situation[:200]}")

    if g.knowledge:
        parts.append("## 정신과 지식 (근거)")
        for k in g.knowledge:
            parts.append(f"- Q: {k.question[:120]}  A: {k.answer[:120]}")

    if g.mentioned_symptoms:
        parts.append("## 환자가 언급한 증상: " + ", ".join(g.mentioned_symptoms))

    if g.follow_up is not None and g.follow_up.follow_up_symptoms:
        parts.append(
            f"## 감별 후보: {g.follow_up.candidate_disease} — "
            "다음 미확인 증상을 자연스럽게 한두 개 물어보세요: "
            + ", ".join(g.follow_up.follow_up_symptoms[:6])
        )

    return "\n".join(parts)


def build_system_prompt(g: Grounding | None) -> str:
    block = render_grounding(g)
    if not block:
        return SYSTEM_BASE
    return f"{SYSTEM_BASE}\n\n# 참고 컨텍스트 (RAG — 내부용, 환자에게 노출 금지)\n{block}"


def build_prompt_messages(
    messages: list[ChatMessage], g: Grounding | None
) -> list[dict[str, str]]:
    """LLM 호출용 messages 배열 (system + 대화)."""
    out = [{"role": "system", "content": build_system_prompt(g)}]
    for m in messages:
        role = "assistant" if m.role == "ai" else m.role
        out.append({"role": role, "content": m.content})
    return out
