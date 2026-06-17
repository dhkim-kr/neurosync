# Neuro-Sync AI Multi-Agent System — Development Plan

> **Version**: 1.0
> **Created**: 2026-06-15
> **PRD Source**: `docs/ai/PRD_ai_v.0.0.0.0.md`
> **API Specs**: `docs/ai/api/{SKT_A_X_API,EXAONE_API,Upstage_API}.md`
> **Target**: 8-week MVP scaffold (PRD §13)
> **Owner**: AI Research Team

---

## Goal

Build a production-ready scaffold for the 12-agent multi-agent AI system that:
- Implements all 5 vendor adapters with correct API specs
- Routes model selection through YAML-based registry (no hardcoded models)
- Exposes 6 FastAPI endpoints matching PRD §7 contracts
- Provides versioned system prompts for all 12 agents
- Includes eval harness skeleton for model comparison

## Architecture Overview

```
Client → Platform API → AI Server (this system)
                            │
                            ├── routes/         ← 6 thin FastAPI handlers
                            ├── agents/         ← 12 agent implementations
                            ├── adapters/       ← 5 vendor API wrappers
                            ├── routing/        ← ModelRouter + YAML registry
                            ├── schemas/        ← Internal Pydantic I/O models
                            ├── prompts/        ← Prompt loader (reads docs/ai/prompts/)
                            └── config.py       ← Environment-based settings
```

## Phase Dependency Graph

```
Phase 1: Foundation
  ├──→ Phase 2: Shared Contracts (parallel)
  └──→ Phase 3: Adapters (parallel)
            └──→ Phase 4: Routing
                      ├──→ Phase 5: Core Agents
                      │         └──→ Phase 6: Pipeline Agents
                      │                   └──→ Phase 7: Routes + Prompts + Eval
                      └──→ Phase 7 (partial: prompt loader)
```

## Phase Summary

| Phase | Name | Files | Depends On | Agent Owner | Gate |
|---|---|---|---|---|---|
| 1 | [Foundation](./phase-1-foundation.md) | 7 new + 1 modified | — | `developer` | `qa`: imports clean, config loads |
| 2 | [Shared Contracts](./phase-2-shared-contracts.md) | 7 new | Phase 1 | `developer` | `critic`: interface review |
| 3 | [Adapters](./phase-3-adapters.md) | 6 new | Phase 1 | `developer` | `qa`: mock healthchecks pass |
| 4 | [Routing](./phase-4-routing.md) | 4 new | Phase 3 | `developer` | `critic`: routing logic review |
| 5 | [Core Agents](./phase-5-core-agents.md) | 12 new | Phase 4 | `developer` | `qa`+`critic`: safety merge correct |
| 6 | [Pipeline Agents](./phase-6-pipeline-agents.md) | 10 new | Phase 5 | `developer` | `critic`: evidence policy review |
| 7 | [Routes, Prompts, Eval](./phase-7-routes-prompts-eval.md) | ~60 new + 1 modified | Phase 6 | `developer`+`writer`+`data` | `qa`: integration test |
| **Total** | | **~106 new + 2 modified** | | | |

## Complete File Inventory

### `apps/ai-server/src/` — AI Server Code (45 files)

```
src/
├── __init__.py                          (exists — no change)
├── main.py                              (modify: Phase 7 — mount routers)
├── config.py                            (Phase 1)
├── dependencies.py                      (Phase 7)
├── agents/
│   ├── __init__.py                      (Phase 1)
│   ├── base.py                          (Phase 1)
│   ├── safety_classifier.py             (Phase 5)
│   ├── stt.py                           (Phase 5)
│   ├── ocr.py                           (Phase 5)
│   ├── input_normalizer.py              (Phase 5)
│   ├── dialogue.py                      (Phase 5)
│   ├── clinical_slot.py                 (Phase 5)
│   ├── orchestrator.py                  (Phase 6)
│   ├── handoff_generator.py             (Phase 6)
│   ├── evidence_verifier.py             (Phase 6)
│   ├── temporal_retriever.py            (Phase 6)
│   ├── temporal_summary.py              (Phase 6)
│   └── prompt_eval.py                   (Phase 6)
├── adapters/
│   ├── __init__.py                      (Phase 3)
│   ├── base.py                          (Phase 1)
│   ├── solar_pro3.py                    (Phase 3)
│   ├── k_exaone.py                      (Phase 3)
│   ├── ak_llm.py                        (Phase 3)
│   ├── skt_ax_stt.py                    (Phase 3)
│   └── upstage_document_parse.py        (Phase 3)
├── routing/
│   ├── __init__.py                      (Phase 4)
│   ├── model_router.py                  (Phase 4)
│   ├── agent_model_registry.yaml        (Phase 4)
│   └── fallback_policy.py               (Phase 4)
├── schemas/
│   ├── __init__.py                      (Phase 1)
│   ├── common.py                        (Phase 1)
│   ├── safety.py                        (Phase 5)
│   ├── dialogue.py                      (Phase 5)
│   ├── clinical_slot.py                 (Phase 5)
│   ├── stt.py                           (Phase 5)
│   ├── ocr.py                           (Phase 5)
│   ├── input_normalizer.py              (Phase 5)
│   ├── orchestrator.py                  (Phase 6)
│   ├── handoff.py                       (Phase 6)
│   ├── evidence.py                      (Phase 6)
│   └── temporal.py                      (Phase 6)
├── prompts/
│   ├── __init__.py                      (Phase 7)
│   └── loader.py                        (Phase 7)
└── routes/
    ├── __init__.py                      (Phase 7)
    ├── chat.py                          (Phase 7)
    ├── safety.py                        (Phase 7)
    ├── stt.py                           (Phase 7)
    ├── ocr.py                           (Phase 7)
    ├── handoff.py                       (Phase 7)
    └── eval.py                          (Phase 7)
```

### `packages/shared-contracts/python/src/contracts/` — Interface Models (7 files)

```
contracts/
├── __init__.py                          (modify: Phase 2 — add re-exports)
├── chat.py                              (Phase 2)
├── safety.py                            (Phase 2)
├── stt.py                               (Phase 2)
├── ocr.py                               (Phase 2)
├── handoff.py                           (Phase 2)
└── eval.py                              (Phase 2)
```

### `docs/ai/prompts/` — Prompt Registry (36+ files)

```
prompts/
├── orchestrator/
│   ├── v1.system.md                     (Phase 7)
│   ├── v1.schema.json                   (Phase 7)
│   └── eval_cases.jsonl                 (Phase 7)
├── safety_classifier/
│   ├── v1.system.md                     (Phase 7)
│   ├── v1.schema.json                   (Phase 7)
│   ├── risk_taxonomy.json               (Phase 7)
│   └── eval_cases.jsonl                 (Phase 7)
├── dialogue/
│   ├── v1.system.md                     (Phase 7)
│   ├── v1.schema.json                   (Phase 7)
│   └── eval_cases.jsonl                 (Phase 7)
├── clinical_slot/                       ... (same pattern)
├── input_normalizer/                    ...
├── stt/                                 ...
├── ocr/                                 ...
├── temporal_retriever/                  ...
├── temporal_summary/                    ...
├── handoff_generator/                   ...
├── evidence_verifier/                   ...
└── prompt_eval/                         ...
```

### `apps/ai-server/eval/` — Eval Harness (5 files)

```
eval/
├── __init__.py                          (Phase 7)
├── metrics.py                           (Phase 7)
└── runners/
    ├── __init__.py                      (Phase 7)
    ├── safety_eval.py                   (Phase 7)
    └── model_comparison.py              (Phase 7)
```

### `docs/ai/eval/` — Eval Datasets (4 skeleton files)

```
eval/
├── safety_redteam_v1.jsonl              (Phase 7)
├── dialogue_intake_v1.jsonl             (Phase 7)
├── slot_extraction_v1.jsonl             (Phase 7)
└── handoff_v1.jsonl                     (Phase 7)
```

### `apps/ai-server/tests/` — Test Files (~20 files)

```
tests/
├── __init__.py                          (exists)
├── test_health.py                       (exists)
├── test_config.py                       (Phase 1)
├── test_schemas.py                      (Phase 1)
├── conftest.py                          (Phase 3 — shared fixtures)
├── adapters/
│   ├── __init__.py                      (Phase 3)
│   ├── test_solar_pro3.py              (Phase 3)
│   ├── test_k_exaone.py               (Phase 3)
│   ├── test_ak_llm.py                 (Phase 3)
│   ├── test_skt_ax_stt.py             (Phase 3)
│   └── test_upstage_doc_parse.py      (Phase 3)
├── routing/
│   ├── __init__.py                      (Phase 4)
│   └── test_model_router.py            (Phase 4)
├── agents/
│   ├── __init__.py                      (Phase 5)
│   ├── test_safety_classifier.py       (Phase 5)
│   ├── test_dialogue.py               (Phase 5)
│   └── test_input_normalizer.py        (Phase 5)
└── routes/
    ├── __init__.py                      (Phase 7)
    ├── test_chat.py                    (Phase 7)
    ├── test_safety.py                  (Phase 7)
    └── test_handoff.py                 (Phase 7)
```

## Key Reconciliation Decisions

| PRD Says | This Plan Does | Reason |
|---|---|---|
| Directory root is `app/` (§4.3) | Use `src/` | Existing `pyproject.toml` line 31: `packages = ["src"]` and `main.py` line 10: `from src import __version__` |
| `agent_model_registry` is DB table (§12.1) | YAML config file | AI server cannot access DB (boundary rule in Master PRD §0.3, AI README §3.3) |
| STT vendor is "A.K" (§3.1) | Internal name `skt-ax-stt` | Same vendor, confirmed via `docs/ai/api/SKT_A_X_API.md` — "A.K" and "A.X" refer to same SKT service |
| OCR vendor is "Solar Document Parse" (§3.1) | Internal name `solar-document-parse` | Same as Upstage Document Parse, confirmed via `docs/ai/api/Upstage_API.md` §11 |
| 3 LLM candidates benchmarked from MVP | YAML registry with initial assignments | Actual benchmarking happens post-scaffold; registry allows easy swap |

## Research Agent Workflow Mapping

Each phase maps to the `.claude/agents/` research pipeline:

```
Phase 1-6: developer (code) → qa (verify) → critic (review)
Phase 7 prompts: writer (prompt content) → critic (safety review)
Phase 7 eval data: data (dataset skeletons) → critic (leakage audit)
All phases: orchestrator (coordination) → filemanager (git hygiene)
```

## Environment Variables Required

```env
# Upstage Solar Pro 3
UPSTAGE_API_KEY=
UPSTAGE_BASE_URL=https://api.upstage.ai/v1
UPSTAGE_CHAT_MODEL=solar-pro3

# EXAONE / Friendli Dedicated
LG_K_EXAONE_API_KEY=
LG_K_EXAONE_ENDPOINT_ID=
LG_K_EXAONE_BASE_URL=https://api.friendli.ai/dedicated/v1

# SKT A.X (LLM + STT — same key, different auth headers)
SKT_A_X_API_KEY=
SKT_A_X_REST_BASE_URL=https://awf-gw.adot.ai
SKT_A_X_WS_BASE_URL=wss://awf-gw.adot.ai
SKT_A_X_LLM_MODEL=A.X-K1
SKT_A_X_STT_STREAMING_MODEL=A.X_STT_note_streaming
SKT_A_X_STT_BATCH_MODEL=A.X_STT_note_batch
```

## Security Reminders

1. **API keys in docs**: `docs/ai/api/EXAONE_API.md` line 41 and `docs/ai/api/Upstage_API.md` line 30 contain hardcoded API keys. Remove and rotate before any commit.
2. **No PII in logs**: All adapters must implement `redact_for_log()`.
3. **Synthetic data only**: All eval datasets use synthetic cases until legal review.
4. **No raw CoT**: Agents return `reason_summary` only, never internal reasoning chains.
