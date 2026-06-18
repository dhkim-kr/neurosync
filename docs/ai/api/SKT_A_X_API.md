# SKT A.X API 기능 정리

기준 문서:

- Service: https://portal.adot.ai/service
- A.X K1 LLM API guide: https://portal.adot.ai/docs/ax-k1-api-guide
- A.X STT API guide: https://portal.adot.ai/docs/stt-api-guide

확인일: 2026-06-15
공식 LLM 가이드 버전: v1.3

이 문서는 SKT AI One Portal의 A.X K1 LLM API와 A.X STT API를 Neuro-Sync에서 사용할 수 있도록 기능, endpoint, 인증 방식, 적용 패턴을 정리한다. 실제 API Key 값은 문서에 기록하지 않고 환경변수로만 사용한다.

> **서비스 성격 주의:** 공식 문서상 A.X K1 LLM과 A.X STT는 전국민 AI 경진대회 전용 서비스이며, 종료 예정일은 2026-11-23이다. 따라서 장기 상용 운영을 전제로 고정 의존하지 말고 LLM/STT Adapter 구조로 구현한다.

## 1. 한 줄 결론

SKT A.X API는 하나의 API Key로 LLM과 STT를 모두 사용할 수 있다.

- A.X K1 LLM API: OpenAI Chat Completions 호환 챗봇/요약/분류/추출 API
- A.X STT API: 한국어 음성을 텍스트로 변환하는 Streaming/WebSocket 및 Batch/REST API

주의할 점은 두 API의 인증 헤더가 다르다는 것이다.

| API | 인증 헤더 |
|---|---|
| LLM API | `Authorization: Bearer $SKT_A_X_API_KEY` |
| STT API | `X-API-Key: $SKT_A_X_API_KEY` |

## 2. 프로젝트 환경 변수

`.env`에는 실제 값이 들어가고, 문서/코드 예제에는 아래처럼 변수명만 쓴다.

```env
SKT_A_X_API_KEY=YOUR_AWF_API_KEY
SKT_A_X_REST_BASE_URL=https://awf-gw.adot.ai
SKT_A_X_WS_BASE_URL=wss://awf-gw.adot.ai
SKT_A_X_LLM_MODEL=A.X-K1
SKT_A_X_STT_STREAMING_MODEL=A.X_STT_note_streaming
SKT_A_X_STT_BATCH_MODEL=A.X_STT_note_batch
```

### API Key / Endpoint 요약

| 항목 | 값 |
|---|---|
| API Key 위치 | `.env`의 `SKT_A_X_API_KEY` |
| REST Base URL | `https://awf-gw.adot.ai` |
| WebSocket Base URL | `wss://awf-gw.adot.ai` |
| LLM Chat Endpoint | `POST https://awf-gw.adot.ai/v1/chat/completions` |
| STT Streaming Endpoint | `wss://awf-gw.adot.ai/v1/stt/realtime` |
| STT Upload Token Endpoint | `GET https://awf-gw.adot.ai/v1/stt/upload-token?fileSize={SIZE}` |
| STT File Upload Endpoint | `PUT https://awf-gw.adot.ai/v1/stt/upload/{upload_token}` |
| STT Batch Transcript Endpoint | `POST https://awf-gw.adot.ai/v1/stt/transcript` |
| LLM 모델 | `A.X-K1` |
| STT Streaming 모델 | `A.X_STT_note_streaming` |
| STT Batch 모델 | `A.X_STT_note_batch` |

실제 API Key는 공유 문서, 커밋, 로그에 노출하지 않는다.

## 3. A.X K1 LLM API

### 3.1 기능

A.X K1 LLM API는 OpenAI Chat Completions 형식과 호환되는 텍스트 생성 API다.

가능한 작업:

- 챗봇 / 대화형 AI
- 멀티턴 대화
- 긴 글 요약
- 감정/카테고리 분류
- 키워드/정보 추출
- 번역
- 문체 변환
- 코드 설명, 디버깅, 작성
- JSON 등 구조화된 출력 생성

Neuro-Sync에서는 사전문진 챗봇, 대화 요약, handoff report 초안 생성, 문진 정보 추출 후보로 사용할 수 있다.

### 3.2 기본 호출

```bash
curl -X POST https://awf-gw.adot.ai/v1/chat/completions \
  -H "Authorization: Bearer $SKT_A_X_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "A.X-K1",
    "messages": [
      {
        "role": "user",
        "content": "안녕!"
      }
    ]
  }'
```

### 3.3 Python OpenAI SDK 호환 호출

```python
import os
from openai import OpenAI

client = OpenAI(
    api_key=os.environ["SKT_A_X_API_KEY"],
    base_url="https://awf-gw.adot.ai/v1",
)

resp = client.chat.completions.create(
    model="A.X-K1",
    messages=[
        {"role": "user", "content": "한국어로 자기소개를 해줘."}
    ],
)

print(resp.choices[0].message.content)
```

### 3.4 응답 구조

응답은 Chat Completions 계열 구조다.

```json
{
  "id": "chatcmpl-xxxx",
  "object": "chat.completion",
  "created": 1747000000,
  "model": "A.X-K1",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "안녕하세요! 무엇을 도와드릴까요?"
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 5,
    "completion_tokens": 12,
    "total_tokens": 17
  }
}
```

애플리케이션에서는 `choices[0].message.content`를 최종 답변으로 사용한다.

### 3.5 멀티턴 대화

LLM API 자체는 이전 대화를 자동으로 기억하지 않는다. 이전 대화를 기억하게 하려면 서버가 DB/session store에서 이전 메시지를 조회해 매 호출마다 `messages`에 다시 넣어야 한다.

```python
history = [
    {
        "role": "system",
        "content": "너는 Neuro-Sync 사전문진 챗봇이다. 진단/처방은 하지 말고 진료 전 정보만 수집한다."
    }
]

def chat(user_input: str) -> str:
    history.append({"role": "user", "content": user_input})
    resp = client.chat.completions.create(
        model="A.X-K1",
        messages=history,
        temperature=0.0,
        max_tokens=512,
    )
    answer = resp.choices[0].message.content
    history.append({"role": "assistant", "content": answer})
    return answer
```

운영에서는 메모리 내 `history`가 아니라 다음 구조를 사용한다.

```text
DB messages
  -> 최근 N턴 원문
  -> 오래된 대화 요약
  -> 현재 user message
  -> LLM messages로 재구성
```

### 3.6 스트리밍

긴 답변을 실시간으로 표시하려면 `stream=true`를 사용한다. OpenAI SDK에서는 chunk를 순회하면서 `delta.content`를 이어 붙이면 된다.

```python
stream = client.chat.completions.create(
    model="A.X-K1",
    messages=[
        {"role": "user", "content": "한국 역사를 한 페이지로 요약해줘."}
    ],
    stream=True,
)

for chunk in stream:
    delta = chunk.choices[0].delta
    if delta.content:
        print(delta.content, end="", flush=True)
```

### 3.7 추론 모드

A.X K1은 빠른 응답 모드와 사고 모드를 지원한다.

| 모드 | 설정 | 용도 |
|---|---|---|
| 빠른 응답 | `enable_thinking=false` 또는 옵션 생략 | 일반 대화, 문진 질문, 분류 |
| 사고 모드 | `reasoning_effort`, `enable_thinking=true` | 복잡한 추론, 코드 분석, 수학 |

사고 모드 예시:

```python
resp = client.chat.completions.create(
    model="A.X-K1",
    messages=[
        {"role": "user", "content": "복잡한 문제를 단계적으로 분석해줘."}
    ],
    max_tokens=1000,
    reasoning_effort="high",
    extra_body={
        "chat_template_kwargs": {"enable_thinking": True}
    },
)
```

Neuro-Sync 문진 챗봇의 기본 응답 생성은 빠른 응답 모드를 권장한다. 문진은 추론 과정보다 짧고 일관된 후속 질문이 중요하므로 `temperature=0.0`, `enable_thinking=false`를 우선 사용한다. 다만 공식 파라미터 표에는 OpenAI식 `response_format`이나 native JSON Schema 강제 기능이 명시되어 있지 않으므로, JSON 출력은 프롬프트로 요구한 뒤 Pydantic/JSON Schema로 애플리케이션에서 검증한다.

### 3.8 주요 파라미터

| 파라미터 | 설명 |
|---|---|
| `model` | `A.X-K1` |
| `messages` | `system`, `user`, `assistant` 역할의 대화 배열 |
| `stream` | SSE 스트리밍 응답 여부 |
| `max_tokens` | 생성 최대 토큰 수 |
| `temperature` | 무작위성. 분류/추출/문진 JSON은 `0.0` 권장 |
| `top_p` | nucleus sampling |
| `top_k` | top-k sampling |
| `presence_penalty` | 새 주제 등장 조절 |
| `frequency_penalty` | 반복 조절 |
| `reasoning_effort` | `low`, `medium`, `high` |
| `chat_template_kwargs.enable_thinking` | A.X K1 사고 모드 토글 |

### 3.9 제약 / 운영 주의

- Rate limit: 팀당 RPS 3. 초과 시 429 응답. 공식 문서 제약 표의 설명 일부에 상충 표현이 있으나 문서 상단과 FAQ가 모두 1초당 3요청으로 명시하므로 RPS 3을 기준으로 한다.
- Context limit: 128,000 Char, 공식 문서 환산 약 64K token.
- 권장 사용 패턴: 입력 8K 이하, 출력 2K 이하. 32K 이상 입력은 TTFT가 수십 초~수 분까지 길어질 수 있다.
- `Retry-After` 헤더는 현재 제공되지 않으므로 1초→2초→4초 지수 백오프를 사용한다.
- 스트리밍 중단 후 이어받기는 지원되지 않는다.
- 이전 대화 자동 기억 없음. 반드시 `messages` 또는 요약 memory를 매 호출에 포함.
- API Key는 클라이언트 앱에 직접 넣지 않는다. 백엔드에서 호출한다.
- 의료 문진에서는 진단/처방/복약 변경 지시를 금지하는 system prompt가 필요하다.


### 3.10 Structured Output 구현 주의

공식 가이드는 JSON 등 구조화된 형식의 텍스트 생성을 소개하지만, 현재 요청 파라미터 표에는 `response_format` 또는 native JSON Schema 강제 기능이 명시되어 있지 않다. 따라서 다음 방식으로 구현한다.

```text
JSON 출력 프롬프트
  -> JSON parser
  -> Pydantic/JSON Schema validation
  -> 실패 시 1회 repair prompt
  -> 반복 실패 시 오류 또는 rule-based fallback
```

A.X K1이 native schema enforcement를 지원한다고 가정하지 않는다.

### 3.11 서비스 운영 기간 및 로그 이용 주의

- A.X K1 LLM API 정식 오픈: 2026-05-22
- 서비스 종료 예정: 2026-11-23
- 공식 가이드에는 API Key 발급 시 동의한 경우 Prompt, Response, metadata를 모델 성능 개선 및 내부 연구에 활용할 수 있다고 명시되어 있다.
- 보유 기간은 목적 달성 후 파기, 최대 1년으로 안내된다.
- 동의 거부 시 API 이용에 제한이 있을 수 있다.

정신건강 문진 데이터는 고위험 민감정보이므로, Neuro-Sync의 초기 Agent test는 전부 합성 데이터로 수행한다. 실제 환자 데이터는 Prompt/Response 저장, 학습 활용, 위탁, 재위탁, 국외 이전, 삭제 절차를 서면 확인하기 전에는 전송하지 않는다.

## 4. A.X STT API

### 4.1 기능

A.X STT API는 한국어 음성을 텍스트로 변환한다.

가능한 작업:

- 실시간 음성 인식
- 라이브 자막
- 음성 명령
- 통화 녹음 변환
- 인터뷰/상담 녹취 변환
- 회의록 작성
- 음성 메모 텍스트화

Neuro-Sync에서는 Push-to-Talk 사전문진 입력의 primary STT 후보로 사용할 수 있다.

### 4.2 Streaming vs Batch

| 항목 | Streaming API | Batch API |
|---|---|---|
| 프로토콜 | WebSocket | REST |
| Endpoint | `wss://awf-gw.adot.ai/v1/stt/realtime` | `/v1/stt/upload-token`, `/v1/stt/upload/{token}`, `/v1/stt/transcript` |
| 주요 용도 | 실시간 음성 입력, 라이브 자막 | 녹음 파일, 회의록, 통화 녹취 |
| 결과 방식 | 중간 결과 + 최종 결과 실시간 수신 | 전체 결과 1회 수신 |
| 오디오 입력 | base64 JSON stream | 파일 업로드 |
| 화자 분리 | 미지원 | `speaker` 필드 지원 |
| 최대 크기/길이 | 실시간 스트림 | 파일당 최대 100MB 또는 30분 |

## 5. STT Streaming API

### 5.1 기본 흐름

```text
1. WebSocket 연결
2. create 메시지로 채널 생성
3. audio 메시지로 base64 오디오 청크 반복 전송
4. 서버가 vad/transcript 반환
5. stop 전송
6. stopped 수신
```

Endpoint:

```text
wss://awf-gw.adot.ai/v1/stt/realtime
```

인증:

```http
X-API-Key: $SKT_A_X_API_KEY
```

### 5.2 create 메시지

```json
{
  "message_type": "create",
  "speech_model": "A.X_STT_note_streaming",
  "audio_format": "pcm_16k",
  "vad_type": "semantic",
  "partial": true,
  "tr_id": "intake-session-001"
}
```

| 필드 | 필수 | 설명 |
|---|---|---|
| `message_type` | 예 | `"create"` 고정 |
| `speech_model` | 예 | `A.X_STT_note_streaming` |
| `audio_format` | 예 | `pcm_8k`, `pcm_16k`, `speex_16k`, `opus_16k` |
| `vad_type` | 아니오 | VAD 타입. 예: `semantic` |
| `partial` | 아니오 | 중간 결과 수신 여부. 기본 `true` |
| `keywords` | 아니오 | word boosting 키워드 배열 |
| `agreement_of_data_collection` | 아니오 | 음성 데이터 수집 동의 여부 |
| `tr_id` | 예 | 클라이언트 세션 트랜잭션 ID |

성공 응답:

```json
{
  "message_type": "created",
  "code": 0,
  "tr_id": "intake-session-001"
}
```

### 5.3 audio 메시지

오디오는 바이너리 WebSocket frame이 아니라 base64 JSON으로 전송한다.

```json
{
  "message_type": "audio",
  "data": "<base64 encoded audio chunk>"
}
```

권장 청크 크기는 20~400ms이며 최소 20ms다. 문진 Push-to-Talk에서는 100ms 청크가 무난하다. 오디오 미전송 구간에는 30초 이내 주기로 `keepalive`를 보낸다.

### 5.4 서버 응답

VAD:

```json
{
  "message_type": "vad",
  "detect_type": "bos",
  "time_offset": 0.5,
  "tr_id": "intake-session-001"
}
```

Transcript:

```json
{
  "message_type": "transcript",
  "text": "요즘 잠을 거의 못 자요",
  "created": "2026-05-18 10:00:00",
  "start_time": 0.5,
  "end_time": 2.7,
  "final": true,
  "words": [
    {
      "text": "요즘",
      "start_time": 0.5,
      "end_time": 0.9
    }
  ],
  "tr_id": "intake-session-001"
}
```

`final=false`는 중간 결과, `final=true`는 최종 결과다.

### 5.5 stop / keepalive / delete

오디오 전송 완료:

```json
{
  "message_type": "stop"
}
```

처리 완료 응답:

```json
{
  "message_type": "stopped"
}
```

오디오 전송이 없는 구간에는 `keepalive` 메시지를 보내 세션을 유지한다. WebSocket ping/pong만으로는 충분하지 않을 수 있다.

취소가 필요하면 `delete` 메시지로 음성인식을 중단한다.

## 6. STT Batch API

### 6.1 기본 흐름

```text
1. 파일 크기로 upload_token 발급
2. upload_token으로 음성 파일 업로드
3. file_key로 transcript 요청
4. 전체 인식 결과 수신
```

### 6.2 upload token 발급

```bash
SIZE=$(stat -c %s "$FILE")

curl -X GET "https://awf-gw.adot.ai/v1/stt/upload-token?fileSize=$SIZE" \
  -H "X-API-Key: $SKT_A_X_API_KEY"
```

응답의 `upload_token`과 `expire_at`을 확인한다. `fileSize`는 실제 PUT body 크기와 정확히 일치해야 하며, 만료 후에는 Step 1부터 다시 진행한다.

### 6.3 파일 업로드

```bash
curl -X PUT "https://awf-gw.adot.ai/v1/stt/upload/$TOKEN" \
  -H "X-API-Key: $SKT_A_X_API_KEY" \
  -H "Content-Type: application/octet-stream" \
  --data-binary @"$FILE"
```

응답의 `file_key`를 transcript 요청에 사용한다. `file_key`는 인식 요청 1회 후 만료될 수 있으므로 재요청 시 재업로드가 필요할 수 있다.

### 6.4 transcript 요청

```bash
curl -X POST https://awf-gw.adot.ai/v1/stt/transcript \
  -H "X-API-Key: $SKT_A_X_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "message_id": "intake-audio-001",
    "speech_model": "A.X_STT_note_batch",
    "audio_file_key": "'"$FILE_KEY"'",
    "keywords": ["우울감", "불면", "불안"],
    "agreement_of_data_collection": false
  }'
```

### 6.5 응답 활용

Batch 응답에서는 다음 필드를 중심으로 사용한다.

| 필드 | 용도 |
|---|---|
| `utterances[].text` | 발화 단위 변환 텍스트 |
| `utterances[].start_time` | 발화 시작 시점 |
| `utterances[].end_time` | 발화 종료 시점 |
| `words[].text` | 단어 단위 텍스트 |
| `words[].speaker` | 화자 구분 index |
| `message_id` | 클라이언트 요청 식별자 |

상담 녹취/회의록처럼 여러 사람이 말하는 오디오에는 Batch가 Streaming보다 적합하다.


### 6.6 Batch 선택 필드와 제한

| 필드 | 설명 |
|---|---|
| `callback_url` | 비동기 결과 수신 URL. 사용 전 운영팀 사전 협의 필요 |
| `keywords` | 도메인 특화 용어 word boosting |
| `agreement_of_data_collection` | 음성 데이터 수집 동의 관련 필드 |

- 파일당 최대 100MB 또는 30분이다.
- `callback_url` 미설정 시 결과는 요청 응답으로 동기 수신한다.
- 앱의 음성 민감정보 동의와 `agreement_of_data_collection`은 동일한 동의로 간주하지 않고 별도 관리한다.

### 6.7 STT confidence 처리 정정

현재 A.X STT 공식 응답 예시와 필드 표에는 일반적인 `confidence` 점수가 문서화되어 있지 않다. 따라서 Neuro-Sync의 `confidence < 0.6` 분기를 A.X STT에 그대로 적용하면 안 된다. Adapter에서는 `confidence: float | None`으로 두고, 값이 없으면 빈 transcript, VAD 대비 final 부재, 오디오 포맷 불일치, 사용자 수정/재입력 요청 등의 규칙으로 품질을 판단한다. 임의 confidence를 생성하지 않는다.

## 7. Neuro-Sync 적용 설계

### 7.1 문진 챗봇 LLM

```text
Client
  -> Backend /api/v1/sessions/:sessionId/chat
  -> Safety Guard
  -> Session Memory Builder
  -> A.X K1 LLM API
  -> Response Validator
  -> DB messages 저장
  -> Client
```

권장 기본값:

```json
{
  "model": "A.X-K1",
  "temperature": 0.0,
  "max_tokens": 512,
  "chat_template_kwargs": {
    "enable_thinking": false
  }
}
```

문진 Agent system prompt에는 반드시 다음 원칙을 넣는다.

- 진단명 단정 금지
- 처방/복약 변경 지시 금지
- 한 번에 한 가지 후속 질문
- 제공된 정보만 사용
- 위험 발화 시 일반 문진 중단

### 7.2 Push-to-Talk STT

```text
1. 사용자가 마이크 버튼을 누름
2. 앱이 16kHz mono PCM 또는 Opus로 녹음
3. Backend STT Adapter가 A.X STT Streaming 연결
4. partial transcript는 UI preview로 표시
5. final transcript를 입력창에 채움
6. 사용자가 수정 가능
7. 사용자가 전송 버튼 클릭
8. 그때 LLM/Safety Guard로 전달
```

중요: STT 결과를 자동으로 LLM에 전송하지 않는다. PRD의 FR-035에 따라 사용자가 확인/수정 후 명시적으로 전송해야 한다.

### 7.3 STT Adapter 인터페이스

Neuro-Sync에서는 벤더 교체를 고려해 다음 형태의 adapter로 감싼다.

```python
class STTResult:
    text: str
    confidence: float | None
    latency_ms: int
    vendor: str
    raw: dict

class STTAdapter:
    async def transcribe_streaming(self, audio_stream, *, session_id: str) -> STTResult:
        ...

    async def transcribe_file(self, audio: bytes, *, filename: str) -> STTResult:
        ...
```

Primary/Fallback 운영:

```text
STT_PRIMARY=skt_a_x
STT_FALLBACK=whisper
```

실패 조건:

- STT API 5xx
- timeout
- transcript 빈 문자열
- confidence가 제공되고 임계값 미만
- WebSocket 연결 실패
- 파일 업로드 실패

실패 시 텍스트 입력 모드로 폴백하고 재발화 안내를 표시한다.

## 8. 에러 처리

### 8.1 LLM

| HTTP status | 의미 | 처리 |
|---|---|---|
| 400 | 요청 형식 오류 | payload/schema 확인 |
| 401 | 인증 실패 | API Key, Bearer prefix 확인 |
| 404 | endpoint/model 오류 | URL, model 확인 |
| 429 | Rate limit 초과 | 지수 백오프, 큐잉 |
| 503 | 서비스 점검/장애 | 재시도 또는 fallback |
| 504 | Gateway Timeout | 지수 백오프 재시도 |

### 8.2 STT

| 에러 | 의미 | 처리 |
|---|---|---|
| 401 | 인증 실패 | `X-API-Key` 확인 |
| WebSocket disconnected | 연결 종료 | reconnect 또는 텍스트 입력 폴백 |
| `code 4001` | audio frame이 JSON text가 아님 | base64 JSON 전송으로 수정 |
| 404 | upload token/file key 만료 | token 재발급 후 재업로드 |
| 413 | 파일 크기 초과 | 파일 분할/압축 |
| 빈 transcript | 침묵/잡음/포맷 오류 | 재발화 안내 |

## 9. 보안 / 개인정보 주의

- API Key는 프론트엔드/모바일 앱에 직접 포함하지 않는다.
- 모든 외부 API 호출은 백엔드에서 수행한다.
- 환자 음성/텍스트는 민감정보로 보고 암호화 저장한다.
- STT 결과는 자동 전송하지 않고 사용자 편집/확인 단계를 둔다.
- 원본 오디오는 PRD 정책에 따라 단기 보존 후 삭제한다.
- 외부 STT/LLM 사용은 위탁/국외이전/재위탁 여부 검토가 필요하다.

## 10. 테스트 체크리스트

### LLM

- [ ] `.env`의 `SKT_A_X_API_KEY`로 단일 호출 성공
- [ ] `messages` history 포함 시 이전 대화 기억
- [ ] history 미포함 시 이전 대화 모름
- [ ] 프롬프트 기반 JSON 출력 + Pydantic validation 안정성
- [ ] streaming 응답 수신
- [ ] RPS 3 초과 시 429 처리
- [ ] 의료 안전 system prompt 준수

### STT

- [ ] Batch upload-token 발급
- [ ] Batch 파일 업로드 후 `file_key` 수신
- [ ] Batch transcript 요청 성공
- [ ] Streaming `create` 성공
- [ ] Streaming base64 audio 전송
- [ ] partial/final transcript 수신
- [ ] `stop` 후 `stopped` 수신
- [ ] 무음/잡음/실패 시 텍스트 입력 폴백
- [ ] STT 결과가 자동 전송되지 않고 입력창에만 채워짐

## 11. 다른 LLM API와 비교

| 항목 | SKT A.X K1 | Upstage Solar | EXAONE/Friendli |
|---|---|---|---|
| Chat API 형식 | OpenAI Chat Completions 호환 | Chat Completions | OpenAI 호환 Dedicated Chat Completions |
| 모델 지정 | `A.X-K1` | `solar-pro3` 등 | Dedicated endpoint ID |
| 이전 대화 기억 | 앱이 `messages`로 재전송 | 앱이 `messages`로 재전송 | 앱이 `messages`로 재전송 |
| STT | 제공 | 별도 확인 필요 | Friendli/EXAONE 자체 STT 아님 |
| 인증 | LLM Bearer, STT X-API-Key | Bearer | Bearer |
| 특징 | 경진대회 전용 LLM + STT, 종료 예정 | 문서/Agent/RAG 기능 강함 | Dedicated endpoint/격리 운영 |

## 12. 최종 검증 결론

Neuro-Sync에서 SKT A.X API는 합성 데이터 기반 PoC와 비교 평가 목적으로 두 용도를 우선 검토할 수 있다. 현재 경진대회 전용 endpoint와 로그 이용 조건을 고려하면, 법무·위탁 검토 전 실제 환자 데이터를 전송하는 운영 Primary로 확정해서는 안 된다.

1. **문진 챗봇 LLM 후보**
   - A.X K1을 Chat Completions 호환으로 호출
   - `messages` 기반 멀티턴 memory 구현
   - Safety Guard와 Response Validator를 별도 유지

2. **음성 문진 STT primary 후보**
   - Push-to-Talk은 Streaming API 사용
   - 녹음 파일/상담 녹취는 Batch API 사용
   - STT 결과는 자동 전송하지 않고 사용자 확인 후 LLM으로 전달



## 13. 권장 배치

```text
Agent/Chat Primary: Upstage Solar
LLM 비교 평가: A.X K1, EXAONE
STT PoC Primary: A.X STT
STT Fallback: Whisper
```

A.X K1과 A.X STT는 종료 예정일과 데이터 처리 조건을 재확인한 뒤 장기 운영 여부를 결정한다.
