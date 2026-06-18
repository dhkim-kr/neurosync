# InputNormalizerAgent

> **Role**: Normalize STT errors, typos, and ungrammatical text into clean input for downstream agents
> **Model Policy**: Benchmarked (Solar Pro 3 / K-EXAONE / A.K)
> **System Prompt**: `docs/ai/prompts/input_normalizer/v1.system.md`
> **Implementation**: `apps/ai-server/src/agents/input_normalizer.py`

## Input

| Field | Type | Required | Description |
|---|---|---|---|
| transcript | string | Yes | Raw transcript from SttAgent or user-typed text |
| source | string | No | Origin of the text: `stt` or `typed` |

## Output

| Field | Type | Description |
|---|---|---|
| normalized_text | string | Cleaned and normalized text ready for downstream processing |
| uncertainty_spans | list[object] | Spans where normalization confidence is low, each with `start`, `end`, `original`, `normalized`, `confidence` |

## Behavior

1. Receive raw transcript (from STT) or user-typed text.
2. Apply Korean colloquial speech normalization (e.g., filler removal, sentence boundary detection).
3. Correct STT-specific errors: misheard syllables, word boundary errors, medical/mental health terminology corrections.
4. Fix common typos and ungrammatical fragments while preserving the patient's original meaning.
5. Identify spans where the normalization is uncertain and mark them with confidence scores.
6. Return normalized text and uncertainty spans for downstream agents.

## Safety Constraints

- Must never alter the semantic meaning of the patient's statement during normalization.
- Must never remove or downplay safety-critical expressions (e.g., suicidal ideation phrasing must be preserved even if grammatically incorrect).
- Must not fabricate words or phrases that the patient did not express.
- Must not log PHI content; only metadata and hashes are stored.

## Failure Fallback

When the normalization LLM fails (timeout, invalid response, 5xx):
- **Preserve the original text as-is** and attach a flag indicating normalization was skipped.
- Downstream agents process the raw text with reduced confidence.
- Log the failure with `agent_trace_id`, `model_used`, and `latency_ms`.

## Model Selection

ModelRouter queries `agent_model_registry` for `agent_name=input_normalizer`. Selection criteria:
- **Priority metrics**: STT noise correction accuracy, latency.
- Candidates: Solar Pro 3, K-EXAONE, A.K.
- Fallback chain: timeout / 429 / 5xx / invalid JSON triggers secondary model or raw-text passthrough.

## Dependencies

- **SttAgent**: Provides raw transcript when input is voice-based.
- **ModelRouter**: Selects the model for normalization.
- **SafetyClassifierAgent**: Downstream consumer; receives normalized text.
- **DialogueAgent**: Downstream consumer; receives normalized text.
