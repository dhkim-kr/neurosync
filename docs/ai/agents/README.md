# Agent Specifications

This directory contains the specification documents for all 12 agents in the Neuro-Sync AI multi-agent pipeline.

Each agent spec follows a standardized template covering: role, model policy, I/O contract, behavior, safety constraints, failure fallback, model selection, and dependencies.

## Agent Index

| # | Agent | Role | Model Policy | Input | Output |
|---|---|---|---|---|---|
| 1 | [OrchestratorAgent](orchestrator.md) | Workflow routing, tool call planning, state transitions | Benchmarked (Solar Pro 3 / K-EXAONE / A.K) | user_intent, session_state, risk_state | next_action, required_agents, confidence |
| 2 | [SttAgent](stt.md) | Voice-to-text transcription | Fixed (SKT A.K STT) | audio_bytes, language, context_hint | transcript, confidence, timestamps, low_confidence_spans |
| 3 | [InputNormalizerAgent](input_normalizer.md) | STT error, typo, and grammar normalization | Benchmarked (Solar Pro 3 / K-EXAONE / A.K) | transcript/text | normalized_text, uncertainty_spans |
| 4 | [SafetyClassifierAgent](safety_classifier.md) | Crisis and risk classification (suicide, self-harm, harm-to-others) | Benchmarked (Solar Pro 3 / K-EXAONE / A.K) + Rule Ensemble | latest_message, recent_context | risk_level, evidence, action, confidence |
| 5 | [DialogueAgent](dialogue.md) | Safe pre-intake dialogue and slot-filling question generation | Benchmarked (Solar Pro 3 / K-EXAONE / A.K) | normalized_text, missing_slots, context | assistant_response, slot_updates |
| 6 | [ClinicalSlotAgent](clinical_slot.md) | CC/HPI/PMH/medication/risk slot extraction | Benchmarked (Solar Pro 3 / K-EXAONE / A.K) | message_batch, ocr_text | structured_clinical_slots, evidence_ids |
| 7 | [OcrAgent](ocr.md) | Medical document OCR, parsing, and entity extraction | Fixed (Solar Document Parse) | file_bytes, doc_type | markdown, structured_blocks, medical_entities, confidence |
| 8 | [TemporalRetrieverAgent](temporal_retriever.md) | Past session/document/scale evidence retrieval | Internal RAG + Benchmarked LLM | query, patient_id, time_filter | evidence_packets, coverage |
| 9 | [TemporalSummaryAgent](temporal_summary.md) | Longitudinal delta summary (improved/worsened/unchanged) | Benchmarked (Solar Pro 3 / K-EXAONE / A.K) | evidence_packets | deltas (improved/worsened/unchanged/unknown), contradictions |
| 10 | [HandoffGeneratorAgent](handoff_generator.md) | Evidence-grounded Handoff Report generation for clinicians | Benchmarked (Solar Pro 3 / K-EXAONE / A.K) | slots, risk, scales, evidence | report_markdown, evidence_table, missing_information |
| 11 | [EvidenceVerifierAgent](evidence_verifier.md) | Verify evidence grounding and prohibit diagnostic/treatment claims | Benchmarked (Solar Pro 3 / K-EXAONE / A.K) + Rule Checker | draft, evidence_packets | verified_report, flags, pass/fail |
| 12 | [PromptEvalAgent](prompt_eval.md) | Offline prompt/model regression evaluation | Offline (Solar Pro 3 / K-EXAONE / A.K) | eval_dataset | metrics, fail_cases, release_decision |

## Pipeline Flow

```
Audio Input ─> SttAgent ─> InputNormalizerAgent ─┐
Text Input ──────────────────────────────────────┤
                                                  v
                                    SafetyClassifierAgent
                                          │
                              ┌───────────┴───────────┐
                              v                       v
                     high/critical              none/low/medium
                     (Crisis Interrupt)               │
                                                      v
                                              DialogueAgent
                                                      │
                                                      v
                                            ClinicalSlotAgent <── OcrAgent
                                                      │
                                                      v
                                          TemporalRetrieverAgent
                                                      │
                                                      v
                                          TemporalSummaryAgent
                                                      │
                                                      v
                                         HandoffGeneratorAgent
                                                      │
                                                      v
                                         EvidenceVerifierAgent
                                                      │
                                                      v
                                            Clinician Dashboard
```

All agents are coordinated by the **OrchestratorAgent** and use **ModelRouter** for model selection.

## Reference

- PRD: `docs/ai/PRD_ai_v.0.0.0.0.md` (sections 3.3, 5.1, 8)
- Model routing config: `agent_model_registry.yaml`
- Prompt registry: `docs/ai/prompts/`
