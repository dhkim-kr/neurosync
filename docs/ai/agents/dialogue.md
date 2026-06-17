# DialogueAgent

> **Role**: Generate safe pre-intake dialogue responses and slot-filling questions for patients
> **Model Policy**: Benchmarked (Solar Pro 3 / K-EXAONE / A.K)
> **System Prompt**: `docs/ai/prompts/dialogue/v1.system.md`
> **Implementation**: `apps/ai-server/src/agents/dialogue.py`

## Input

| Field | Type | Required | Description |
|---|---|---|---|
| normalized_text | string | Yes | Patient message after normalization |
| missing_slots | list[string] | Yes | Clinical slots that still need to be filled |
| context | object | Yes | Session context including past turns, filled slots, risk state, patient profile |

## Output

| Field | Type | Description |
|---|---|---|
| assistant_response | string | The generated dialogue response text for the patient |
| slot_updates | object | Key-value pairs of clinical slots extracted or updated from this turn |
| risk_level | string | Risk level echoed from the safety gate (for traceability) |
| model_used | string | Model that generated the response |
| prompt_version | string | Prompt version used (e.g., `dialogue_intake.v1`) |
| requires_human_review | bool | Whether the response needs clinician review |

## Behavior

1. Receive normalized patient text, list of missing clinical slots, and session context.
2. Verify that the Safety Gate has already been passed for this message (never generate a response without safety clearance).
3. Analyze the patient's statement to extract any clinical slot information mentioned.
4. Generate a single follow-up question targeting the most relevant missing slot.
5. Ensure the response does not repeat questions about information the patient already provided.
6. Return the assistant response text and any slot updates as separate fields.

## Safety Constraints

- Must never generate a response if the Safety Gate has not cleared the message.
- Must include exactly one question per response (no multi-question responses).
- Must never fabricate medical facts not present in the patient's statements.
- Must never produce diagnostic assertions, treatment recommendations, or medication adjustment language.
- Must refuse diagnostic requests and route the patient to clinician consultation.
- Must not log PHI response content; only metadata and hashes are stored.

## Failure Fallback

When the Dialogue LLM fails (timeout, invalid JSON, 5xx):
- Fall back to a **template-based question** selected from the missing slots list.
- The template response is safe and generic (e.g., "Could you tell me more about when this started?").
- Retry with secondary model if available via ModelRouter fallback chain.
- Log the failure with `agent_trace_id`, `model_used`, and `latency_ms`.

## Model Selection

ModelRouter queries `agent_model_registry` for `agent_name=dialogue`. Selection criteria:
- **Priority metrics**: Korean naturalness, safety score, slot completion rate.
- Candidates: Solar Pro 3, K-EXAONE, A.K.
- Minimum threshold: clinician/user safety score >= 4.0.
- Fallback chain: timeout / 429 / 5xx / invalid JSON triggers secondary model or template fallback.

## Dependencies

- **SafetyClassifierAgent**: Must clear the message before DialogueAgent runs.
- **InputNormalizerAgent**: Provides normalized text input.
- **ClinicalSlotAgent**: Consumes slot updates; provides missing slots list.
- **OrchestratorAgent**: Routes to DialogueAgent based on workflow state.
- **ModelRouter**: Selects the model for dialogue generation.
