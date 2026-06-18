"""Test: Generate a 사전 문진 Handoff Report using available LLM APIs.

This script:
1. Loads system prompts from docs/ai/prompts/
2. Simulates a multi-turn patient dialogue (synthetic data only)
3. Calls LLM API to generate a Handoff Report
4. Saves the result as docs/ai/eval/sample_handoff_report.md

Usage:
    cd /home/neuroai/users/dhkim/local_neurosync
    python scripts/test_handoff_report.py --vendor upstage
    python scripts/test_handoff_report.py --vendor exaone
    python scripts/test_handoff_report.py --vendor all
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# Vendor configs
# ---------------------------------------------------------------------------

VENDORS = {
    "upstage": {
        "api_key_env": "UPSTAGE_API_KEY",
        "base_url": "https://api.upstage.ai/v1",
        "model": "solar-pro3",
        "extra_body": {},
    },
    "exaone": {
        "api_key_env": "LG_K_EXAONE_API_KEY",
        "base_url": "https://api.friendli.ai/dedicated/v1",
        "model_env": "LG_K_EXAONE_ENDPOINT_ID",
        "extra_body": {
            "chat_template_kwargs": {"enable_thinking": False},
            "parse_reasoning": True,
            "include_reasoning": False,
        },
    },
}

# ---------------------------------------------------------------------------
# Synthetic patient conversation (합성 데이터 — 실제 환자 데이터 아님)
# ---------------------------------------------------------------------------

SYNTHETIC_PATIENT_DIALOGUE = [
    {
        "id": "msg_001",
        "role": "user",
        "content": "요즘 잠을 잘 못 자요. 한 2주 정도 된 것 같아요.",
    },
    {
        "id": "msg_002",
        "role": "assistant",
        "content": "잠을 잘 못 주무시는군요. 2주 정도 되셨다니 힘드셨겠습니다. 잠들기가 어려우신 건가요, 아니면 중간에 자주 깨시나요?",
    },
    {
        "id": "msg_003",
        "role": "user",
        "content": "잠들기가 어려워요. 누우면 이런저런 생각이 많아져서... 새벽 2~3시까지 못 자는 날이 많아요.",
    },
    {
        "id": "msg_004",
        "role": "assistant",
        "content": "새벽까지 잠을 이루지 못하시면 많이 피곤하시겠어요. 혹시 낮 동안 일이나 공부에 집중하기 어려우신 적이 있으신가요?",
    },
    {
        "id": "msg_005",
        "role": "user",
        "content": "네, 회사에서 집중이 잘 안 돼요. 실수도 늘었고, 상사한테 지적도 받았어요. 그래서 더 스트레스받고...",
    },
    {
        "id": "msg_006",
        "role": "assistant",
        "content": "업무에서 어려움이 생기시면 스트레스가 더 쌓이실 수 있겠네요. 식욕은 어떠세요? 평소와 비교해서 변화가 있으신가요?",
    },
    {
        "id": "msg_007",
        "role": "user",
        "content": "밥맛이 없어서 하루에 한 끼 정도만 먹어요. 살도 좀 빠진 것 같아요.",
    },
    {
        "id": "msg_008",
        "role": "assistant",
        "content": "식욕이 많이 줄으셨군요. 혹시 평소에 즐기시던 활동이나 취미에 대한 흥미도 줄어드셨나요?",
    },
    {
        "id": "msg_009",
        "role": "user",
        "content": "네, 원래 주말마다 친구들 만나고 운동도 했는데 요즘은 그냥 집에만 있어요. 아무것도 하기 싫어요.",
    },
    {
        "id": "msg_010",
        "role": "assistant",
        "content": "활동이 많이 줄어드셨네요. 혹시 이런 증상이 시작된 특별한 계기가 있으셨나요?",
    },
    {
        "id": "msg_011",
        "role": "user",
        "content": "한 달 전쯤에 오래 사귀던 여자친구와 헤어졌어요. 그때부터 좀 무너진 것 같아요.",
    },
    {
        "id": "msg_012",
        "role": "assistant",
        "content": "소중한 관계가 끝나면 마음이 많이 힘드실 수 있어요. 현재 복용하고 계신 약이 있으신가요?",
    },
    {
        "id": "msg_013",
        "role": "user",
        "content": "약은 따로 먹는 건 없어요. 정신과 진료는 이번이 처음이에요.",
    },
    {
        "id": "msg_014",
        "role": "assistant",
        "content": "알겠습니다. 불안하거나 가슴이 두근거리는 느낌이 드실 때가 있으신가요?",
    },
    {
        "id": "msg_015",
        "role": "user",
        "content": "가끔 회사에서 갑자기 가슴이 답답하고 숨이 막히는 느낌이 들 때가 있어요. 일주일에 2~3번 정도요.",
    },
]

# PHQ-9 / GAD-7 합성 점수
SYNTHETIC_PHQ9 = {"score": 16, "severity": "moderately_severe", "item_scores": [2, 2, 2, 2, 2, 1, 1, 1, 1]}
SYNTHETIC_GAD7 = {"score": 12, "severity": "moderate", "item_scores": [2, 2, 2, 1, 2, 1, 2]}

# Safety events (none in this case)
SYNTHETIC_RISK_EVENTS: list = []


def load_prompt(prompt_path: str) -> str:
    """Load a system prompt .md file."""
    path = Path(prompt_path)
    if not path.exists():
        print(f"ERROR: Prompt file not found: {path}")
        sys.exit(1)
    return path.read_text(encoding="utf-8")


def build_handoff_user_prompt(
    messages: list[dict],
    phq9: dict,
    gad7: dict,
    risk_events: list,
) -> str:
    """Build the user prompt for the Handoff Generator with all evidence."""

    conversation_block = "\n".join(
        f"[{m['id']}] {m['role']}: {m['content']}" for m in messages
    )

    return f"""아래 정보를 바탕으로 의료진용 Handoff Report를 생성하세요.

## 환자 대화 기록 (합성 데이터)

{conversation_block}

## PHQ-9 결과
- 총점: {phq9['score']}점 / 27점
- 심각도: {phq9['severity']}
- 문항별 점수: {phq9['item_scores']}

## GAD-7 결과
- 총점: {gad7['score']}점 / 21점
- 심각도: {gad7['severity']}
- 문항별 점수: {gad7['item_scores']}

## 위험 이벤트
{json.dumps(risk_events, ensure_ascii=False) if risk_events else "없음"}

## 업로드 문서
없음

## 이전 세션 기록
해당 없음 (초진)

---

위 정보만을 근거로 Handoff Report를 작성하세요.
- 모든 핵심 claim에 근거 ID(예: [ev_msg_001], [ev_scale_001])를 반드시 첨부하세요.
- 환자 발화에 없는 의학적 사실을 생성하지 마세요.
- 진단명을 단정하지 마세요.
"""


def call_llm(vendor: str, system_prompt: str, user_prompt: str) -> tuple[str, dict]:
    """Call LLM API and return (content, metadata)."""
    try:
        from openai import OpenAI
    except ImportError:
        print("ERROR: openai package not installed. Run: pip install openai")
        sys.exit(1)

    config = VENDORS[vendor]

    if vendor == "upstage":
        api_key = os.environ.get("UPSTAGE_API_KEY", "")
        model = config["model"]
    elif vendor == "exaone":
        api_key = os.environ.get("LG_K_EXAONE_API_KEY", "")
        model = os.environ.get("LG_K_EXAONE_ENDPOINT_ID", "")
    else:
        raise ValueError(f"Unknown vendor: {vendor}")

    if not api_key:
        print(f"SKIP: {vendor} — API key not set")
        return "", {}

    client = OpenAI(api_key=api_key, base_url=config["base_url"])

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    kwargs: dict = {
        "model": model,
        "messages": messages,
        "max_tokens": 4096,
        "temperature": 0.2,
    }

    if config.get("extra_body"):
        kwargs["extra_body"] = config["extra_body"]

    start = time.time()
    try:
        resp = client.chat.completions.create(**kwargs)
    except Exception as e:
        print(f"ERROR: {vendor} API call failed: {e}")
        return "", {"error": str(e)}

    latency_ms = int((time.time() - start) * 1000)

    content = resp.choices[0].message.content or ""
    metadata = {
        "vendor": vendor,
        "model": model,
        "latency_ms": latency_ms,
        "finish_reason": resp.choices[0].finish_reason,
        "prompt_tokens": resp.usage.prompt_tokens if resp.usage else 0,
        "completion_tokens": resp.usage.completion_tokens if resp.usage else 0,
        "total_tokens": resp.usage.total_tokens if resp.usage else 0,
    }

    return content, metadata


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate 사전 문진 Handoff Report")
    parser.add_argument(
        "--vendor",
        choices=["upstage", "exaone", "all"],
        default="upstage",
        help="Which LLM vendor to use",
    )
    args = parser.parse_args()

    # Resolve paths from project root
    project_root = Path(__file__).resolve().parent.parent
    os.chdir(project_root)

    # Load system prompt
    system_prompt = load_prompt("docs/ai/prompts/handoff_generator/v1.system.md")

    # Build user prompt
    user_prompt = build_handoff_user_prompt(
        messages=SYNTHETIC_PATIENT_DIALOGUE,
        phq9=SYNTHETIC_PHQ9,
        gad7=SYNTHETIC_GAD7,
        risk_events=SYNTHETIC_RISK_EVENTS,
    )

    vendors_to_test = ["upstage", "exaone"] if args.vendor == "all" else [args.vendor]
    output_dir = project_root / "docs" / "ai" / "eval"
    output_dir.mkdir(parents=True, exist_ok=True)

    for vendor in vendors_to_test:
        print(f"\n{'='*60}")
        print(f"Testing: {vendor}")
        print(f"{'='*60}")

        content, metadata = call_llm(vendor, system_prompt, user_prompt)

        if not content:
            print(f"No output from {vendor}")
            continue

        # Print metadata
        print(f"Latency: {metadata.get('latency_ms', '?')}ms")
        print(f"Tokens: {metadata.get('total_tokens', '?')}")
        print(f"Finish: {metadata.get('finish_reason', '?')}")

        # Save report
        output_path = output_dir / f"sample_handoff_report_{vendor}.md"
        report_header = f"""---
vendor: {vendor}
model: {metadata.get('model', '')}
latency_ms: {metadata.get('latency_ms', 0)}
tokens: {metadata.get('total_tokens', 0)}
finish_reason: {metadata.get('finish_reason', '')}
generated_at: {time.strftime('%Y-%m-%dT%H:%M:%S+09:00')}
data_type: synthetic
---

"""
        output_path.write_text(report_header + content, encoding="utf-8")
        print(f"Saved: {output_path}")

        # Also save user prompt for reproducibility
        prompt_path = output_dir / f"sample_handoff_prompt_{vendor}.md"
        prompt_path.write_text(
            f"# System Prompt\n\n{system_prompt}\n\n---\n\n# User Prompt\n\n{user_prompt}",
            encoding="utf-8",
        )
        print(f"Saved prompt: {prompt_path}")


if __name__ == "__main__":
    main()
