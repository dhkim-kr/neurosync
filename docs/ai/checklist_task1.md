# Task 1 개발/검증 체크리스트

> AI 기반 사전문진 Handoff Report 생성 (기능 1-1 ~ 1-5)

## ID 형식

`T1-Fn-{TYPE}-{SEQ}`

| 접두어 | 의미 |
|---|---|
| T1 | Task 1 |
| F0 | 공통/Orchestrator |
| F1 | 기능 1-1: 자율 대화 기반 문진 |
| F2 | 기능 1-2: RAG 기반 정신건강 영역 추론 |
| F3 | 기능 1-3: 구조화된 사전문진 설문 |
| F4 | 기능 1-4: 종단적 상태 추론 |
| F5 | 기능 1-5: Handoff Report 생성 |

| TYPE | 의미 |
|---|---|
| DEV | 개발 |
| VER | 검증 |
| CFG | 설정/인프라 |
| DOC | 문서 |

| 상태 | 의미 |
|---|---|
| `[ ]` | TODO |
| `[~]` | IN_PROGRESS |
| `[x]` | DONE |
| `[!]` | BLOCKED |

---

## F0: 공통/Orchestrator (T1-F0-*)

| ID | Type | 항목 | 상태 | 선행 조건 | Report 참조 |
|---|---|---|---|---|---|
| T1-F0-DEV-001 | DEV | Orchestrator state machine 구현 (ReceiveInput->SafetyGate->ContextRetrieval->Dialogue->SlotExtraction->HandoffReady) | [ ] | - | - |
| T1-F0-DEV-002 | DEV | CTRS <-> RiskLevel 매핑 enum 구현 | [x] | - | RPT-001 |
| T1-F0-DEV-003 | DEV | agent_model_registry.yaml 전체 agent 등록 확인 | [x] | - | RPT-008 |
| T1-F0-DEV-004 | DEV | PromptLoader 경로 설정 및 검증 | [x] | - | RPT-008 |
| T1-F0-CFG-001 | CFG | Docker Compose AI server 개발 환경 확인 | [ ] | - | - |
| T1-F0-CFG-002 | CFG | shared-contracts 패키지 동기화 | [ ] | - | - |
| T1-F0-DOC-001 | DOC | PRD_task1_development.md 작성 | [x] | - | - |
| T1-F0-DOC-002 | DOC | checklist_task1.md 작성 | [x] | - | - |
| T1-F0-DOC-003 | DOC | 가상 환자 Persona VP-001~VP-004 작성 | [x] | T1-F0-DOC-001 | - |
| T1-F0-DOC-004 | DOC | Patient LLM 시뮬레이션 사양서 작성 | [x] | T1-F0-DOC-003 | - |
| T1-F0-VER-001 | VER | Orchestrator 전체 파이프라인 end-to-end 테스트 | [ ] | T1-F0-DEV-001, T1-F5-DEV-005 | - |
| T1-F0-VER-002 | VER | 전체 VP 4명 통합 시뮬레이션 | [ ] | T1-F0-VER-001, T1-F0-DOC-003 | - |

---

## F1: 기능 1-1 자율 대화 기반 문진 (T1-F1-*)

| ID | Type | 항목 | 상태 | 선행 조건 | Report 참조 |
|---|---|---|---|---|---|
| T1-F1-DEV-001 | DEV | SafetyClassifierAgent CTRS 5단계 매핑 반영 | [x] | T1-F0-DEV-002 | RPT-002 |
| T1-F1-DEV-002 | DEV | InputNormalizerAgent 구현 | [ ] | - | - |
| T1-F1-DEV-003 | DEV | STT Agent + SKT A.X adapter 구현 | [ ] | - | - |
| T1-F1-DEV-004 | DEV | OCR Agent + Upstage Document Parse adapter 구현 | [ ] | - | - |
| T1-F1-DEV-005 | DEV | DialogueAgent slot coverage tracking 구현 | [x] | - | RPT-007 |
| T1-F1-DEV-006 | DEV | POST /ai/chat/respond 라우트 Orchestrator 연동 리팩토링 | [ ] | T1-F0-DEV-001 | - |
| T1-F1-DEV-007 | DEV | POST /ai/stt/transcribe 라우트 신규 구현 | [ ] | T1-F1-DEV-003 | - |
| T1-F1-DEV-008 | DEV | POST /ai/ocr/parse 라우트 신규 구현 | [ ] | T1-F1-DEV-004 | - |
| T1-F1-DEV-009 | DEV | safety_classifier prompt v1 고도화 (CTRS 기반) | [x] | T1-F1-DEV-001 | RPT-009 |
| T1-F1-DEV-010 | DEV | dialogue prompt v1 고도화 (slot tracking, 피로도 관리) | [x] | T1-F1-DEV-005 | RPT-009 |
| T1-F1-DEV-011 | DEV | SentimentAnalyzerAgent 구현 (Mode A: per-utterance, Mode B: session) | [x] | - | RPT-011 |
| T1-F1-DEV-012 | DEV | SentimentAnalyzer schema 정의 (SentimentInput, UtteranceOutput, SessionOutput) | [x] | T1-F1-DEV-011 | RPT-011 |
| T1-F1-DEV-013 | DEV | SentimentAnalyzer prompt v1 작성 완료 | [x] | - | RPT-005 |
| T1-F1-VER-001 | VER | VP-001 자율 대화 시뮬레이션 (초진 경증) | [x] | T1-F0-DOC-003 | RPT-006,007 |
| T1-F1-VER-002 | VER | VP-003 자율 대화 시뮬레이션 (초진 중증, CTRS 2-3 trigger) | [x] | T1-F0-DOC-003 | RPT-006,007 |
| T1-F1-VER-003 | VER | Safety gate CTRS 1-2 crisis bypass 통합 테스트 | [x] | T1-F1-DEV-001 | RPT-006,007 |
| T1-F1-VER-004 | VER | STT->InputNormalizer 정규화 정확도 테스트 | [ ] | T1-F1-DEV-002, T1-F1-DEV-003 | - |
| T1-F1-VER-005 | VER | Slot coverage convergence 테스트 (15턴 이내 0.7 달성) | [ ] | T1-F1-DEV-005 | - |
| T1-F1-VER-006 | VER | 위기 키워드 recall >= 95% 회귀 테스트 | [x] | T1-F1-DEV-001, T1-F1-DEV-009 | RPT-010 |
| T1-F1-VER-007 | VER | SentimentAnalyzer per-utterance 정확도 테스트 (경증/중증 발화 20건) | [ ] | T1-F1-DEV-011 | - |
| T1-F1-VER-008 | VER | SentimentAnalyzer session-level report 정합성 테스트 | [ ] | T1-F1-DEV-011 | - |

---

## F2: 기능 1-2 RAG 기반 정신건강 영역 추론 (T1-F2-*)

| ID | Type | 항목 | 상태 | 선행 조건 | Report 참조 |
|---|---|---|---|---|---|
| T1-F2-DEV-001 | DEV | TemporalRetrieverAgent 구현 | [ ] | - | - |
| T1-F2-DEV-002 | DEV | pgvector 기반 embedding 저장/검색 모듈 (placeholder) | [ ] | T1-F2-CFG-001 | - |
| T1-F2-DEV-003 | DEV | POST /ai/temporal/retrieve 라우트 신규 구현 | [ ] | T1-F2-DEV-001 | - |
| T1-F2-DEV-004 | DEV | RAG scoring formula 구현 (semantic_similarity + recency + risk_relevance) | [ ] | T1-F2-DEV-002 | - |
| T1-F2-CFG-001 | CFG | pgvector extension 설치 및 테이블 생성 (placeholder) | [ ] | T1-F0-CFG-001 | - |
| T1-F2-VER-001 | VER | VP-002 재진 데이터 retrieval 테스트 | [ ] | T1-F2-DEV-003, T1-F0-DOC-003 | - |
| T1-F2-VER-002 | VER | VP-004 재진 데이터 retrieval 테스트 | [ ] | T1-F2-DEV-003, T1-F0-DOC-003 | - |
| T1-F2-VER-003 | VER | VP-001/VP-003 초진 empty retrieval 테스트 | [ ] | T1-F2-DEV-003 | - |
| T1-F2-VER-004 | VER | Retrieval ranking 품질 검증 | [ ] | T1-F2-DEV-004 | - |

---

## F3: 기능 1-3 구조화된 사전문진 설문 (T1-F3-*)

| ID | Type | 항목 | 상태 | 선행 조건 | Report 참조 |
|---|---|---|---|---|---|
| T1-F3-DEV-001 | DEV | ClinicalSlotAgent 구현 | [x] | - | RPT-007 |
| T1-F3-DEV-002 | DEV | POST /ai/slots/extract 라우트 신규 구현 | [x] | T1-F3-DEV-001 | RPT-009 |
| T1-F3-DEV-003 | DEV | Rule-based scoring engine (PHQ-9, GAD-7, PHQ-4, WHO-5, AUDIT-C) | [x] | - | RPT-003 |
| T1-F3-DEV-004 | DEV | POST /ai/survey/score 라우트 신규 구현 (rule-based, no LLM) | [x] | T1-F3-DEV-003 | RPT-009 |
| T1-F3-DEV-005 | DEV | Survey Planner 로직 Orchestrator에 통합 | [ ] | T1-F0-DEV-001, T1-F3-DEV-001 | - |
| T1-F3-VER-001 | VER | PHQ-9 scoring unit test (알려진 입력 -> 예상 점수) | [x] | T1-F3-DEV-003 | RPT-004 |
| T1-F3-VER-002 | VER | GAD-7 scoring unit test | [x] | T1-F3-DEV-003 | RPT-004 |
| T1-F3-VER-003 | VER | VP별 slot extraction 정확도 비교 | [ ] | T1-F3-DEV-002, T1-F0-DOC-003 | - |
| T1-F3-VER-004 | VER | 자살 문항 양성 시 Safety 연동 테스트 | [ ] | T1-F3-DEV-005, T1-F1-DEV-001 | - |

---

## F4: 기능 1-4 종단적 상태 추론 (T1-F4-*)

| ID | Type | 항목 | 상태 | 선행 조건 | Report 참조 |
|---|---|---|---|---|---|
| T1-F4-DEV-001 | DEV | TemporalSummaryAgent 구현 | [ ] | - | - |
| T1-F4-DEV-002 | DEV | POST /ai/temporal/summarize 라우트 신규 구현 | [ ] | T1-F4-DEV-001 | - |
| T1-F4-DEV-003 | DEV | Direction classification 로직 (improved/worsened/unchanged/unknown) | [ ] | T1-F4-DEV-001 | - |
| T1-F4-DEV-004 | DEV | Plot-ready time-series data 생성 모듈 | [ ] | T1-F4-DEV-003 | - |
| T1-F4-VER-001 | VER | VP-002 종단 비교 테스트 (경증 호전) | [ ] | T1-F4-DEV-002, T1-F0-DOC-003 | - |
| T1-F4-VER-002 | VER | VP-004 종단 비교 테스트 (중증 악화, 새 증상 감지) | [ ] | T1-F4-DEV-002, T1-F0-DOC-003 | - |
| T1-F4-VER-003 | VER | VP-001/VP-003 초진 시 전체 "unknown" 반환 테스트 | [ ] | T1-F4-DEV-002 | - |
| T1-F4-VER-004 | VER | 모순 감지 테스트 (이전 "호전" vs 현재 "악화") | [ ] | T1-F4-DEV-003 | - |

---

## F5: 기능 1-5 Handoff Report 생성 (T1-F5-*)

| ID | Type | 항목 | 상태 | 선행 조건 | Report 참조 |
|---|---|---|---|---|---|
| T1-F5-DEV-001 | DEV | HandoffGenerator 12-section 템플릿 강화 | [x] | - | RPT-009 |
| T1-F5-DEV-002 | DEV | Evidence registry 완전성 강화 | [x] | T1-F5-DEV-001 | RPT-009 |
| T1-F5-DEV-003 | DEV | CTRS-action 일관성 검증 로직 추가 | [x] | T1-F0-DEV-002, T1-F5-DEV-001 | RPT-009 |
| T1-F5-DEV-004 | DEV | PDF/JSON 듀얼 출력 모듈 | [ ] | T1-F5-DEV-001 | - |
| T1-F5-DEV-005 | DEV | POST /ai/handoff/generate 라우트 전체 파이프라인 연동 | [ ] | T1-F5-DEV-001, T1-F0-DEV-001 | - |
| T1-F5-VER-001 | VER | VP-001 handoff report 생성 + EvidenceVerifier 검증 | [ ] | T1-F5-DEV-005, T1-F0-DOC-003 | - |
| T1-F5-VER-002 | VER | VP-002 handoff report (종단 데이터 포함) 생성 + 검증 | [ ] | T1-F5-DEV-005, T1-F4-DEV-001 | - |
| T1-F5-VER-003 | VER | VP-003 handoff report (CTRS 2-3 고위험) 생성 + 검증 | [ ] | T1-F5-DEV-005, T1-F1-DEV-001 | - |
| T1-F5-VER-004 | VER | VP-004 handoff report (종단 악화) 생성 + 검증 | [ ] | T1-F5-DEV-005, T1-F4-DEV-001 | - |
| T1-F5-VER-005 | VER | 12-section 완전성 자동 검증 | [x] | T1-F5-DEV-001 | RPT-009 |
| T1-F5-VER-006 | VER | Evidence citation 100% coverage 테스트 | [ ] | T1-F5-DEV-002 | - |

---

## 요약 통계

### 전체 항목 수

| 구분 | 수량 |
|---|---|
| **전체** | **70** |
| DEV | 35 |
| VER | 28 |
| CFG | 3 |
| DOC | 4 |

### 기능별 항목 수

| 기능 | 항목 수 | DEV | VER | CFG | DOC |
|---|---|---|---|---|---|
| F0: 공통/Orchestrator | 12 | 4 | 2 | 2 | 4 |
| F1: 자율 대화 기반 문진 | 21 | 13 | 8 | 0 | 0 |
| F2: RAG 기반 정신건강 영역 추론 | 9 | 4 | 4 | 1 | 0 |
| F3: 구조화된 사전문진 설문 | 9 | 5 | 4 | 0 | 0 |
| F4: 종단적 상태 추론 | 8 | 4 | 4 | 0 | 0 |
| F5: Handoff Report 생성 | 11 | 5 | 6 | 0 | 0 |
| **합계** | **70** | **35** | **28** | **3** | **4** |
