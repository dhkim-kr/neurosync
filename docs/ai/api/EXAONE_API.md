# Friendli Dedicated EXAONE API 기능 정리

기준 문서:

- Friendli Dedicated OpenAPI overview: https://friendli.ai/docs/openapi/dedicated/overview
- Dedicated Chat Completions: https://friendli.ai/docs/openapi/dedicated/inference/chat-completions
- EXAONE 4.0 tutorial: https://friendli.ai/docs/guides/tutorials/getting-started-with-exaone-4.0
- Dedicated QuickStart: https://friendli.ai/docs/guides/dedicated-endpoints/quickstart
- Reasoning guide: https://friendli.ai/docs/guides/reasoning
- OpenAI compatibility: https://friendli.ai/docs/guides/openai-compatibility
- Documentation index: https://friendli.ai/docs/llms.txt

검증 반영일: 2026-06-09

## 1. 한 줄 결론

EXAONE은 FriendliAI의 `Dedicated Endpoint`에 배포된 전용 LLM 엔드포인트로 호출한다. 호출 방식은 OpenAI 호환 `chat/completions` 구조이고, `model` 값에는 모델 이름이 아니라 Friendli Dedicated Endpoint ID를 넣는다.

우리 프로젝트 기준 핵심 호출 주소는 다음이다.

```text
Base URL: https://api.friendli.ai/dedicated/v1
Chat endpoint: POST https://api.friendli.ai/dedicated/v1/chat/completions
Auth: Authorization: Bearer $LG_K_EXAONE_API_KEY
Model field: $LG_K_EXAONE_ENDPOINT_ID
```

## 2. 프로젝트 환경 변수

`.env`에는 실제 값이 들어가고, 문서/코드 예제에는 아래처럼 변수명만 쓴다.

```env
LG_K_EXAONE_API_KEY=YOUR_LG_K_EXAONE_API_KEY
LG_K_EXAONE_ENDPOINT_ID=YOUR_LG_K_EXAONE_ENDPOINT_ID
```


# API KEY
#######################################
LG_K_EXAONE_BASE_MODEL=LGAI-EXAONE/EXAONE-4.0.1-32B
LG_K_EXAONE_API_KEY=flp_wPJGi0ECi2A3tjZxtYPqdbRW3HIUqi7E0BnGbM4vMkwf6
LG_K_EXAONE_ENDPOINT_ID=depmkuykpfon9lg
#######################################



## 3. EXAONE Dedicated Endpoint가 하는 일

EXAONE 4.0 Dedicated Endpoint는 다음 목적에 맞는다.

- 한국어/영어 기반 대화형 응답 생성
- 추론이 필요한 질의응답, 분석, 계획, 에이전트 작업
- 엔터프라이즈 자동화와 연구용 텍스트 생성
- 고정된 전용 GPU 리소스로 안정적인 고처리량 서비스 운영
- Playground에서 파라미터를 조정하며 빠르게 테스트
- 애플리케이션 레이어에서 챗봇, RAG, 멀티에이전트 오케스트레이션, 업무 자동화와 연결 가능

Friendli Dedicated Endpoint는 공유 서버리스 모델 API와 다르게 사용자가 배포한 전용 엔드포인트를 대상으로 한다. 따라서 비용, GPU 타입, replica, autoscaling, endpoint lifecycle을 직접 관리할 수 있다.

## 4. 가장 중요한 API: Chat Completions

### 4.1 기본 요청

```bash
curl -X POST https://api.friendli.ai/dedicated/v1/chat/completions \
  -H "Authorization: Bearer $LG_K_EXAONE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "'"$LG_K_EXAONE_ENDPOINT_ID"'",
    "messages": [
      {
        "role": "system",
        "content": "너는 한국어로 간결하게 답하는 AI assistant다."
      },
      {
        "role": "user",
        "content": "안녕. 한 문장으로 답해줘."
      }
    ],
    "max_tokens": 256,
    "temperature": 0.2,
    "stream": false
  }'
```

응답은 OpenAI Chat Completions와 유사하다.

```json
{
  "id": "chatcmpl-...",
  "model": "(endpoint-id)",
  "object": "chat.completion",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "..."
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 9,
    "completion_tokens": 11,
    "total_tokens": 20
  },
  "created": 1735722153
}
```

### 4.2 필수 필드

| 필드 | 의미 |
| --- | --- |
| `model` | Dedicated Endpoint ID. LoRA adapter를 붙이면 `ENDPOINT_ID:ADAPTER_ROUTE` 형태도 가능 |
| `messages` | 대화 메시지 배열. `system`, `user`, `assistant` 역할을 넣어 멀티턴 대화 구성 |

### 4.3 주요 선택 필드

| 필드 | 기능 |
| --- | --- |
| `max_tokens` | 최대 생성 토큰 수. `finish_reason=length`가 나오면 늘려야 함 |
| `temperature` | 낮을수록 결정적, 높을수록 다양함 |
| `top_p` | nucleus sampling 범위 |
| `top_k` | 상위 k개 토큰 제한 |
| `frequency_penalty` | 반복 표현 억제 |
| `presence_penalty` | 이미 나온 주제/토큰 재등장 억제 |
| `repetition_penalty` | 반복 생성 억제 |
| `stop` | 지정 문자열이 나오면 생성 중단 |
| `seed` | 재현성 제어 |
| `n` | 같은 요청에서 여러 후보 생성 |
| `stream` | `true`면 SSE 스트리밍 응답 |
| `stream_options` | 스트리밍 옵션. `stream=true`일 때만 사용 |
| `logprobs`, `top_logprobs` | 토큰 확률 정보 반환 |
| `response_format` | JSON mode / structured output 강제 |
| `tools`, `tool_choice`, `parallel_tool_calls` | OpenAI식 function/tool calling |
| `chat_template_kwargs` | 모델 chat template에 전달할 추가 인자. EXAONE reasoning 제어에 중요 |
| `parse_reasoning` | reasoning을 `reasoning_content`로 분리 |
| `include_reasoning` | `parse_reasoning=true`일 때 reasoning 내용을 응답에 포함할지 제어 |
| `reasoning_effort` | reasoning 모델의 추론 강도. 모델/엔드포인트 지원 여부에 따라 다름 |
| `reasoning_budget` | reasoning 토큰 예산. 모델/엔드포인트 지원 여부에 따라 다름 |

## 5. EXAONE reasoning 제어

EXAONE 4.0 문서는 `enable_thinking`을 요청 단위로 켜고 끄는 방식을 설명한다.

### 5.1 기본값

EXAONE 4.0은 `enable_thinking`을 지정하지 않으면 기본적으로 reasoning을 사용하지 않는다고 문서에 설명되어 있다.

### 5.2 reasoning을 켜는 경우

복잡한 분석, 계획, 장문 문제 해결처럼 품질이 더 중요한 요청에 사용한다.

```json
{
  "model": "$LG_K_EXAONE_ENDPOINT_ID",
  "messages": [
    {"role": "user", "content": "복잡한 업무 자동화 플로우를 설계해줘."}
  ],
  "chat_template_kwargs": {
    "enable_thinking": true
  },
  "temperature": 1.0,
  "top_p": 1.0,
  "parse_reasoning": true,
  "include_reasoning": false
}
```

문서상 reasoning을 켤 때는 `temperature=1.0`, `top_p=1.0`이 권장된다. 다만 실제 서비스에서 reasoning 내용을 사용자에게 보여줄 필요가 없으면 `include_reasoning=false`를 둔다.

### 5.3 reasoning을 끄는 경우

짧은 답변, 분류, 추출, deterministic 출력이 필요한 경우에 적합하다.

```json
{
  "model": "$LG_K_EXAONE_ENDPOINT_ID",
  "messages": [
    {"role": "user", "content": "이 문장을 긍정/부정/중립으로 분류해줘."}
  ],
  "chat_template_kwargs": {
    "enable_thinking": false
  },
  "temperature": 0,
  "parse_reasoning": true,
  "include_reasoning": false
}
```

우리 테스트에서는 reasoning 관련 설정에 따라 빈 `content`, `finish_reason=length`, 또는 reasoning 텍스트 노출이 생길 수 있었다. 그래서 EXAONE 호출에서는 아래 조합을 우선 권장한다.

```json
{
  "chat_template_kwargs": {
    "enable_thinking": false
  },
  "temperature": 0,
  "parse_reasoning": true,
  "include_reasoning": false,
  "max_tokens": 512
}
```

복잡한 답변 품질이 필요할 때만 `enable_thinking=true`로 바꾸고 `max_tokens`를 충분히 크게 잡는다.

## 6. Streaming

`stream=true`를 설정하면 `text/event-stream` 형식으로 토큰이 순차 전송된다.

```bash
curl -X POST https://api.friendli.ai/dedicated/v1/chat/completions \
  -H "Authorization: Bearer $LG_K_EXAONE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "'"$LG_K_EXAONE_ENDPOINT_ID"'",
    "messages": [
      {"role": "user", "content": "짧게 자기소개해줘."}
    ],
    "stream": true
  }'
```

스트리밍 응답은 `data: {...}` chunk들이 오고 마지막에 `data: [DONE]`이 온다. 챗봇 UI에서는 이 방식이 사용자 체감 속도에 유리하다.

## 7. OpenAI SDK 호환 사용

Friendli Dedicated Endpoint는 OpenAI Python/Node SDK로도 호출 가능하다. 핵심은 `base_url`만 Friendli Dedicated URL로 바꾸는 것이다.

```python
import os
from openai import OpenAI

client = OpenAI(
    api_key=os.getenv("LG_K_EXAONE_API_KEY"),
    base_url="https://api.friendli.ai/dedicated/v1",
)

completion = client.chat.completions.create(
    model=os.getenv("LG_K_EXAONE_ENDPOINT_ID"),
    messages=[
        {"role": "system", "content": "너는 한국어로 간결하게 답한다."},
        {"role": "user", "content": "Neuro-Sync를 한 문장으로 설명해줘."},
    ],
    max_tokens=256,
    temperature=0.2,
    extra_body={
        "chat_template_kwargs": {"enable_thinking": False},
        "parse_reasoning": True,
        "include_reasoning": False,
    },
)

print(completion.choices[0].message.content)
```

OpenAI SDK에서 Friendli 전용 필드를 넣을 때는 `extra_body`를 사용한다.

## 8. Function Calling / Tool Calling

Dedicated Chat Completions 스키마에는 다음 tool 관련 필드가 있다.

- `tools`: 모델이 호출할 수 있는 함수 목록
- `tool_choice`: `none`, `auto`, `required`, 또는 특정 함수 지정
- `parallel_tool_calls`: 병렬 function calling 허용 여부

주의할 점:

- `tools`를 지정하면 `response_format`, `min_tokens`는 지원되지 않는다.
- 실제 tool calling 품질과 지원 범위는 배포된 EXAONE 모델, chat template, endpoint 설정에 좌우된다.
- Tool calling은 모델이 함수를 직접 실행하는 것이 아니라 호출 의도를 JSON 형태로 반환하는 구조다. 실제 함수 실행, 결과 주입, 후속 응답 요청은 애플리케이션 오케스트레이터가 해야 한다.

## 9. Structured Output / JSON Mode

`response_format`으로 출력 형식을 강제할 수 있다. 문서상 중요한 제약은 다음이다.

- `response_format`을 쓰면 `tools`, `min_tokens`와 함께 사용할 수 없다.
- 시스템 프롬프트나 유저 메시지에도 원하는 JSON 형식을 명시해야 한다.
- `max_tokens`가 부족하면 JSON이 잘릴 수 있고, 이때 `finish_reason=length`를 확인해야 한다.

예시:

```json
{
  "model": "$LG_K_EXAONE_ENDPOINT_ID",
  "messages": [
    {
      "role": "system",
      "content": "너는 JSON만 출력하는 API다. 다른 문장은 출력하지 마라."
    },
    {
      "role": "user",
      "content": "문장 감정을 positive, neutral, negative 중 하나로 분류해라: 오늘 진료가 빨라서 좋았다."
    }
  ],
  "response_format": {
    "type": "json_object"
  },
  "temperature": 0,
  "max_tokens": 128
}
```

## 10. Chat Render

Dedicated inference 목록에는 `Chat render`가 있다. 이 기능은 messages가 실제 모델 prompt/template으로 어떻게 렌더링되는지 미리 보는 용도다.

활용처:

- system/user/assistant 메시지가 최종 prompt에 어떻게 들어가는지 확인
- EXAONE의 chat template이 `enable_thinking`을 어떻게 반영하는지 디버깅
- 토큰 수와 프롬프트 구조 검증
- tool/function call 프롬프트가 모델에 어떻게 전달되는지 확인

## 11. Tokenization / Detokenization

Dedicated inference 목록에는 tokenization과 detokenization도 있다.

- `Tokenization`: 텍스트를 토큰 ID로 변환
- `Detokenization`: 토큰 ID를 텍스트로 복원

활용처:

- context window 초과 전 사전 토큰 수 계산
- chunking/RAG에서 문서 분할 길이 조절
- `max_tokens`와 입력 길이 조합 검증
- EXAONE 응답이 `finish_reason=length`로 잘릴 때 원인 분석

## 12. Embeddings / Classification / Image / Audio 기능

Dedicated overview에는 다음 inference API도 포함되어 있다.

| 기능 | 설명 |
| --- | --- |
| Completions | prompt 기반 텍스트 완성 |
| Messages Beta | Anthropic Messages 스타일의 구조화 메시지 API |
| Embeddings | 텍스트를 벡터로 변환 |
| Text classification | 텍스트 분류 |
| Image generations | 텍스트 기반 이미지 생성 |
| Image edits | 이미지 편집 |
| Audio transcriptions | 음성 파일을 텍스트로 변환 |

중요: 이 기능들이 Dedicated 제품군에 존재한다는 뜻이지, 현재 배포된 EXAONE 텍스트 LLM endpoint 하나가 이미지/음성/임베딩까지 모두 처리한다는 뜻은 아니다. 각 기능은 해당 태스크를 지원하는 모델과 endpoint가 있어야 정상 동작한다. 현재 EXAONE endpoint에서 우선 검증된 것은 Chat Completions 계열이다.

## 13. Endpoint 관리 API

Friendli Dedicated Endpoint 관리 API는 beta로 제공된다. 문서상 base path는 다음 계열이다.

```text
/dedicated/beta/endpoint
/dedicated/beta/endpoint/{endpoint_id}
/dedicated/beta/endpoint/{endpoint_id}/status
/dedicated/beta/endpoint/{endpoint_id}/version
/dedicated/beta/endpoint/{endpoint_id}/sleep
/dedicated/beta/endpoint/{endpoint_id}/wake
/dedicated/beta/endpoint/{endpoint_id}/terminate
/dedicated/beta/endpoint/{endpoint_id}/restart
```

### 13.1 가능한 관리 기능

| 기능 | API 의미 |
| --- | --- |
| List endpoints | 프로젝트/팀의 Dedicated Endpoint 목록 조회 |
| Retrieve endpoint specification | endpoint 모델, GPU, replica 등 상세 spec 조회 |
| Retrieve endpoint versions | endpoint version history 조회 |
| Retrieve endpoint status | 실행 상태 조회 |
| Create endpoint with Hugging Face model | Hugging Face 모델로 endpoint 생성 |
| Create endpoint from W&B artifact | Weights & Biases artifact로 endpoint 생성 |
| Update endpoint configuration | 모델/GPU/replica 등 설정 변경 |
| Sleep endpoint | endpoint를 sleep 상태로 전환 |
| Wake endpoint | sleeping endpoint 재기동 |
| Terminate endpoint | inference 중단 및 리소스 release |
| Restart endpoint | 실패/종료 endpoint 재시작 |
| Delete endpoint | endpoint 삭제 |

### 13.2 상태 확인 예시

```bash
curl -X GET "https://api.friendli.ai/dedicated/beta/endpoint/$LG_K_EXAONE_ENDPOINT_ID/status" \
  -H "Authorization: Bearer $LG_K_EXAONE_API_KEY"
```

응답은 endpoint의 현재 상태와 phase 정보를 포함한다. 실제 상태 문자열은 공식 Endpoint Beta 응답 스키마와 실행 환경에 따라 달라질 수 있으므로, 운영 코드에서는 특정 문자열만 하드코딩하기보다 unknown/default 분기를 함께 둔다.

## 14. EXAONE 배포/운영 설정

EXAONE 4.0 튜토리얼 기준 Dedicated Endpoint 생성 시 고려할 수 있는 설정은 다음이다.

- EXAONE 4.0 계열 base model 선택
- Multi-LoRA adapter 적용
- Online Quantization으로 GPU 사용량/처리량 최적화
- N-gram Speculative Decoding으로 output token latency 최적화
- GPU type 선택
- autoscaling parameter 설정
- inference engine 설정
  - special token 추가
  - special token skip
  - maximum batch size
  - request content logging
- Playground에서 system prompt, token length, temperature, top_p, frequency penalty 테스트
- metrics/logs로 throughput, latency, processed token, replica count, request activity 모니터링

Request/response content logging은 디버깅에는 유용하지만 민감정보가 로그에 남을 수 있으므로 운영에서는 신중하게 켜야 한다.

## 15. 챗봇 / 멀티에이전트 관점

### 15.1 이전 대화 기억

Friendli Chat Completions API 자체는 stateless다. 이전 대화를 자동으로 기억하지 않는다.

챗봇이 이전 대화를 기억하게 하려면 애플리케이션이 이전 `messages`를 매 요청마다 다시 넣어야 한다.

```json
{
  "messages": [
    {"role": "system", "content": "너는 Neuro-Sync 상담 챗봇이다."},
    {"role": "user", "content": "내 이름은 민수야."},
    {"role": "assistant", "content": "알겠습니다, 민수님."},
    {"role": "user", "content": "내 이름 기억해?"}
  ]
}
```

대화가 길어지면 다음 전략이 필요하다.

- 최근 N턴만 유지
- 오래된 대화는 요약해서 system/developer context로 삽입
- 사용자 profile/memory store를 별도 DB에 저장
- RAG 검색으로 필요한 기억만 가져오기
- tokenization API 또는 tokenizer로 context window 초과 전 검사

### 15.2 하나의 endpoint로 병렬 에이전트가 가능한가

가능하다. 같은 endpoint에 여러 HTTP 요청을 동시에 보내고, 각 요청의 `messages`를 다르게 구성하면 병렬 에이전트처럼 운용할 수 있다.

단, 각 에이전트는 자동으로 서로의 대화를 알지 못한다. 다른 에이전트에게 내용을 전달하려면 오케스트레이터가 명시적으로 다음 요청의 `messages`에 넣어야 한다.

예시:

1. Agent A 요청: 문서 요약
2. Agent B 요청: 문서 리스크 분석
3. Orchestrator가 A/B 결과를 수집
4. Agent C 요청의 `messages`에 A/B 결과를 넣고 최종 판단 요청

이 구조에서 정보 전달은 API가 자동으로 하는 것이 아니라 애플리케이션이 한다.

### 15.3 endpoint가 하나인 경우 한계

가능한 것:

- 같은 모델/endpoint에 병렬 요청
- 역할별 system prompt로 agent 성격 분리
- 독립 context로 agent isolation 구현
- 오케스트레이터가 agent 간 결과 전달

어려운 것:

- 하나의 API key로 서로 다른 모델을 동시에 호출하는 테스트
- 모델별 성능 비교
- endpoint별 장애/latency 분산
- EXAONE 텍스트 endpoint 하나로 이미지/음성/임베딩까지 처리

다른 모델을 병렬 호출하려면 Friendli에 여러 Dedicated Endpoint를 만들거나, Model APIs/serverless 모델을 별도로 사용해야 한다.

## 16. 현재 프로젝트 테스트 스크립트

### 16.1 기본 호출

```bash
python scripts/test_lg_exaone.py
python scripts/test_lg_exaone.py "Neuro-Sync를 한 문장으로 설명해줘."
```

확인하는 것:

- `.env`에서 `LG_K_EXAONE_API_KEY`, `LG_K_EXAONE_ENDPOINT_ID` 로드
- `POST /dedicated/v1/chat/completions` 호출
- HTTP 200 여부
- assistant message 추출
- `usage` 출력
- `finish_reason=length`면 `max_tokens` 부족 힌트 출력

### 16.2 챗봇/컨텍스트/병렬 동작

```bash
python scripts/test_exaone_behaviors.py
```

확인하는 것:

- 단일 호출 성공 여부
- 이전 대화를 `messages`에 넣었을 때 기억하는지
- 이전 대화를 넣지 않았을 때 기억하지 않는지
- 병렬 요청이 가능한지
- agent 간 결과를 명시적으로 전달했을 때 후속 agent가 사용할 수 있는지

### 16.3 병렬 agent isolation

```bash
python scripts/test_exaone_agent_isolation.py
```

확인하는 것:

- 같은 endpoint에 3개 agent 요청을 병렬 전송
- 각 agent에 서로 다른 private code를 제공
- agent가 자기 code만 알고, 다른 agent code는 모른다고 답하는지 확인

이 테스트의 핵심 결론:

- 하나의 endpoint라도 병렬 요청은 가능하다.
- 요청별 `messages`는 독립적이다.
- 다른 agent의 내용을 자동으로 알지 못한다.
- 다른 agent에게 내용을 전달하려면 반드시 오케스트레이터가 프롬프트/messages에 넣어야 한다.

## 17. 구현 권장 설정

일반 챗봇 기본값:

```json
{
  "max_tokens": 512,
  "temperature": 0.2,
  "stream": false,
  "chat_template_kwargs": {
    "enable_thinking": false
  },
  "parse_reasoning": true,
  "include_reasoning": false
}
```

복잡한 reasoning 작업:

```json
{
  "max_tokens": 2048,
  "temperature": 1.0,
  "top_p": 1.0,
  "chat_template_kwargs": {
    "enable_thinking": true
  },
  "parse_reasoning": true,
  "include_reasoning": false
}
```

JSON 출력 작업:

```json
{
  "temperature": 0,
  "max_tokens": 512,
  "response_format": {
    "type": "json_object"
  },
  "chat_template_kwargs": {
    "enable_thinking": false
  },
  "parse_reasoning": true,
  "include_reasoning": false
}
```

## 18. 주의사항

- API Key는 `flp_...` 형태의 Personal API Key이며 절대 문서/코드에 하드코딩하지 않는다.
- 현재 endpoint ID는 모델 이름이 아니라 Friendli Dedicated 배포 ID다.
- reasoning token은 `include_reasoning=false`여도 usage/billing에 포함될 수 있다.
- `finish_reason=length`면 답변이 잘린 것이므로 `max_tokens`를 늘린다.
- `response_format`을 사용할 때는 system/user prompt에도 JSON 출력 요구를 명시한다.
- `tools`와 `response_format`은 함께 쓸 수 없다.
- Endpoint 관리 API는 beta이므로 운영 자동화에서는 실패/상태 변화에 대한 fallback을 둔다.
- Request content logging은 민감정보 노출 위험이 있어 운영에서 기본 off로 두는 편이 안전하다.
