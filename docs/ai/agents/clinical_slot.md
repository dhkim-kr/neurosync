# ClinicalSlotAgent

> **Role**: Extract structured clinical slots (CC, HPI, PMH, medication, risk) from patient messages and OCR text
> **Model Policy**: Benchmarked (Solar Pro 3 / K-EXAONE / A.K)
> **System Prompt**: `docs/ai/prompts/clinical_slot/v1.system.md`
> **Implementation**: `apps/ai-server/src/agents/clinical_slot.py`

## Input

| Field | Type | Required | Description |
|---|---|---|---|
| message_batch | list[object] | Yes | Batch of patient messages (each with `text`, `turn_id`, `timestamp`) |
| ocr_text | string | No | Structured text from OcrAgent output (markdown or plain text from parsed documents) |

## Output

| Field | Type | Description |
|---|---|---|
| structured_clinical_slots | object | Extracted slots organized by category: `chief_complaint`, `hpi`, `pmh`, `medication`, `risk_factors`, `symptoms` (sleep, appetite, mood, anxiety, concentration, functional_impairment) |
| slot_confidence | object | Per-slot confidence scores |
| evidence_ids | list[string] | Source message or document IDs that support each slot value |
| requires_human_review | bool | Whether any slot has low confidence requiring clinician review |

## Behavior

1. Receive a batch of patient messages and optionally OCR-parsed document text.
2. Parse each message and document segment to identify clinical information.
3. Extract structured slots: Chief Complaint, History of Present Illness, Past Medical History, current medications, risk factors, and symptom domains (sleep, appetite, mood, anxiety, concentration, functional impairment).
4. Attach evidence IDs (message turn IDs or document block IDs) to each extracted slot value.
5. Compute per-slot confidence scores based on extraction certainty.
6. Flag slots with low confidence or ambiguous extractions for human review.
7. Return structured slots with confidence and evidence linkage.

## Safety Constraints

- Must never infer or fabricate clinical information not explicitly stated by the patient or present in the documents.
- Must never generate diagnostic conclusions; only extract what the patient reported.
- Must preserve the patient's exact phrasing in evidence references.
- Must flag ambiguous or contradictory slot values rather than silently resolving them.
- Must not log PHI slot content; only metadata and hashes are stored.

## Failure Fallback

When the Clinical Slot LLM fails (timeout, invalid JSON, 5xx):
- Set `requires_human_review = true` for all slots.
- Return partial extraction results if available, or an empty slot structure with the review flag.
- Log the failure with `agent_trace_id`, `model_used`, and `latency_ms`.

## Model Selection

ModelRouter queries `agent_model_registry` for `agent_name=clinical_slot`. Selection criteria:
- **Priority metrics**: Slot F1 score, evidence alignment accuracy.
- Candidates: Solar Pro 3, K-EXAONE, A.K.
- Fallback chain: timeout / 429 / 5xx / invalid JSON triggers secondary model or human review flag.

## Dependencies

- **DialogueAgent**: Provides message batches from the intake conversation.
- **OcrAgent**: Provides structured OCR text from uploaded documents.
- **ModelRouter**: Selects the model for slot extraction.
- **HandoffGeneratorAgent**: Consumes the structured slots for report generation.
- **OrchestratorAgent**: Routes to ClinicalSlotAgent and checks slot completeness.
