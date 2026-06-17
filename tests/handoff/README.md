# Handoff Health Report — Test Framework

가상 환자 데이터와 종단 기록을 활용한 체계적 Handoff Report 테스트 환경.

## Test Matrix (6 Cases)

| Case | ID | Label | Severity | Visit | Key Feature |
|------|----|-------|----------|-------|-------------|
| 1 | TC-001 | 경증 초진 | Mild | First | Clean baseline, no risk |
| 2 | TC-002 | 경증 재진 | Mild | Revisit | Escitalopram, PHQ-9 improved (14→7) |
| 3 | TC-003 | 중증 초진 | Severe | First | Suicidal ideation, business failure |
| 4 | TC-004 | 중증 재진 | Severe | Revisit | Sertraline+alprazolam, worsened (12→23) |
| 5 | TC-005 | Safety guard | Critical | - | Crisis keyword detection, dual rule+LLM |
| 6 | TC-006 | First vs longitudinal | Severe | Both | Same patient, minimal vs full records |

## Directory Structure

```
tests/handoff/
├── conftest.py              # pytest fixtures: real agent bootstrapping
├── fixtures/
│   ├── patients.py          # fixture loader + HandoffInput factory
│   ├── mild_first_visit.json
│   ├── mild_revisit.json
│   ├── severe_first_visit.json
│   ├── severe_revisit.json
│   ├── safety_trigger.json
│   └── longitudinal_pair.json
├── evaluators/
│   ├── section_checker.py   # 11 required sections presence
│   ├── evidence_checker.py  # citation integrity + dangling refs
│   ├── violation_checker.py # diagnosis + treatment violation regex
│   ├── risk_checker.py      # expected vs actual risk level
│   ├── safety_checker.py    # crisis protocol, rule trigger, categories
│   ├── longitudinal_checker.py  # delta section, score comparison
│   └── composite.py         # orchestrates all checkers → HandoffEvalResult
├── runners/
│   └── matrix_runner.py     # CLI: runs all 6 cases, generates reports
├── reports/
│   └── generator.py         # generates result.md, discussion.md, version.md, error.md
├── test_handoff_matrix.py   # pytest: parametrized 4 handoff cases
├── test_safety_guard.py     # pytest: 5 safety assertions
├── test_longitudinal.py     # pytest: 4 first-vs-longitudinal comparisons
└── README.md
```

## How to Run

### Prerequisites

```bash
# LLM API key 설정 (최소 1개)
export UPSTAGE_API_KEY=...
# 또는
export LG_K_EXAONE_API_KEY=...
export SKT_A_X_API_KEY=...
```

### pytest (individual tests)

```bash
cd apps/ai-server
python -m pytest tests/handoff/ -v --asyncio-mode=auto
```

### Matrix Runner (full suite + reports)

```bash
cd apps/ai-server
python -m tests.handoff.runners.matrix_runner --output-dir ../../docs/
```

Output: `docs/result.md`, `docs/discussion.md`, `docs/version.md`, `docs/error.md` (if failures)

## Fixture Format

Each fixture JSON maps directly to `HandoffInput` schema:

```json
{
  "case_id": "TC-001",
  "case_name": "경증 초진",
  "handoff_input": {
    "session_id": "...",
    "slots": { "chief_complaint": "...", ... },
    "conversation_history": [{"role": "...", "content": "..."}],
    "scale_scores": [{"scale_name": "PHQ-9", "total_score": 6, "severity": "mild"}],
    "risk_events": [],
    "prior_handoff": null,
    "is_first_visit": true
  },
  "safety_input": { "user_message": "...", "conversation_history": [] },
  "expected": { "risk_level": "none", "min_sections": 9, ... }
}
```

## Adding New Test Cases

1. Create a new `.json` file in `fixtures/`
2. Follow the fixture format above
3. Add to `MATRIX_CASES` in `test_handoff_matrix.py`
4. Add to `CASE_MATRIX` in `runners/matrix_runner.py`

## Evaluator Checks

| Checker | What it validates |
|---------|-------------------|
| SectionChecker | 11 required handoff report sections present |
| EvidenceChecker | Evidence citations exist, no dangling refs |
| ViolationChecker | No diagnosis assertions, no treatment recommendations |
| RiskChecker | Risk level matches expected (exact or minimum) |
| SafetyChecker | Crisis protocol, rule trigger, risk categories |
| LongitudinalChecker | Delta section present, score comparison, direction |
| CompositeEvaluator | Runs all applicable checkers, produces overall verdict |

## Report Files

| File | Content |
|------|---------|
| `result.md` | Results table + per-case detail |
| `discussion.md` | Analysis, safety findings, recommendations |
| `version.md` | Archived run summary + ADRs |
| `error.md` | Bug entries for failures (only if failures exist) |
