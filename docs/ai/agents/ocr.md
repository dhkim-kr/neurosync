# OcrAgent

> **Role**: Parse uploaded medical documents via OCR and extract structured evidence blocks
> **Model Policy**: Fixed (Solar Document Parse)
> **System Prompt**: `docs/ai/prompts/ocr/v1.system.md`
> **Implementation**: `apps/ai-server/src/agents/ocr.py`

## Input

| Field | Type | Required | Description |
|---|---|---|---|
| file_bytes | bytes | Yes | Raw file content (PDF, image, doc/docx/hwpx) received via file token or presigned URL |
| doc_type | string | No | Hint for document type: `prescription`, `diagnosis_note`, `lab_result`, `psych_scale`, `unknown` |
| requested_outputs | list[string] | No | Output formats requested, defaults to `["markdown", "structured_blocks"]` |

## Output

| Field | Type | Description |
|---|---|---|
| doc_id | string | Unique document identifier |
| text_markdown | string | Full document content rendered as Markdown |
| structured_blocks | list[object] | Block-level data, each with `block_id`, `page`, `type`, `content`, `confidence` |
| medical_entities | list[object] | Extracted entities, each with `entity_id`, `type`, `value`, `confidence`, `source_block_id`, `requires_human_review` |
| vendor | string | Always `solar_document_parse` |
| requires_human_review | bool | Whether any block or entity has low confidence |

## Behavior

1. Receive the uploaded file bytes and optional document type hint from the platform.
2. Validate the file format (PDF, image, doc/docx/hwpx support confirmed per API spec).
3. Call `SolarDocumentParseAdapter.parse_document()` with file bytes, doc type, and requested outputs.
4. Parse vendor response into Markdown text and structured blocks with page/block/coordinate metadata.
5. Extract medical entities based on document type:
   - `prescription`: medication_name, dosage, frequency, duration, prescribing_date, institution.
   - `diagnosis_note`: diagnosis_text, impression, visit_date, clinician_note, institution.
   - `lab_result`: test_name, value, unit, reference_range, date.
   - `psych_scale`: scale_name, item_scores, total_score, severity.
   - `unknown`: title, date, text_blocks, low_confidence_blocks.
6. Flag low-confidence blocks/entities, handwritten sections, and table parse failures with `requires_human_review = true`.
7. Apply medical entity normalization using the best-performing benchmarked LLM (Solar Pro 3 / K-EXAONE / A.K).

## Safety Constraints

- Must never treat OCR results as confirmed facts; low-confidence items must always be flagged for review.
- Must preserve original page/block/coordinate metadata for evidence traceability.
- Must not send documents to the OCR vendor without proper consent and data processing agreements (PHI handling).
- Raw uploaded files follow short-term retention and deletion policies.
- Must not log PHI document content; only metadata and hashes are stored.

## Failure Fallback

When OCR fails (timeout, 5xx, unsupported format, parse failure):
- Return a **manual text input** fallback prompting the user or clinician to enter document information manually.
- Log failure details including document type, file size, and error reason.

## Model Selection

This agent uses a **fixed vendor**: Solar Document Parse. No ModelRouter selection for the core OCR task. However, post-OCR medical entity normalization uses a benchmarked LLM selected by ModelRouter based on entity normalization accuracy.

## Dependencies

- **SolarDocumentParseAdapter**: The vendor adapter wrapping the Solar Document Parse API.
- **ModelRouter**: Selects the LLM for post-OCR entity normalization.
- **ClinicalSlotAgent**: Consumes OCR text for clinical slot extraction.
- **TemporalRetrieverAgent**: OCR document blocks are indexed as temporal evidence.
- **HandoffGeneratorAgent**: OCR entities and blocks serve as evidence in the Handoff Report.
