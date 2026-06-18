# OrchestratorAgent

> **Role**: Workflow routing, tool call planning, and state transitions across the multi-agent pipeline
> **Model Policy**: Benchmarked (Solar Pro 3 / K-EXAONE / A.K)
> **System Prompt**: `docs/ai/prompts/orchestrator/v1.system.md`
> **Implementation**: `apps/ai-server/src/agents/orchestrator.py`

## Input

| Field | Type | Required | Description |
|---|---|---|---|
| user_intent | string | Yes | Parsed user intent from the current message |
| session_state | object | Yes | Current session state including completed slots, turn count, phase |
| risk_state | object | Yes | Latest risk classification result from SafetyClassifierAgent |

## Output

| Field | Type | Description |
|---|---|---|
| next_action | string | One of: `call_agent`, `ask_clarifying_question`, `interrupt_for_safety`, `generate_handoff`, `no_op` |
| required_agents | list[string] | Agent names to invoke next (e.g., `["safety_classifier", "temporal_retriever", "dialogue"]`) |
| confidence | float | Routing confidence score (0.0 - 1.0) |
| risk_gate_required | bool | Whether a safety gate check is required before proceeding |
| context_required | bool | Whether temporal/context retrieval is needed |
| selected_model | string | Resolved by ModelRouter at runtime |
| reason_summary | string | Policy-level short reason for the routing decision. No hidden reasoning exposed. |

## Behavior

1. Receive user intent, session state, and risk state from the AI runtime.
2. Determine the current phase of the patient intake workflow (safety check, dialogue, slot filling, handoff generation).
3. Decide which agents need to be called next based on session state and missing slots.
4. If `risk_state` indicates high/critical, route to `interrupt_for_safety` and block normal dialogue.
5. If all required slots are filled and handoff conditions are met, route to `generate_handoff`.
6. Return a structured JSON plan with the next action, required agents, and confidence.

## Safety Constraints

- Must always check `risk_state` before routing to any dialogue or slot extraction agent.
- Must never skip the safety gate for any user message.
- Must never expose raw chain-of-thought in `reason_summary`; only policy-level summaries are allowed.
- Must never hard-code model names; always delegate to ModelRouter.

## Failure Fallback

When the LLM-based orchestrator fails (timeout, invalid JSON, 5xx):
- Fall back to a **rule-based router** that uses session state and risk state to determine the next action deterministically.
- Log the failure with `agent_trace_id`, `model_used`, and `latency_ms`.

## Model Selection

ModelRouter queries `agent_model_registry` for `agent_name=orchestrator`. Selection criteria:
- **Priority metrics**: JSON reliability, routing accuracy, tool-use accuracy.
- Candidates: Solar Pro 3, K-EXAONE, A.K.
- If registry is empty, returns `eval-required` status and blocks deployment.
- Fallback chain: timeout / 429 / 5xx / invalid JSON triggers secondary model.

## Dependencies

- **SafetyClassifierAgent**: Provides `risk_state` input.
- **ModelRouter**: Selects the model for orchestration.
- **Context Gateway**: Provides session state and slot status.
- All downstream agents (DialogueAgent, ClinicalSlotAgent, TemporalRetrieverAgent, HandoffGeneratorAgent, EvidenceVerifierAgent) are invoked based on orchestrator output.
