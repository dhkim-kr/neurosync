# SttAgent

> **Role**: Convert patient voice input to text via SKT A.K STT
> **Model Policy**: Fixed (SKT A.K STT)
> **System Prompt**: `docs/ai/prompts/stt/v1.system.md`
> **Implementation**: `apps/ai-server/src/agents/stt.py`

## Input

| Field | Type | Required | Description |
|---|---|---|---|
| audio_bytes | bytes | Yes | Raw audio data from patient recording |
| language | string | No | Language code, defaults to `ko-KR` |
| context_hint | string | No | Optional context hint for improved accuracy (e.g., mental health domain) |
| enable_timestamps | bool | No | Whether to return segment-level timestamps, defaults to `true` |

## Output

| Field | Type | Description |
|---|---|---|
| text | string | Full transcript text |
| confidence | float | Overall transcription confidence (0.0 - 1.0) |
| vendor | string | Always `skt-ak-stt` |
| segments | list[object] | Segment-level data with `start_ms`, `end_ms`, `text` |
| low_confidence_spans | list[object] | Spans where confidence is below threshold, for UI highlighting |
| requires_user_confirmation | bool | Whether the transcript should be shown to the user for review |

## Behavior

1. Receive audio blob from the platform API gateway (via file token or presigned URL).
2. Validate input format (wav/m4a supported in MVP) and duration (max 60 seconds for push-to-talk).
3. Call `SktAkSttAdapter.transcribe()` with the audio bytes, language, and context hint.
4. Parse the vendor response into the standardized `SttResult` schema.
5. Identify low-confidence spans and mark them for user review.
6. Return transcript with confidence, timestamps, and low-confidence spans.
7. The transcript is presented to the user for confirmation/correction before proceeding to InputNormalizerAgent.

## Safety Constraints

- Must never store raw audio beyond the short-term retention policy.
- Must never send audio to the STT vendor without user consent for external AI API transmission.
- Must never treat the transcript as confirmed text until user review is complete.
- Must not log PHI-containing transcript content; only hash and metadata are stored.

## Failure Fallback

When STT fails (timeout, 429, 5xx, no speech detected, low overall confidence):
- Return a **typed input fallback** message prompting the user to type their response instead.
- If a local/offline STT fallback is available, attempt local transcription before falling back to typed input.
- Log failure reason with `agent_trace_id` and `latency_ms`.

## Model Selection

This agent uses a **fixed vendor**: SKT A.K STT. No ModelRouter selection is performed. The adapter endpoint and auth details are configured in the adapter layer and updated only when vendor contract changes.

## Dependencies

- **SktAkSttAdapter**: The vendor adapter that wraps the SKT A.K STT API.
- **InputNormalizerAgent**: Downstream consumer of the confirmed transcript.
- **Platform API Gateway**: Provides the audio file via secure token/presigned URL.
