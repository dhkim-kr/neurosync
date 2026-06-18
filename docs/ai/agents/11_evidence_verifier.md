# Agent 11: QA & Consistency Checker Agent

## 개요

| 항목 | 내용 |
|---|---|
| **Agent ID** | `11` |
| **Agent Name** | `EvidenceVerifierAgent` |
| **역할** | Handoff report 품질 검증 및 release gate |
| **LLM Routing** | benchmarked (Primary: Upstage Solar Pro 3 / Secondary: LG K-EXAONE / Fallback: SKT A.X K1) |

## 목적

HandoffGeneratorAgent(10)가 생성한 report를 배포 전에 검증한다. 모든 검증 항목을 통과해야만 report가 의료진에게 전달된다. 위반 사항 발견 시 **reject하고 재생성을 요청**하며, 최대 2회 재시도 후에도 통과하지 못하면 의료진에게 경고와 함께 전달한다. 이 에이전트가 **release gate** 역할을 수행한다.

## 검증 항목 (Validation Checklist)

| 번호 | 검증 항목 | 심각도 | 설명 |
|---|---|---|---|
| V-01 | Evidence citation 완전성 | CRITICAL | 모든 claim에 `[ev_*]` 인용이 있는가 |
| V-02 | 진단적 단정 부재 | CRITICAL | 진단명을 단정하는 표현이 없는가 |
| V-03 | 치료 지시 부재 | CRITICAL | 치료를 지시하는 표현이 없는가 |
| V-04 | 구조화 점수 정확성 | CRITICAL | PHQ-9/GAD-7 등의 점수가 rule-based 계산 결과와 일치하는가 |
| V-05 | CTRS-조치 정합성 | CRITICAL | CTRS level과 권장 조치가 정합한가 (CTRS 1-2 → 즉시 대응 포함) |
| V-06 | OCR/STT low-confidence 표기 | HIGH | OCR/STT confidence < 0.8 항목이 한계 섹션에 명시되어 있는가 |
| V-07 | 누락 위험 신호 + CTRS 일관성 | CRITICAL | Safety classifier가 감지한 위험 신호가 report에 반영되어 있는가. **CTRS level이 위험 지표와 일치하는가** (아래 세부 규칙 참조) |
| V-08 | 12개 섹션 완전성 | HIGH | 모든 섹션이 존재하는가 (데이터 없는 섹션도 "정보 없음"으로 포함) |
| V-09 | Evidence registry 정합성 | HIGH | report 내 인용된 evidence ID가 모두 registry에 존재하는가 |
| V-10 | Disclaimer 존재 | HIGH | Section 5, 11, 12에 disclaimer가 포함되어 있는가 |
| V-11 | 종단 비교 근거 충분성 | MEDIUM | 종단 비교에서 "unknown" 아닌 판정에 근거가 있는가 |
| V-12 | 시제/표현 일관성 | LOW | 보고서 내 시제와 표현이 일관적인가 |

## V-07 CTRS 일관성 검증 세부 규칙

V-07은 단순한 위험 신호 누락 검사를 넘어, CTRS level이 관련 위험 지표와 일관적인지 교차 검증한다:

| 조건 | 최소 CTRS | 불일치 시 |
|---|---|---|
| PHQ-9 Q9 >= 1 (자살 사고 문항 양성) | CTRS 3 이하 | CTRS 4-5이면 FAIL |
| Active suicidal ideation (능동적 자살 사고) 감지됨 | CTRS 2 이하 | CTRS 3-5이면 FAIL |
| 구체적 자살 계획/수단 언급 | CTRS 2 이하 | CTRS 3-5이면 FAIL |
| 자살시도 진행 중 또는 직후 | CTRS 1 | CTRS 2-5이면 FAIL |
| Safety classifier가 crisis_triggered = true 반환 | CTRS 1-2 | CTRS 3-5이면 FAIL |
| CTRS 1-2인데 권장 조치에 즉시 대응(119/112/109) 미포함 | - | FAIL |

**FAIL 판정 시:** CRITICAL 위반으로 처리하여 report를 reject하고 재생성을 요청한다. rejection_instructions에 CTRS level 불일치 원인과 수정 방향을 포함한다.

## 입력

| 필드 | 타입 | 설명 |
|---|---|---|
| `handoff_report` | `object` | HandoffGeneratorAgent가 생성한 report |
| `clinical_slots` | `object` | ClinicalSlotAgent 원본 출력 (점수 검증용) |
| `safety_classification` | `object` | SafetyClassifierAgent 원본 결과 |
| `scale_scores_rule_based` | `object \| null` | Rule-based 계산된 척도 점수 원본 |
| `ocr_results` | `array<object> \| null` | OCR 원본 결과 (confidence 검증용) |
| `retry_count` | `integer` | 현재 재시도 횟수 (0, 1, 2) |

## 출력

```json
{
  "report_id": "handoff_20260618_001",
  "verification_result": "PASS",
  "retry_count": 0,
  "checks": [
    {
      "check_id": "V-01",
      "name": "Evidence citation 완전성",
      "severity": "CRITICAL",
      "result": "PASS",
      "details": "7개 claim, 7개 citation 확인"
    },
    {
      "check_id": "V-02",
      "name": "진단적 단정 부재",
      "severity": "CRITICAL",
      "result": "PASS",
      "details": "진단적 단정 표현 미발견"
    },
    {
      "check_id": "V-03",
      "name": "치료 지시 부재",
      "severity": "CRITICAL",
      "result": "PASS",
      "details": "치료 지시 표현 미발견"
    },
    {
      "check_id": "V-04",
      "name": "구조화 점수 정확성",
      "severity": "CRITICAL",
      "result": "PASS",
      "details": "PHQ-9 report 12점 = rule-based 12점 일치"
    },
    {
      "check_id": "V-05",
      "name": "CTRS-조치 정합성",
      "severity": "CRITICAL",
      "result": "PASS",
      "details": "CTRS 4, 권장 조치에 즉시 대응 불필요"
    },
    {
      "check_id": "V-06",
      "name": "OCR/STT low-confidence 표기",
      "severity": "HIGH",
      "result": "PASS",
      "details": "OCR confidence < 0.8 항목 1건, Section 11에 표기 확인"
    },
    {
      "check_id": "V-07",
      "name": "누락 위험 신호",
      "severity": "CRITICAL",
      "result": "PASS",
      "details": "Safety classifier 결과와 report CTRS 섹션 일치"
    },
    {
      "check_id": "V-08",
      "name": "12개 섹션 완전성",
      "severity": "HIGH",
      "result": "PASS",
      "details": "12개 섹션 모두 존재"
    },
    {
      "check_id": "V-09",
      "name": "Evidence registry 정합성",
      "severity": "HIGH",
      "result": "PASS",
      "details": "인용된 7개 ID 모두 registry에 존재"
    },
    {
      "check_id": "V-10",
      "name": "Disclaimer 존재",
      "severity": "HIGH",
      "result": "PASS",
      "details": "Section 5, 11, 12 disclaimer 확인"
    },
    {
      "check_id": "V-11",
      "name": "종단 비교 근거 충분성",
      "severity": "MEDIUM",
      "result": "PASS",
      "details": "improved/unchanged 판정 모두 evidence 포함"
    },
    {
      "check_id": "V-12",
      "name": "시제/표현 일관성",
      "severity": "LOW",
      "result": "PASS",
      "details": "일관성 확인"
    }
  ],
  "critical_violations": 0,
  "high_violations": 0,
  "medium_violations": 0,
  "low_violations": 0,
  "action": "RELEASE",
  "timestamp": "2026-06-18T14:36:30+09:00"
}
```

### Reject 시 출력 예시

```json
{
  "report_id": "handoff_20260618_001",
  "verification_result": "FAIL",
  "retry_count": 1,
  "checks": [
    {
      "check_id": "V-02",
      "name": "진단적 단정 부재",
      "severity": "CRITICAL",
      "result": "FAIL",
      "details": "Section 5에서 '주요우울장애가 의심됩니다' 표현 발견. 진단적 단정 금지 위반.",
      "location": "sections.s05_mental_health_domains.candidates[0].basis",
      "suggested_fix": "'우울 영역 관련 증상이 수집되었습니다'로 변경"
    }
  ],
  "critical_violations": 1,
  "action": "REJECT_AND_REGENERATE",
  "rejection_instructions": [
    "Section 5의 '주요우울장애가 의심됩니다'를 '우울 영역 관련 증상이 수집되었습니다'로 수정"
  ],
  "timestamp": "2026-06-18T14:36:30+09:00"
}
```

## 핵심 동작

1. **전수 검증**: 12개 검증 항목을 모두 수행한다. 일부만 검증하지 않는다.
2. **CRITICAL 위반 시 즉시 reject**: CRITICAL 심각도 항목이 하나라도 FAIL이면 report를 reject한다.
3. **Reject → 재생성 루프**: reject 시 violation 상세와 수정 지시를 HandoffGeneratorAgent에 전달한다. 최대 2회 재시도.
4. **3회 실패 시 경고 배포**: 2회 재시도 후에도 CRITICAL 위반이 남아있으면, 경고 메시지를 첨부하여 의료진에게 전달한다. report를 차단하지는 않는다 (의료진 판단 우선).
5. **Rule-based 점수 교차 검증**: report 내 구조화 척도 점수를 rule-based 계산 원본과 대조한다.
6. **진단/치료 표현 패턴 탐지**: 금지 표현 패턴 사전 기반으로 report 텍스트를 스캔한다.
7. **Evidence trace**: report 내 모든 `[ev_*]` ID가 evidence registry에 존재하고, 원본 데이터와 일치하는지 검증한다.

## 금지 표현 패턴 (예시)

| 카테고리 | 패턴 예시 |
|---|---|
| 진단적 단정 | `~장애`, `~증`, `~병`, `의심됩니다`, `진단`, `확진` |
| 치료 지시 | `처방`, `투약`, `입원`, `~해야 합니다`, `~하세요`, `권고합니다` |
| 과도한 확신 | `확실히`, `분명히`, `틀림없이` |

- 문맥 의존적 패턴은 LLM이 판별한다 (예: "이전 진단서에 우울증이 기재되어 있었습니다"는 허용).

## 안전 제약

1. **Release gate 역할**: 이 에이전트를 통과하지 않은 report는 의료진에게 전달되지 않는다.
2. **CRITICAL 위반 무시 금지**: CRITICAL 위반은 어떤 경우에도 무시할 수 없다. 3회 실패 시에도 경고를 첨부한다.
3. **자동 수정 금지**: Verifier는 report를 직접 수정하지 않는다. 수정은 HandoffGeneratorAgent가 수행한다.
4. **검증 로그 보존**: 모든 검증 결과(PASS/FAIL)를 로그에 저장한다. 추후 감사(audit)에 활용한다.

## 실패 시 대응

| 실패 유형 | 대응 |
|---|---|
| LLM 검증 실패 | Rule-based 검증 항목(V-01, V-04, V-05, V-08, V-09)만 수행. LLM 의존 항목(V-02, V-03, V-12)은 "검증 불가" 표기 |
| 전체 LLM 실패 | Rule-based 검증만 수행 + 의료진에게 "LLM 검증 미완료" 경고 첨부 |
| 검증 timeout | 타임아웃된 항목만 "검증 불가"로 표기하고, 나머지 결과를 반환 |
| 3회 연속 CRITICAL 실패 | Report에 상세 경고를 첨부하여 의료진에게 전달. 차단하지 않음 |
