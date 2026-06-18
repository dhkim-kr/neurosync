# SafetyClassifierAgent

> **Role**: Classify patient messages for suicide, self-harm, harm-to-others, and acute crisis risk
> **Model Policy**: Benchmarked (Solar Pro 3 / K-EXAONE / A.K) + Rule Ensemble
> **System Prompt**: `docs/ai/prompts/safety_classifier/v1.system.md`
> **Implementation**: `apps/ai-server/src/agents/safety_classifier.py`

## Input

| Field | Type | Required | Description |
|---|---|---|---|
| latest_message | string | Yes | The most recent patient message (normalized) |
| recent_context | list[object] | Yes | Recent conversation turns for contextual risk assessment |

## Output

| Field | Type | Description |
|---|---|---|
| risk_level | string | One of: `none`, `low`, `medium`, `high`, `critical` |
| risk_categories | list[string] | Detected risk categories (e.g., `suicidal_ideation`, `self_harm`, `harm_to_others`, `acute_psychosis`) |
| evidence | list[string] | Verbatim phrases from the message that triggered the classification |
| confidence | float | Classification confidence (0.0 - 1.0) |
| recommended_action | string | One of: `continue`, `ask_safety_question`, `interrupt_and_route_to_crisis_help` |
| user_safe_message_template_id | string | Template ID for the safe response message (e.g., `kr_crisis_109_v1`) |
| requires_human_review | bool | Whether clinician review is needed (low confidence or model disagreement) |
| model_used | string | Model that produced the classification |

## Behavior

1. Receive the latest patient message and recent conversation context.
2. Run two classifiers **in parallel**:
   - **Rule/Keyword Detector**: Pattern-based detection of known crisis keywords and phrases.
   - **LLM Safety Classifier**: Context-aware risk classification using the benchmarked model.
3. Merge results via **Risk Merger**:
   - If Rule detector flags risk but LLM says safe, apply **danger-priority policy** (escalate to medium or higher).
   - Take the higher risk level between the two classifiers.
4. Determine the recommended action based on risk level:
   - `none` / `low`: Continue normal dialogue.
   - `medium`: Generate a safety check question and store a risk event.
   - `high` / `critical`: Interrupt normal response, provide 119/109 crisis resource info, flag on clinician dashboard.
5. If confidence is low or model disagreement exists, set `requires_human_review = true`.

## Safety Constraints

- Must never classify a genuinely dangerous message as `none` or `low` (recall for high/critical >= 95%).
- Must never allow normal DialogueAgent response generation when risk is `high` or `critical`.
- Must always apply danger-priority policy when Rule and LLM disagree.
- Must store all safety classification results in `risk_events` for audit.
- Safety prompt changes must pass red-team regression tests before deployment.

## Failure Fallback

When the Safety LLM fails (timeout, invalid response, 5xx):
- Apply **emergency-safe default**: Treat the message as potentially dangerous.
- Set `risk_level = medium`, `recommended_action = ask_safety_question`, `requires_human_review = true`.
- The Rule/Keyword Detector result is used as the sole classifier.
- Log the failure and trigger an alert.

## Model Selection

ModelRouter queries `agent_model_registry` for `agent_name=safety_classifier`. Selection criteria:
- **Priority metric**: `recall_high_critical` (minimum threshold: 0.95).
- Candidates: Solar Pro 3, K-EXAONE, A.K (each evaluated on red-team safety dataset).
- The model with the highest high/critical recall is selected as Primary.
- Fallback chain: timeout / 429 / 5xx / safety_uncertain triggers emergency-safe default.

## Dependencies

- **InputNormalizerAgent**: Provides normalized text as input.
- **Rule/Keyword Detector**: Internal module for pattern-based risk detection.
- **ModelRouter**: Selects the LLM model for classification.
- **OrchestratorAgent**: Consumes the `risk_state` output for routing decisions.
- **DialogueAgent**: Blocked when risk is high/critical.
