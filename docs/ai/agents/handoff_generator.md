# HandoffGeneratorAgent

> **Role**: Generate evidence-grounded Handoff Reports for clinician pre-visit review
> **Model Policy**: Benchmarked (Solar Pro 3 / K-EXAONE / A.K)
> **System Prompt**: `docs/ai/prompts/handoff_generator/v1.system.md`
> **Implementation**: `apps/ai-server/src/agents/handoff_generator.py`

## Input

| Field | Type | Required | Description |
|---|---|---|---|
| slots | object | Yes | Structured clinical slots from ClinicalSlotAgent |
| risk | object | Yes | Risk assessment results from SafetyClassifierAgent |
| scales | object | No | PHQ-9/GAD-7 scores and severity |
| evidence | list[object] | Yes | Evidence packets from TemporalRetrieverAgent |

## Output

| Field | Type | Description |
|---|---|---|
| report_markdown | string | Full Handoff Report in Markdown format with all required sections |
| evidence_table | list[object] | Evidence references used in the report, each with `evidence_id`, `source_type`, `claim_text` |
| missing_information | list[string] | Clinical domains where information was not available |
| requires_human_review | bool | Whether any section contains low-confidence data needing clinician review |
| model_used | string | Model that generated the report |
| prompt_version | string | Prompt version used |

## Behavior

1. Receive structured clinical slots, risk assessment, scale scores, and evidence packets.
2. Generate a Handoff Report with the following **required sections**:
   1. One-line Summary
   2. Chief Complaint
   3. History of Present Illness
   4. Key Symptoms (sleep, appetite, mood, anxiety, concentration, functional impairment)
   5. PHQ-9 / GAD-7
   6. Risk & Safety Flags
   7. Medication / Past History / Uploaded Documents
   8. Longitudinal Delta
   9. Missing Information
   10. Evidence Table
   11. Clinician Review Required Flags
3. Attach evidence IDs (e.g., `[ev_msg_001, ev_scale_001]`) to every core claim in the report.
4. List all missing clinical domains in the Missing Information section.
5. Flag low-confidence OCR entities with `needs_review` annotations.
6. After generating the draft, **always invoke EvidenceVerifierAgent** for validation.

## Safety Constraints

- Every core claim in the report must have at least one evidence ID; unsupported claims are prohibited.
- Must never generate diagnostic assertions (e.g., "Patient has major depressive disorder").
- Must never include treatment recommendations, medication adjustments, or clinical directives.
- Must never fabricate information not present in patient messages, documents, or scale results.
- If EvidenceVerifierAgent finds unsupported claims, the report must be rejected or regenerated.
- Low-confidence OCR-sourced claims must be marked as `needs_review`.
- Must not log PHI report content; only metadata and hashes are stored.

## Failure Fallback

When the Handoff LLM fails (timeout, invalid JSON, 5xx):
- Generate a **partial report** containing only the sections for which structured data is available (slots, scales, risk flags).
- Mark the report as incomplete with `requires_human_review = true`.
- Retry with secondary model if available via ModelRouter fallback chain.
- Log the failure with `agent_trace_id`, `model_used`, and `latency_ms`.

## Model Selection

ModelRouter queries `agent_model_registry` for `agent_name=handoff_generator`. Selection criteria:
- **Priority metrics**: Unsupported claim count (lower is better), clinician satisfaction score.
- Candidates: Solar Pro 3, K-EXAONE, A.K.
- The model with the lowest unsupported claim rate and highest clinician score is selected as Primary.
- Fallback chain: timeout / 429 / 5xx / invalid JSON triggers secondary model or partial report.

## Dependencies

- **ClinicalSlotAgent**: Provides structured clinical slots.
- **SafetyClassifierAgent**: Provides risk assessment data.
- **TemporalRetrieverAgent**: Provides evidence packets.
- **TemporalSummaryAgent**: Provides longitudinal delta summaries.
- **EvidenceVerifierAgent**: **Must be called** after report generation to validate evidence grounding.
- **ModelRouter**: Selects the model for report generation.
- **OrchestratorAgent**: Routes to HandoffGeneratorAgent when slot filling is complete.
