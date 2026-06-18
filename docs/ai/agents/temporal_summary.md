# TemporalSummaryAgent

> **Role**: Generate longitudinal delta summaries comparing current vs. past patient state
> **Model Policy**: Benchmarked (Solar Pro 3 / K-EXAONE / A.K)
> **System Prompt**: `docs/ai/prompts/temporal_summary/v1.system.md`
> **Implementation**: `apps/ai-server/src/agents/temporal_summary.py`

## Input

| Field | Type | Required | Description |
|---|---|---|---|
| evidence_packets | list[object] | Yes | Temporal evidence packets from TemporalRetrieverAgent, each with `evidence_id`, `source_type`, `source_id`, `timestamp`, `content`, `metadata`, `retrieval_score` |

## Output

| Field | Type | Description |
|---|---|---|
| deltas | list[object] | Per-domain change assessments, each with `domain` (e.g., sleep, mood, anxiety), `status` (one of: `improved`, `worsened`, `unchanged`, `unknown`), `evidence_ids`, `summary` |
| overall_trajectory | string | One of: `improved`, `worsened`, `unchanged`, `mixed`, `unknown` |
| contradictions | list[object] | Detected contradictions between past and current evidence, each with `domain`, `past_evidence_id`, `current_evidence_id`, `description` |

## Behavior

1. Receive evidence packets spanning multiple sessions and time periods.
2. Group evidence by clinical domain (sleep, appetite, mood, anxiety, concentration, functional impairment, medication, risk).
3. For each domain, compare the most recent evidence against historical baselines.
4. Classify each domain's trajectory as `improved`, `worsened`, `unchanged`, or `unknown`.
5. Detect contradictions between past and current evidence (e.g., patient previously reported improvement but now reports worsening).
6. Mark domains with insufficient evidence as `unknown` rather than making unsupported claims.
7. Attach evidence IDs to every delta claim for traceability.

## Safety Constraints

- Must never assert a change direction without supporting evidence (every delta must have evidence IDs).
- Must mark insufficient-evidence domains as `unknown` rather than guessing.
- Must flag contradictions explicitly rather than silently resolving them.
- Must never produce diagnostic conclusions from temporal trends.
- Must not log PHI summary content; only metadata and hashes are stored.

## Failure Fallback

When the Temporal Summary LLM fails (timeout, invalid response, 5xx):
- Return all domains as `unknown` with a **judgment-unavailable flag**.
- The HandoffGeneratorAgent proceeds with current-session data only, noting that longitudinal comparison was unavailable.
- Log the failure with `agent_trace_id`, `model_used`, and `latency_ms`.

## Model Selection

ModelRouter queries `agent_model_registry` for `agent_name=temporal_summary`. Selection criteria:
- **Priority metrics**: Delta factuality, temporal consistency.
- Candidates: Solar Pro 3, K-EXAONE, A.K.
- Fallback chain: timeout / 429 / 5xx / invalid JSON triggers secondary model or unknown-flag fallback.

## Dependencies

- **TemporalRetrieverAgent**: Provides the evidence packets as input.
- **ModelRouter**: Selects the model for delta summarization.
- **HandoffGeneratorAgent**: Consumes delta summaries for the Longitudinal Delta section of the Handoff Report.
- **EvidenceVerifierAgent**: Verifies that delta claims are properly evidence-grounded.
