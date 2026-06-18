# Task 1 개발/검증 리포트

> 이 문서는 append-only입니다. 각 항목은 checklist_task1.md의 ID를 참조합니다.

## 작성 규칙

1. 각 entry는 `## [YYYY-MM-DD] CHECKLIST_ID | STATUS` 형식으로 시작합니다.
2. STATUS: DONE, BLOCKED, ISSUE, NOTE
3. 개발 완료 시: 구현 요약, 변경된 파일 목록, 주요 결정사항
4. 검증 완료 시: 테스트 결과 (pass/fail), 발견된 이슈, VP별 결과 요약
5. 이슈 발생 시: 원인 분석, 영향 범위, 해결 계획
6. version.md 와 연동: 주요 마일스톤 달성 시 version.md에 버전 범프 기록

---

## Entries

### RPT-001 [2026-06-19] T1-F0-DEV-002 | DONE

**Summary:** CTRSLevel IntEnum + CTRS↔RiskLevel 양방향 매핑 테이블 구현
**변경 파일:**
- `apps/ai-server/src/schemas/common.py` — `CTRSLevel(IntEnum)`, `CTRS_TO_RISK`, `RISK_TO_CTRS` 추가
- `apps/ai-server/src/schemas/safety.py` — `SafetyOutput.ctrs_level: int` 필드 추가
**결정사항:** PRD Section 13 Option A 채택 — CTRSLevel을 별도 IntEnum으로 정의하고 명시적 매핑 테이블 사용

---

### RPT-002 [2026-06-19] T1-F1-DEV-001 | DONE

**Summary:** SafetyClassifierAgent에 CTRS level 산출 통합
**변경 파일:**
- `apps/ai-server/src/agents/safety_classifier.py` — `RISK_TO_CTRS` import, `run()` 반환값에 `ctrs_level` 추가, `crisis_protocol_activated`를 CTRS 1-2 기준으로 변경 (기존: critical만), `requires_human_review`를 CTRS 1-3 기준으로 확장
**영향:** crisis flow 발동 조건이 `critical` 단독 → `CTRS 1-2 (critical + high)` 로 확장됨

---

### RPT-003 [2026-06-19] T1-F3-DEV-003 | DONE

**Summary:** 5개 정신건강 구조화 척도 rule-based scoring engine 구현
**변경 파일:**
- `apps/ai-server/src/scoring/__init__.py` — 신규 모듈
- `apps/ai-server/src/scoring/survey_scorer.py` — PHQ-9, GAD-7, PHQ-4, WHO-5, AUDIT-C 구현
**구현 내역:**
- 순수 Python, LLM 호출 없음
- `ScoreResult` dataclass: total_score, severity, critical_items, subscale_scores
- PHQ-9 item 9 양성 시 `safety_referral` action 반환
- AUDIT-C 성별별 threshold 적용 (남 ≥4, 여 ≥3)
- 입력 검증: 문항 수 불일치, 값 범위 초과 시 ValueError

---

### RPT-004 [2026-06-19] T1-F3-VER-001, T1-F3-VER-002 | DONE

**Summary:** 전체 scoring unit test 39건 실행 — 100% pass
**변경 파일:**
- `apps/ai-server/tests/test_survey_scoring.py` — 신규 테스트
**테스트 결과:**
- PHQ-9: 10 boundary tests + Q9 safety trigger + validation = 14 passed
- GAD-7: 8 boundary tests + no-critical + validation = 10 passed
- PHQ-4: 8 boundary tests + subscale = 9 passed
- WHO-5: 3 tests (low/adequate/max) = 3 passed
- AUDIT-C: 2 tests (male/female threshold) = 2 passed
- Invalid scale: 1 passed
- **Total: 39/39 passed (0.04s)**
**추가 조치:** 구 모듈 경로 참조하던 `tests/test_safety.py` (레거시) 삭제

---

### RPT-005 [2026-06-19] T1-F1-DEV-011~013 + 문서 전체 업데이트 | DONE

**Summary:** SentimentAnalyzerAgent(13) 독립 agent로 분리 신설

**신규 파일:**
- `docs/ai/agents/13_sentiment_analyzer.md` — agent spec (Mode A: per-utterance, Mode B: session-level)
- `docs/ai/prompts/sentiment_analyzer/v1.system.md` — system prompt (감정 8종, 한국어 감정 표현 주의사항)

**수정 파일:**
- `09_temporal_summary.md` (agent spec + prompt) — sentiment 소비자 역할로 전환, plot_data에 sentiment_polarity 추가
- `10_handoff_generator.md` (agent spec + prompt) — Section 8에 발화별 sentiment 태그 표시
- `agent_model_registry.yaml` — sentiment_analyzer entry 추가
- `PRD_task1.md` — agent 매핑 분리, 통합 결정 변경, F1 DEV-011~013 추가
- `checklist_task1.md` — DEV 3건 + VER 2건 추가 (65→70항목)

**설계 결정:**
- Sentiment agent: F1 파이프라인에서 매 턴 실행 (Dialogue와 병렬 가능)
- TemporalSummary: sentiment 소비만 (직접 분석 안 함)
- HandoffGenerator: per_utterance_tags로 발화별 감정 시각화
- Downstream: SentimentAnalyzer → TemporalSummary (plot_data) + HandoffGenerator (Section 8)

---
