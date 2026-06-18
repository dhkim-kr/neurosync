# STT Specification

> **Version**: 1.0
> **Created**: 2026-06-15
> **Source PRD**: `docs/ai/PRD_ai_v.0.0.0.0.md` section 6.5 (FR-033/035/037)
> **Source API**: `docs/ai/api/SKT_A_X_API.md` sections 4-6
> **Status**: Implementation-Ready

---

## 1. Primary Vendor: SKT A.X STT

Neuro-Sync uses **SKT A.X STT** as the primary speech-to-text service for patient voice input during pre-consultation intake (PRD section 3.1). The STT is a fixed-vendor agent -- it is not subject to the benchmark-based model selection process used for LLM agents.

| Property | Value |
|---|---|
| Vendor | SKT A.X (via adot.ai portal) |
| Agent | `SttAgent` |
| Adapter | `SktAkSttAdapter` |
| Model Policy | Fixed (not benchmarked) |
| Streaming Model | `A.X_STT_note_streaming` |
| Batch Model | `A.X_STT_note_batch` |
| Primary Use Case | Push-to-Talk pre-consultation voice input |

### Service Availability Warning

Per SKT A.X API documentation: the A.X STT service is designated for a national AI competition and has a scheduled end date of 2026-11-23. The system is designed with an Adapter abstraction layer so the underlying vendor can be replaced without changing the agent interface.

---

## 2. Two Modes: Streaming and Batch

SKT A.X STT provides two distinct APIs (API doc section 4.2).

### 2.1 Streaming Mode (WebSocket)

For real-time Push-to-Talk voice input during intake.

| Property | Value |
|---|---|
| Protocol | WebSocket |
| Endpoint | `wss://awf-gw.adot.ai/v1/stt/realtime` |
| Model | `A.X_STT_note_streaming` |
| Input | Base64-encoded audio chunks via JSON messages |
| Output | Intermediate (`final=false`) and final (`final=true`) transcript results |
| Speaker Diarization | Not supported |
| Latency | Real-time (intermediate results stream as audio is received) |

**Flow**:

```
1. Open WebSocket connection
2. Send "create" message (speech_model, audio_format, vad_type, tr_id)
3. Receive "created" acknowledgment
4. Send "audio" messages with base64 chunks (recommended: 100ms chunks)
5. Receive "vad" events (bos/eos detection) and "transcript" results
6. Send "stop" when audio ends
7. Receive "stopped" confirmation
```

**Audio transmission**: Audio is sent as base64-encoded JSON, not binary WebSocket frames.

```json
{
  "message_type": "audio",
  "data": "<base64 encoded audio chunk>"
}
```

**Keepalive**: During silent periods, send `keepalive` messages within 30 seconds. WebSocket ping/pong alone may not be sufficient.

**Transcript response**:

```json
{
  "message_type": "transcript",
  "text": "요즘 잠을 거의 못 자요",
  "created": "2026-05-18 10:00:00",
  "start_time": 0.5,
  "end_time": 2.7,
  "final": true,
  "words": [
    { "text": "요즘", "start_time": 0.5, "end_time": 0.9 }
  ],
  "tr_id": "intake-session-001"
}
```

### 2.2 Batch Mode (REST)

For processing recorded audio files (e.g., therapy recordings, uploaded voice memos).

| Property | Value |
|---|---|
| Protocol | REST (3-step) |
| Model | `A.X_STT_note_batch` |
| Speaker Diarization | Supported (`words[].speaker` field) |
| Max File Size | 100MB or 30 minutes |

**3-Step Flow**:

```
Step 1: Get upload token
  GET https://awf-gw.adot.ai/v1/stt/upload-token?fileSize={SIZE}
  -> Returns upload_token + expire_at

Step 2: Upload audio file
  PUT https://awf-gw.adot.ai/v1/stt/upload/{upload_token}
  Content-Type: application/octet-stream
  -> Returns file_key

Step 3: Request transcript
  POST https://awf-gw.adot.ai/v1/stt/transcript
  Body: { message_id, speech_model, audio_file_key, keywords, agreement_of_data_collection }
  -> Returns utterances with text, timestamps, speaker labels
```

**Important**: `fileSize` in Step 1 must exactly match the actual uploaded file size. `upload_token` expires. `file_key` may expire after one transcript request. Re-upload may be needed for retry.

---

## 3. Authentication

STT authentication uses `X-API-Key` header -- this is **different from the LLM API** which uses `Authorization: Bearer`.

| API | Auth Header |
|---|---|
| A.X K1 LLM | `Authorization: Bearer $SKT_A_X_API_KEY` |
| A.X STT | `X-API-Key: $SKT_A_X_API_KEY` |

The same API key value is used for both, but the header name and format differ. This is a common integration error point.

```
# Correct for STT
X-API-Key: $SKT_A_X_API_KEY

# WRONG for STT (this is the LLM format)
Authorization: Bearer $SKT_A_X_API_KEY
```

API keys are stored in environment variables only. Never in source code, documentation, or commit history.

---

## 4. Audio Formats

Supported audio formats for the Streaming API `create` message (API doc section 5.2):

| Format | Description |
|---|---|
| `pcm_8k` | Raw PCM, 8kHz sample rate |
| `pcm_16k` | Raw PCM, 16kHz sample rate |
| `speex_16k` | Speex codec, 16kHz |
| `opus_16k` | Opus codec, 16kHz |

### Recommended Configuration for Neuro-Sync

| Setting | Value | Rationale |
|---|---|---|
| Format | `pcm_16k` or `opus_16k` | 16kHz mono provides good quality for speech. Opus reduces bandwidth for mobile. |
| Chunk size | 100ms | Recommended range is 20-400ms. 100ms balances latency and overhead for Push-to-Talk. |
| VAD type | `semantic` | Semantic VAD for sentence-level segmentation |
| Partial results | `true` | Show intermediate transcript in UI preview |

### MVP Input Format

Per PRD STT-2: The exact input format (wav/m4a) is finalized based on the mobile app recording format. The adapter accepts `audio_bytes` and handles format negotiation internally.

### MVP Audio Length

Per PRD STT-3: MVP supports push-to-talk recordings of 60 seconds or less.

---

## 5. Confidence Handling

### Critical Note: A.X STT Provides No Confidence Score

Per API documentation section 6.7:

> The A.X STT official response examples and field tables do not document a `confidence` score. Neuro-Sync's `confidence < 0.6` branching logic CANNOT be directly applied to A.X STT output. The adapter must use `confidence: float | None` and never fabricate a confidence value.

This is a known deviation from the PRD's ideal STT output schema (which includes `confidence: 0.86`). The adapter handles this by inferring quality from indirect signals.

### Quality Inference Rules (No Confidence Available)

Since A.X STT does not provide a numeric confidence score, the `SktAkSttAdapter` infers transcript quality from observable signals:

| Signal | Interpretation | Action |
|---|---|---|
| Empty transcript text | No speech detected, noise only, or format mismatch | Treat as low quality. Prompt user to re-record or type. |
| VAD events but no final transcript | Audio detected but speech recognition failed | Treat as low quality. Prompt re-recording. |
| Audio format mismatch | Format not in supported list | Reject immediately. Request supported format. |
| User requests re-recording | Implicit quality signal | Allow re-recording. |
| Very short transcript vs long audio | Possible partial recognition failure | Flag for user review. |

### Adapter Confidence Field

```python
class SttResult:
    text: str
    confidence: float | None  # None when vendor does not provide it
    latency_ms: int
    vendor: str
    raw: dict
```

When `confidence` is `None`:
- The adapter does NOT generate a synthetic confidence value.
- Low-confidence span highlighting in the mobile UI is based on the indirect signals above, not a numeric threshold.
- Downstream agents treat `confidence=None` as "unknown quality" and set `requires_user_confirmation=True`.

---

## 6. Fallback Chain

```
SKT A.X STT (primary)
  |
  ├── Success -> Return transcript
  |
  v (failure)
Typed input fallback
  |
  -> Prompt user to type their response instead of speaking
  -> Display: "음성 인식이 어려운 상황입니다. 텍스트로 입력해 주세요."
```

### No Whisper in Current Vendor Set

The current vendor configuration does not include Whisper or any secondary STT service. The fallback is typed text input, not another STT vendor. The adapter interface supports a fallback STT vendor for future addition:

```
STT_PRIMARY=skt_a_x
STT_FALLBACK=typed_input  # No secondary STT vendor currently
```

### Failure Conditions

| Condition | Detection | Fallback Action |
|---|---|---|
| STT API 5xx | HTTP status code | Typed input fallback |
| Timeout (>15s default) | Adapter timeout | Typed input fallback |
| Empty transcript | `text == ""` | Prompt re-recording. If second attempt fails, typed input. |
| WebSocket connection failure | Connection error | Typed input fallback |
| File upload failure (Batch) | Upload error | Typed input fallback |
| Authentication failure (401) | HTTP status code | Log error. Typed input fallback. Alert ops. |

### Error Responses for STT (from API doc section 8.2)

| Error | Meaning | Handling |
|---|---|---|
| 401 | Auth failure | Check `X-API-Key` header (not Bearer) |
| WebSocket disconnected | Connection dropped | Reconnect or typed input fallback |
| Code 4001 | Audio frame is not JSON text | Fix to base64 JSON format |
| 404 | Upload token/file key expired | Re-issue token and re-upload |
| 413 | File too large | Split or compress file |
| Empty transcript | Silence/noise/format error | Prompt re-recording |

---

## 7. FR-035: STT Results Are Never Auto-Sent to LLM

This is a critical safety and accuracy requirement from the PRD (FR-035, reiterated in API doc section 7.2).

### Rule

> STT transcript output is NEVER automatically forwarded to the LLM/Safety Guard pipeline. The user must explicitly confirm or edit the transcript before it enters the dialogue pipeline.

### Flow

```
1. User presses microphone button
2. App records audio (16kHz mono PCM or Opus)
3. Backend STT Adapter connects to A.X STT Streaming
4. Partial transcript is displayed as UI preview (read-only indicator)
5. Final transcript is placed in the input field (editable)
6. User reviews, edits if needed
7. User presses send button
8. ONLY THEN does the text enter Safety Guard -> Orchestrator -> Dialogue pipeline
```

### Rationale

- STT errors in medical context can change clinical meaning (e.g., "약을 안 먹었어요" vs "약을 먹었어요").
- Without a confidence score from A.X STT, the system cannot programmatically determine transcript accuracy.
- User confirmation serves as the quality gate that replaces the missing confidence score.
- This also respects patient autonomy: the patient controls what text is submitted as their input.

### Implementation Contract

The mobile app must:
1. Display the STT transcript in an editable text field.
2. NOT have an auto-send feature that bypasses user confirmation.
3. Show a clear "send" button that the user must actively press.
4. Store both the original STT transcript and the user-edited version separately.

---

## 8. 48-Hour Audio Deletion (FR-036)

### Rule

Original audio recordings are retained for a maximum of 48 hours after STT processing, then permanently deleted.

### Policy (from PRD section 12.2)

| Data | Retention | Notes |
|---|---|---|
| Original audio file | 48 hours or less | Deleted after STT confirmation/review window |
| STT transcript (original) | Service retention period | Stored separately from user-edited version |
| STT transcript (user-edited) | Service retention period | Canonical text used in dialogue pipeline |
| STT metadata (latency, vendor, format) | Long-term | No PHI content |

### Deletion Flow

```
1. Audio uploaded -> stored in encrypted object storage
2. STT processing completes
3. User confirms/edits transcript
4. 48-hour retention timer starts
5. After 48 hours: audio file permanently deleted from object storage
6. Deletion logged in audit trail
```

### Rationale

- Audio is the highest-sensitivity PHI (contains voice biometrics, emotional state, potentially identifiable information).
- Once the transcript is confirmed by the user, the audio serves no further purpose.
- 48 hours provides a buffer for re-processing if STT issues are discovered.
- This policy aligns with data minimization principles for mental health data.

---

## 9. Adapter Interface

The `SktAkSttAdapter` implements the common `VendorAdapter` interface (PRD section 8.3).

```python
class SktAkSttAdapter(VendorAdapter):
    name = "skt-ak-stt"

    async def transcribe(
        self,
        audio_bytes: bytes,
        language: str = "ko-KR",
        context_hint: str | None = None,
        enable_timestamps: bool = True,
        timeout_s: int = 15,
    ) -> SttResult:
        """
        Primary transcription method.
        Routes to streaming or batch based on audio size and use case.
        """
        ...
```

### Higher-Level STT Adapter

For vendor-agnostic usage:

```python
class STTResult:
    text: str
    confidence: float | None    # None when vendor does not provide it
    latency_ms: int
    vendor: str
    raw: dict                   # Vendor-specific raw response

class STTAdapter:
    async def transcribe_streaming(
        self, audio_stream, *, session_id: str
    ) -> STTResult:
        """Real-time Push-to-Talk transcription via WebSocket."""
        ...

    async def transcribe_file(
        self, audio: bytes, *, filename: str
    ) -> STTResult:
        """Batch file transcription via 3-step REST."""
        ...
```

---

## 10. Word Boosting (Domain Keywords)

A.X STT supports `keywords` for word boosting -- improving recognition of domain-specific terms.

### Recommended Keywords for Mental Health Intake

```json
{
  "keywords": [
    "우울감", "불면", "불안", "공황",
    "자해", "자살", "환청", "환각",
    "약물", "수면제", "항우울제", "항불안제",
    "PHQ", "GAD", "BDI",
    "정신건강의학과", "심리상담"
  ]
}
```

These are passed in the `create` message (Streaming) or `transcript` request (Batch) to improve recognition accuracy for clinical terminology.

---

## 11. Data Collection Consent

Both Streaming and Batch APIs include an `agreement_of_data_collection` field related to SKT's audio data collection for model improvement.

### Neuro-Sync Policy

- The app's patient consent for AI processing and SKT's `agreement_of_data_collection` are managed as **separate consents** (API doc section 6.6).
- Mental health voice data is high-sensitivity PHI. Default `agreement_of_data_collection` to `false` unless explicit separate consent is obtained.
- No real patient audio is sent to SKT A.X until legal/privacy review confirms the data processing terms are acceptable.

---

## 12. Performance Targets

| Metric | Target | Source |
|---|---|---|
| STT latency p95 | < 2,000ms | PRD section 14 |
| Push-to-Talk max duration (MVP) | 60 seconds | PRD STT-3 |
| Audio deletion | <= 48 hours | PRD section 12.2 |
| Transcript user confirmation | Required before LLM | FR-035 |

---

## 13. Acceptance Criteria (from PRD)

| Given | When | Then |
|---|---|---|
| User describes symptoms via voice | STT completes | Transcript and timestamps are returned |
| Low-quality audio or silence | STT returns empty text | User is prompted to re-record or type |
| STT times out | API response | Typed input fallback message is returned |
| User edits transcript | Before sending | Edited version is stored as canonical text; original STT output is stored separately |
| 48 hours after STT confirmation | Retention check | Original audio file is permanently deleted |
| STT result returned | Before dialogue processing | Text is NOT auto-sent to LLM. User must press send. |
