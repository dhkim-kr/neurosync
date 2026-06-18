# TemporalRetrieverAgent

> **Role**: Retrieve past session, document, scale, and risk event evidence for longitudinal patient context
> **Model Policy**: Internal RAG + Benchmarked (Solar Pro 3 / K-EXAONE / A.K) for summary
> **System Prompt**: `docs/ai/prompts/temporal_retriever/v1.system.md`
> **Implementation**: `apps/ai-server/src/agents/temporal_retriever.py`

## Input

| Field | Type | Required | Description |
|---|---|---|---|
| query | string | Yes | Semantic query describing the information need (e.g., symptom history, medication changes) |
| patient_id | string | Yes | Patient identifier for scoping the retrieval |
| time_filter | object | No | Time range filter with `start` and `end` ISO timestamps |

## Output

| Field | Type | Description |
|---|---|---|
| evidence_packets | list[object] | Retrieved evidence items, each with `evidence_id`, `source_type`, `source_id`, `timestamp`, `content`, `metadata`, `retrieval_score` |
| coverage | object | Coverage flags for key clinical domains: `cc` (bool), `hpi` (bool), `risk` (bool), `medication` (bool) |

## Behavior

1. Receive a semantic query, patient ID, and optional time filter.
2. Search across multiple evidence sources using pgvector semantic similarity:
   - **Conversation messages**: 1-3 turn segments with session_id, timestamp, speaker, risk_level, slot_tags.
   - **PHQ-9/GAD-7 scales**: Score results with severity, item_scores, date.
   - **OCR documents**: Paragraph/table/block level with doc_type, page, block_id, confidence, date.
   - **Handoff reports**: Section-level chunks with report_version, claim_ids, clinician_feedback.
   - **Risk events**: Event records with risk_level, category, evidence, action, timestamp.
3. Score each evidence item using the composite retrieval formula:
   - `score = semantic_similarity + 0.15 * recency_weight + 0.25 * risk_relevance + 0.10 * document_confidence + 0.20 * clinician_feedback_weight - 0.30 * stale_or_contradicted_penalty`
4. Rank and return top evidence packets with their scores.
5. Compute coverage flags indicating which clinical domains have sufficient evidence.

## Safety Constraints

- Must only retrieve evidence for the authenticated patient (patient_id scoping enforced via Context Gateway).
- Must never access the database directly; all queries go through the Context Gateway API.
- PHI-containing evidence is stored only in the internal pgvector instance; external vector stores are prohibited.
- Must not log PHI evidence content; only metadata and retrieval scores are stored.

## Failure Fallback

When retrieval fails (pgvector timeout, Context Gateway error, LLM summary failure):
- Fall back to **recency-only retrieval**: Return the most recent evidence items without semantic scoring.
- Set lower confidence on all returned packets.
- Log the failure with `agent_trace_id` and `latency_ms`.

## Model Selection

The retrieval component uses internal pgvector (no LLM). The optional LLM summary component uses ModelRouter to select from Solar Pro 3 / K-EXAONE / A.K based on summary quality benchmarks. Fallback chain applies for timeout / 429 / 5xx.

## Dependencies

- **Context Gateway**: Provides access to past sessions, documents, scales, and risk events via API.
- **pgvector (PostgreSQL)**: Internal vector store for semantic similarity search.
- **ModelRouter**: Selects the LLM for evidence summarization (if needed).
- **TemporalSummaryAgent**: Downstream consumer of evidence packets for delta summarization.
- **HandoffGeneratorAgent**: Downstream consumer of evidence packets for report generation.
- **EvidenceVerifierAgent**: Uses evidence packets to verify Handoff claims.
