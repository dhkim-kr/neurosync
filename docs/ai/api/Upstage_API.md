# Upstage API 사용 가이드

원문: <https://console.upstage.ai/api/docs/for-agents/raw>  
확인일: 2026-06-09

이 문서는 Upstage `for-agents/raw` API 레퍼런스를 기준으로, 실제 개발에 필요한 사용법만 한국어로 정리한 것이다. API Key 값은 문서에 직접 쓰지 않고 `.env`의 `UPSTAGE_API_KEY`를 사용한다.

## 1. 기본 설정

### 인증

Upstage API는 `Authorization` 헤더에 Bearer token을 넣어 호출한다.

```bash
Authorization: Bearer $UPSTAGE_API_KEY
```

현재 프로젝트의 `.env`에는 다음 형태로 설정한다.

```env
UPSTAGE_API_KEY=...
UPSTAGE_BASE_URL=https://api.upstage.ai/v1
UPSTAGE_V2_BASE_URL=https://api.upstage.ai/v2
UPSTAGE_CHAT_MODEL=solar-pro3
```


# API KEY
################################################
UPSTAGE_API_KEY=up_P7vzCgDt8yjQ0gfJOmJAw1NaCu3kU
################################################


`UPSTAGE_BASE_URL`은 현재 `scripts/test_upstage_solar.py`가 사용하는 v1 Chat API base URL이다. Agent API, Responses, File Search처럼 v2를 쓰는 코드가 추가될 때는 `UPSTAGE_V2_BASE_URL`을 별도로 사용한다.

### Base URL

| 용도 | Base URL |
|---|---|
| Chat, Embeddings, Document OCR/Parse/Classify/Extraction | `https://api.upstage.ai/v1` |
| Agent API, Files, Responses | `https://api.upstage.ai/v2` |
| Vector Stores, File Search/RAG | `https://api.upstage.ai/v2` |

주의: **Agent API는 v1이 아니라 v2**를 사용한다.

## 2. Getting Started / 콘솔 사용 흐름

Getting Started 페이지는 “계정 생성 → API Key 발급 → Playground에서 먼저 확인 → 필요한 기능 문서로 이동 → API 호출” 흐름을 안내한다. 콘솔 상단 배너에서는 Solar Pro 3를 바로 Playground에서 시험해볼 수 있고, 본문 카드들은 기능별 Playground와 Documentation으로 연결된다.

### 처음 시작 순서

1. <https://console.upstage.ai>에서 계정을 만든다.
2. API Keys 메뉴에서 API Key를 발급한다.
3. 키를 프로젝트 `.env`의 `UPSTAGE_API_KEY`에 저장한다.
4. Playground에서 먼저 동작을 확인한다.
5. 같은 설정을 API 요청 코드로 옮긴다.
6. 운영 코드에서는 API Key를 코드/문서/Git에 넣지 않고 환경변수나 secret manager로 주입한다.

### Playground 우선 테스트

개발 전에는 Playground에서 prompt, model, temperature, reasoning, schema 등을 먼저 맞추는 것이 빠르다.

| 기능 | Playground |
|---|---|
| Chat / Solar Pro 3 | <https://console.upstage.ai/playground/chat> |
| Document parsing | <https://console.upstage.ai/playground/document-parsing> |
| Information extraction | <https://console.upstage.ai/playground/universal-information-extraction> |
| Document classification | <https://console.upstage.ai/playground/document-classification> |

### Getting Started 카드별 용도

| 카드 | 설명 | 관련 문서 |
|---|---|---|
| Chat | Solar 계열 LLM으로 챗봇/텍스트 생성 | <https://console.upstage.ai/docs/capabilities/generate/chat> |
| Document parsing | PDF/문서 구조를 LLM이 읽기 좋은 Markdown/HTML 등으로 변환 | <https://console.upstage.ai/docs/capabilities/parse/document-parsing> |
| Information extraction | 문서에서 key-value, 필드, 구조화 데이터를 고정 schema로 추출 | <https://console.upstage.ai/docs/capabilities/extract/universal-extraction> |
| Document classification | 문서를 미리 정의한 카테고리로 분류 | <https://console.upstage.ai/docs/capabilities/classify/document-classification> |
| Embeddings | 텍스트를 벡터로 변환해 검색/RAG에 사용 | <https://console.upstage.ai/docs/capabilities/embed> |

### 주요 문서 메뉴

Getting Started 좌측 문서 내비게이션에서 확인되는 실사용 메뉴는 다음과 같다.

| 영역 | 주요 페이지 |
|---|---|
| Overview | Getting started, Models, Deployment Options, For AI Coding Assistant |
| Studio & Agents | Studio, Create a custom agent, Feedback loop, Performance Monitor, Agents API, Files, Jobs |
| Generate | Chat, Reasoning, Structured outputs, Function calling |
| Parse | Document parsing, API Quickstart, Input requirements, Understanding output, Chart Recognition, Merge multipage table, Handling large documents, Tips & FAQ, Document OCR |
| Extract | Universal extraction, Writing a schema, Location coordinates, Document split, Confidence, Asynchronous API |
| Classify | Document Classification, Document split |
| Search | File Search |
| Guides | Rate limits, Counting tokens, MCP server |
| Resources | Cookbook, Pricing, Support, Changelog, Error codes, FAQ |

## 3. 모델 alias

문서는 버전 고정 이름보다 alias 사용을 권장한다. alias는 최신 버전으로 매핑될 수 있다.

| Alias | 용도 |
|---|---|
| `solar-pro3` | 최신 Solar Pro 계열 Chat 모델, 복잡한 reasoning 작업 권장 |
| `solar-pro2` | 이전 세대 Solar Pro Chat 모델 |
| `solar-mini` | 빠르고 가벼운 Chat 모델 |
| `syn-pro` | 합성 데이터 최적화 모델, function calling 미지원 |
| `embedding-query` | 검색 질의용 embedding |
| `embedding-passage` | 문서 passage embedding |
| `ocr` | 문서 OCR |
| `document-parse` | 문서 구조 파싱 |
| `document-classify` | 문서 분류 |
| `information-extract` | 문서 정보 추출 |

## 4. Chat Completions API

텍스트 생성/챗봇/멀티에이전트 기본 호출에 사용한다.

### Endpoint

```text
POST https://api.upstage.ai/v1/chat/completions
```

### 기본 요청

```bash
curl -X POST https://api.upstage.ai/v1/chat/completions \
  -H "Authorization: Bearer $UPSTAGE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "solar-pro3",
    "messages": [
      {"role": "system", "content": "한국어로 간결하게 답해라."},
      {"role": "user", "content": "안녕. 한 문장으로 답해줘."}
    ],
    "max_tokens": 200,
    "temperature": 0.2
  }'
```

### Python 예시

```python
import os
import requests
from dotenv import load_dotenv

load_dotenv(".env")

response = requests.post(
    "https://api.upstage.ai/v1/chat/completions",
    headers={
        "Authorization": f"Bearer {os.environ['UPSTAGE_API_KEY']}",
        "Content-Type": "application/json",
    },
    json={
        "model": os.getenv("UPSTAGE_CHAT_MODEL", "solar-pro3"),
        "messages": [
            {"role": "user", "content": "Hello, Solar."}
        ],
        "max_tokens": 200,
    },
    timeout=60,
)

data = response.json()
print(data["choices"][0]["message"]["content"])
```

### 주요 파라미터

| 파라미터 | 필수 | 설명 |
|---|---:|---|
| `model` | 예 | `solar-pro3`, `solar-pro2`, `solar-mini`, `syn-pro` 등 |
| `messages` | 예 | `system`, `user`, `assistant`, `tool` 메시지 배열 |
| `max_tokens` | 아니오 | 생성할 최대 토큰 수 |
| `temperature` | 아니오 | 응답 다양성. 낮을수록 일관적 |
| `stream` | 아니오 | `true`면 SSE streaming |
| `reasoning_effort` | 아니오 | reasoning 강도. `minimal`, `low`, `medium`, `high`. 모델별 지원 범위가 다르므로 운영 코드에서는 명시 지정 권장 |
| `tools` | 아니오 | function calling 도구 정의 |
| `tool_choice` | 아니오 | `none`, `auto`, `required`, 특정 함수 지정 |
| `parallel_tool_calls` | 아니오 | `solar-pro3`의 병렬 tool call 사용 여부. 기본 `true` |
| `response_format` | 아니오 | JSON schema 기반 structured output |
| `prompt_cache_key` | 아니오 | 프롬프트 캐싱용 session key |

### 챗봇 memory 주의점

Chat API는 기본적으로 요청 단위로 독립적이다. 이전 대화를 기억하게 하려면 서버가 이전 `messages`를 다시 포함해서 보내야 한다.

```json
[
  {"role": "user", "content": "내 이름은 민수야."},
  {"role": "assistant", "content": "알겠습니다."},
  {"role": "user", "content": "내 이름이 뭐였지?"}
]
```

`prompt_cache_key`는 latency/cost 최적화용 캐시 키이지, 자동 memory 저장소가 아니다. 사용자별 대화 기록은 별도 DB나 session store에서 관리해야 한다.

## 5. Reasoning 설정

`solar-pro3`는 reasoning budget을 지원한다.

| 값 | 의미 | 권장 상황 |
|---|---|---|
| `high` | 강한 reasoning | 복잡한 추론, 분석 |
| `medium` | 균형형 reasoning | 일반적인 고난도 작업 |
| `low` | reasoning off 또는 최소화 | 빠른 단순 응답 |
| `minimal` | reasoning off 기본값 계열 | 가장 단순한 응답, reasoning 비활성화가 필요한 경우 |

주의: 공식 문서 내에서 `solar-pro3`의 기본 reasoning 설명이 `minimal`과 `medium` 계열로 혼재되어 보일 수 있다. 운영 코드에서는 기본값에 의존하지 말고 `reasoning_effort`를 명시적으로 지정하는 편이 안전하다.

단순 챗봇/에이전트 라우팅에서는 보통 다음처럼 시작하는 것이 안전하다.

```json
{
  "model": "solar-pro3",
  "reasoning_effort": "low",
  "temperature": 0.2,
  "max_tokens": 300
}
```

## 6. Structured Output

정해진 JSON 형식이 필요하면 `response_format`에 JSON schema를 넣는다.

```json
{
  "model": "solar-pro3",
  "messages": [
    {
      "role": "user",
      "content": "Coffee $5, Sandwich $8에서 메뉴를 추출해줘."
    }
  ],
  "response_format": {
    "type": "json_schema",
    "json_schema": {
      "name": "menu_extraction",
      "strict": true,
      "schema": {
        "type": "object",
        "properties": {
          "items": {
            "type": "array",
            "items": {
              "type": "object",
              "properties": {
                "name": {"type": "string"},
                "price": {"type": "number"}
              },
              "required": ["name", "price"],
              "additionalProperties": false
            }
          }
        },
        "required": ["items"],
        "additionalProperties": false
      }
    }
  }
}
```

제약:

- `strict`는 `true`
- 모든 필드는 `required`에 포함
- `additionalProperties`는 `false`
- 최대 nesting depth는 3
- recursive schema와 `$ref`는 미지원

## 7. Function Calling

외부 API/DB/함수를 모델이 호출하게 만들 때 사용한다.

### 도구 정의

```json
{
  "type": "function",
  "function": {
    "name": "get_current_weather",
    "description": "도시의 현재 날씨 조회",
    "parameters": {
      "type": "object",
      "properties": {
        "location": {
          "type": "string",
          "description": "도시명"
        }
      },
      "required": ["location"]
    }
  }
}
```

### 병렬 tool call

`solar-pro3`는 `parallel_tool_calls`를 지원한다. 예를 들어 “서울과 파리 날씨를 알려줘”처럼 독립적인 도구 호출이 여러 개 필요하면 모델이 여러 tool call을 한 번에 반환할 수 있다.

중요한 흐름:

1. 모델에 `tools`를 포함해 요청
2. 응답의 `tool_calls` 확인
3. 서버가 실제 함수를 실행
4. 실행 결과를 `role: "tool"` 메시지로 다시 모델에 전달
5. 모델이 최종 답변 생성

즉, 도구 실행은 모델이 직접 하지 않고 **애플리케이션 서버가 실행**한다.

## 8. Streaming

`stream: true`를 주면 SSE 형태로 token delta를 받는다.

```python
from openai import OpenAI
import os

client = OpenAI(
    api_key=os.environ["UPSTAGE_API_KEY"],
    base_url="https://api.upstage.ai/v1",
)

stream = client.chat.completions.create(
    model="solar-pro3",
    messages=[{"role": "user", "content": "짧은 이야기를 써줘."}],
    stream=True,
)

for chunk in stream:
    text = chunk.choices[0].delta.content
    if text:
        print(text, end="", flush=True)
```

## 9. Agent API

Agent API는 Upstage Studio에서 만든 multi-step workflow를 실행하는 API다. 예를 들어 `Parse -> Classify -> Extract` 같은 문서 처리 파이프라인을 Studio에서 만든 뒤 API로 실행한다.

중요 조건:

- Agent 생성은 API로 하지 않는다.
- 먼저 <https://studio.upstage.ai>에서 Agent workflow를 만든다.
- Studio의 Code panel에서 `Agent ID`를 복사한다.
- 실행은 `POST /v2/responses`로 한다.

### Base URL

```text
https://api.upstage.ai/v2
```

### 9.1 파일 업로드

Agent가 처리할 파일을 먼저 업로드해서 `file_id`를 받는다.

```bash
curl -X POST https://api.upstage.ai/v2/files \
  -H "Authorization: Bearer $UPSTAGE_API_KEY" \
  -F "file=@document.pdf" \
  -F "purpose=user_data"
```

응답:

```json
{
  "id": "file-abc123",
  "object": "file",
  "bytes": 17408,
  "created_at": 1756368389,
  "expires_at": null,
  "filename": "document.pdf",
  "purpose": "user_data"
}
```

### 9.2 Agent Job 생성

```bash
curl -X POST https://api.upstage.ai/v2/responses \
  -H "Authorization: Bearer $UPSTAGE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "agt_YOUR_AGENT_ID",
    "include": ["last"],
    "input": [
      {
        "role": "user",
        "content": [
          {
            "type": "input_file",
            "file_id": "file-abc123"
          }
        ]
      }
    ]
  }'
```

요청 필드:

| 필드 | 필수 | 설명 |
|---|---:|---|
| `model` | 예 | Studio에서 복사한 Agent ID |
| `input` | 예 | 입력 메시지. 파일은 `input_file` 블록으로 전달 |
| `include` | 아니오 | `["last"]`는 최종 step만, `["all"]`은 전체 step 결과 |

### 9.3 Job 조회

```bash
curl "https://api.upstage.ai/v2/responses/{JOB_ID}?include[]=last" \
  -H "Authorization: Bearer $UPSTAGE_API_KEY"
```

Job 상태:

| 상태 | 의미 |
|---|---|
| `queued` | 대기 중 |
| `in_progress` | 처리 중 |
| `completed` | 완료 |
| `failed` | 실패 |

### 9.4 Python end-to-end

```python
import os
import time
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv(".env")

client = OpenAI(
    api_key=os.environ["UPSTAGE_API_KEY"],
    base_url="https://api.upstage.ai/v2",
)

AGENT_ID = "agt_YOUR_AGENT_ID"

with open("document.pdf", "rb") as f:
    uploaded = client.files.create(file=f, purpose="user_data")

response = client.responses.create(
    model=AGENT_ID,
    include=["last"],
    input=[
        {
            "role": "user",
            "content": [{"type": "input_file", "file_id": uploaded.id}],
        }
    ],
)

while response.status in {"queued", "in_progress"}:
    time.sleep(2)
    response = client.responses.retrieve(response.id, include=["last"])

if response.status == "completed":
    print(response.output_text)
else:
    print(response.model_dump())
```

## 10. File Search / RAG API

파일을 업로드하고 vector store에 넣은 뒤 검색하거나, 검색 결과 기반으로 답변을 생성할 수 있다. 이 API도 v2를 사용한다.

검증 메모: 2026-06-09 기준 공식 raw 문서에서 Agent/Responses API와 File Search / Vector Store가 모두 v2 계열로 확인된다. 다만 File Search는 Beta 기능이므로 운영 코드 작성 전 공식 레퍼런스의 최신 request/response schema와 제한값을 재검증한다.

### 제한

| 항목 | 제한 |
|---|---:|
| Vector stores per user | 50 |
| Files per vector store | 500 |
| Files per batch | 50 |

지원 파일 형식:

```text
PDF, DOCX, PPTX, XLSX, HWP, HWPX, MD, TXT, JPEG, JPG, PNG, BMP, TIFF, TIF, HEIC
```

### 10.1 RAG 구성 흐름

```text
1. POST /v2/files
   -> file_id 획득

2. POST /v2/vector_stores
   -> vector_store_id 획득

3. POST /v2/vector_stores/{id}/files
   -> 파일 색인 시작

4. GET /v2/vector_stores/{id}/files/{file_id}
   -> status가 completed 될 때까지 polling

5. POST /v2/vector_stores/{id}/search
   -> 문서 검색

6. POST /v2/responses
   -> file_search tool을 사용해 RAG 답변 생성
```

### 10.2 Vector Store 생성

```bash
curl -X POST https://api.upstage.ai/v2/vector_stores \
  -H "Authorization: Bearer $UPSTAGE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"name": "my-knowledge-base"}'
```

응답의 `id`가 `vector_store_id`다.

### 10.3 파일 추가

```bash
curl -X POST https://api.upstage.ai/v2/vector_stores/{VECTOR_STORE_ID}/files \
  -H "Authorization: Bearer $UPSTAGE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"file_id": "file-abc123"}'
```

색인 상태는 `in_progress -> completed | failed | cancelled`로 바뀐다.

### 10.4 검색

```bash
curl -X POST https://api.upstage.ai/v2/vector_stores/{VECTOR_STORE_ID}/search \
  -H "Authorization: Bearer $UPSTAGE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "문서의 핵심 내용은?",
    "max_num_results": 5
  }'
```

응답에는 `file_id`, `filename`, `score`, 매칭된 `content`가 포함된다.

### 10.5 RAG 답변 생성

```bash
curl -X POST https://api.upstage.ai/v2/responses \
  -H "Authorization: Bearer $UPSTAGE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "solar-pro3",
    "input": "문서의 핵심 내용을 요약해줘.",
    "tools": [
      {
        "type": "file_search",
        "vector_store_ids": ["vs_abc123"],
        "max_num_results": 5
      }
    ]
  }'
```

응답 구조:

- `output[]`에 `file_search_call`과 `message`가 포함된다.
- 최종 답변은 `type: "message"` 항목의 `content[].text`에 들어간다.

## 11. Document APIs 요약

문서 OCR/파싱/분류/추출은 v1을 사용한다.

| 목표 | API | Endpoint |
|---|---|---|
| 스캔 문서 텍스트 추출 | Document OCR | `POST /v1/document-digitization` with `model=ocr` |
| PDF를 Markdown/HTML 구조로 변환 | Document Parse | `POST /v1/document-digitization` with `model=document-parse` |
| 대용량 문서 비동기 파싱 | Document Parse Async | `POST /v1/document-digitization/async` |
| 문서 유형 분류 | Document Classification | `POST /v1/document-classification` |
| 특정 필드 추출 | Information Extraction | `POST /v1/information-extraction` |
| 대용량 정보 추출 | IE Async | `POST /v1/information-extraction/async` |

공통 제한:

- 최대 파일 크기: 50MB
- 일반 Document API 지원 포맷: JPEG, PNG, BMP, PDF, TIFF, HEIC, DOCX, PPTX, XLSX, HWP, HWPX
- Document OCR: 최대 100 pages
- Document Parse: sync 100 pages, async 1,000 pages
- Information Extraction: sync 100 pages, async 1,000 pages
- 주의: Information Extraction Async는 HWP/HWPX를 지원하지 않는다. IE Async 대상 파일은 PDF, JPEG, PNG, BMP, TIFF, HEIC, DOCX, PPTX, XLSX 위주로 제한해서 처리한다.

## 12. Error / Rate Limit / Token 관리

일반 오류 형식:

```json
{
  "error": {
    "message": "Description of the error.",
    "type": "error_type",
    "code": null
  }
}
```

주요 상태 코드:

| HTTP | 의미 |
|---:|---|
| 400 | 잘못된 요청, 필드 누락, 제한 초과 |
| 401 | API Key 누락 또는 잘못된 API Key |
| 403 | 권한 또는 credit 부족 |
| 404 | 파일, vector store, job, URL path 등을 찾을 수 없음 |
| 405 | 허용되지 않은 method 또는 잘못된 프로토콜 사용 |
| 415 | 지원하지 않는 media type 또는 파일 형식 |
| 422 | 손상된 문서, metadata/attributes 제한 초과, 잘못된 chunking strategy 등 |
| 429 | rate limit 초과 |
| 500/502/503/504 | 서버 또는 gateway 계열 오류. 짧은 지연 후 재시도 |

rate limit 대응:

- 429가 나오면 exponential backoff 적용
- 병렬 요청 수 제한
- 대량 문서는 async API나 batch 처리 사용
- 동일한 긴 system prompt/context는 `prompt_cache_key` 사용 검토

### Token counting

Counting tokens 가이드는 Hugging Face `tokenizers` 라이브러리 사용을 안내한다. 긴 context나 멀티턴 챗봇을 만들 때는 요청 전에 토큰 수를 계산하고, limit을 넘는 부분은 요약하거나 잘라야 한다.

설치:

```bash
pip install tokenizers==0.20.0
```

모델별 tokenizer:

| Tokenizer | 대상 모델 |
|---|---|
| `upstage/solar-pro3-tokenizer` | `solar-pro3` |
| `upstage/solar-pro2-tokenizer` | `solar-pro2`, `syn-pro` |
| `upstage/solar-1-mini-tokenizer` | `solar-mini`, `embedding-query`, `embedding-passage` |

예시:

```python
from tokenizers import Tokenizer

tokenizer = Tokenizer.from_pretrained("upstage/solar-pro3-tokenizer")
text = "Hi, how are you?"

encoded = tokenizer.encode(text)
print(len(encoded.ids))

token_limit = 4000
truncated_text = tokenizer.decode(encoded.ids[:token_limit])
```

## 13. 멀티에이전트 구현 관점

Upstage Chat API 자체는 요청 단위 stateless다. 따라서 에이전트 간 정보 전달은 자동으로 되지 않는다.

권장 구조:

```text
User request
  -> Orchestrator server
     -> Agent A: 의도 분석
     -> Agent B: 문서 검색/RAG
     -> Agent C: 최종 응답 작성
  -> Shared memory / DB
  -> Final response
```

에이전트 간 내용을 전달하려면 서버가 Agent A의 결과를 Agent B의 `messages` 또는 `input`에 명시적으로 넣어줘야 한다.

```json
[
  {
    "role": "system",
    "content": "너는 예약 가능 여부를 판단하는 에이전트다."
  },
  {
    "role": "user",
    "content": "Agent A 분석 결과: 사용자는 6월 10일 오전 진료를 원한다. 가능한 슬롯을 판단해라."
  }
]
```

같은 API Key나 같은 모델을 쓴다고 해서 context가 공유되지는 않는다.

## 14. 프로젝트 내 테스트 스크립트

현재 프로젝트에는 Solar Pro 테스트용 스크립트가 있다.

```bash
python scripts/test_upstage_solar.py
```

이 스크립트는 다음을 확인한다.

- 기본 Chat 호출
- 히스토리를 넣었을 때 이전 대화 기억 여부
- 히스토리 없이 호출했을 때 기억하지 않는지
- 같은 API Key/model로 병렬 에이전트 호출 시 context가 섞이지 않는지

## 15. 보안 메모

- API Key는 `.env`에만 저장한다.
- 코드, 문서, Git commit에 실제 키를 넣지 않는다.
- 키가 대화나 문서에 노출되면 콘솔에서 폐기/재발급한다.
- 운영 서버에서는 환경변수/secret manager로 주입한다.
