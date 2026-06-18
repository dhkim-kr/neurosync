---
patient_id: VP-003
vendor: exaone
model: depmkuykpfon9lg
latency_ms: 12633
tokens: 2566
finish_reason: stop
generated_at: 2026-06-16T14:56:51+09:00
data_type: synthetic
quality_pass: False
sections_present: 11/11
evidence_citations: 23
diagnosis_violations: 0
risk_match: False
---

## Handoff Summary

### 1. One-line Summary
환자는 지속적인 무기력과 수면 장애, 우울 및 불안 증상 호소하며, 일상 기능 저하 상태임 [ev_msg_002][ev_msg_004][ev_msg_006][ev_msg_009][ev_scale_001][ev_scale_0ают_002]

### 2. Chief Complaint (주호소)
- 환자는 "매일 똑같아요. 집에 누워만 있어요"라고 표현하며 일상 활동 저하를 호소함 [ev_msg_002]

### 3. History of Present Illness (현병력)
- 환자는 최근 수면 장애로 인해 새벽 3시경 깨며 이후 수면 유지 어려움, 하루 평균 수면 시간 약 3시간으로 보고함 [ev_msg_004]
- 식욕 저하 및 무기력감 호소, TV 시청 등 일상 활동 수행 어려움 언급 [ev_msg_009]
- 기분 저하 및 희망 상실감, 미래에 대한 걱정(특히 경제적 부담) 표현 [ev_msg_006][ev_msg_007]
- 술 섭취 빈도 증가, 수면 개선 목적이나 오히려 악화 가능성 시사 [ev_msg_008]

### 4. 주요 증상
| 영역 | 상태 | 근거 |
|---|---|---|
| 수면 | 새벽 3시경 각성, 수면 유지 어려움, 일일 수면 시간 약 3시간 | [ev_msg_004] |
| 식욕 | 식욕 저하 보고됨 (직접 언급은 없으나 보조자 언급 기반) | [ev_msg_005] |
| 기분 | 기분 무거움, 희망 상실감, 무기력감 | [ev_msg_006] |
| 불안 | 미래에 대한 걱정, 특히 경제적 부담에 대한 우려 | [ev_msg_007] |
| 집중력 | 일상 활동 수행 어려움 (TV 시청조차 어려움) | [ev_msg_009] |
| 기능 손상 | 일상 활동 대부분 중단, 주로 침상 생활 유지 | [ev_msg_002][ev_msg_009] |

### 5. PHQ-9 / GAD-7
- PHQ-9 총점 22점 (27점 만점), 심각도: severe [ev_scale_001]
- GAD-7 총점 16점 (21점 만점), 심각도: severe [ev_scale_002]

### 6. Risk & Safety Flags
- 현재 직접적 위험 신호 없음 (자해, 타해, 자살 생각 등 명시적 언급 없음) [ev_risk_001]

### 7. Medication / Past History
- 약물 복용 이력은 대화 내 명시되지 않음. 이전 세션에서 약물 관련 언급 존재하나 구체적 내용 미제공 [prior_handoff_001]

### ্ম Uploaded Documents
- 업로드된 문서 없음 [ev_doc_001]

### 9. Longitudinal Delta
- 이전 대비 변화 정보 미수집. 재진이지만 이전 세션 대비 변화 평가에 대한 구체적 언급 없음 [prior_handoff_001]

### .
- **Missing Information**
  - 약물 복용 이력 (구체적 약물명, 용량, 복용 여부)
  - 과거 정신건강 진료 이력 (진단명, 치료 이력)
  - 자해 또는 자살 생각 여부
  - 사회적 지지 체계 (가족, 친구 등)
  - 음주 빈도 및 양
  - 이전 치료 반응 여부
  - 신체 질환 동반 여부
  - 일상 활동 구체적 수준 (예: 식사, 위생, 외출 등)

### 11. Evidence Table
| ID | 유형 | 출처 | 내용 요약 |
|---|---|---|---|
| ev_msg_001 | message | 환자 발화 | "안녕하세요, 박성호님. 최근 어떻게 지내고 계세요?" — 대화 시작 |
| ev_msg_002 | message | 환자 발화 | "그냥... 매일 똑같아요. 집에 누워만 있어요." — 일상 기능 저하 |
| ev_msg_003 | message | 환자 발화 | "잠은 잘 주무시고 계신가요? 요즘은 어떤가요?" — 수면 관련 질문 |
| ev_msg_004 | message | 환자 발 coexisting | "새벽 3시쯤 깨서 다시 못 자요. 하루 3시간 정도밖에 못 자요." — 수면 장애 |
| ev_msg_005 | message | 환자 발화 | "식사나 물 마시는 건 어떠세요? 식욕이 많이 떨어졌다고 들었어요." — 식욕 저하 (간접 언급) |
| ev_msg_006 | message | 환자 발화 | "기분이 계속 무겁고 희망이 없어진 것 같다고 느껴지세요?" — 기분 저하 |
| ev_msg_007 | message | 환자 발화 | "미래에 대한 걱정도 많이 되시나요? 특히 경제적으로요." — 불안 및 경제적 우려 |
| ev_msg_008 | message | 환자 발화 | "술을 자주 드시게 되신 이유가 뭔가요? 잠도 잘 못 자시고." — 음주 빈도 증가 (수면 문제 관련) |
| ev_msg_009 | message | 환자 발화 | "기운이 없고, 뭘 하기도 힘드신가요? TV 보는 것도 어렵나요?" — 무기력 및 기능 손상 |
| ev_msg_010 | message | 환자 발화 | "혼자서 힘들어하실 필요 없어요. 언제든 다시 이야기 나눠요." — 지지 제안 |
| ev_scale_001 | scale | PHQ-9 결과 | 총점 22점, 심각도: severe |
| ev_scale_002 | scale | GAD-7 결과 | 총점 16점, 심각도: severe |
| ev_risk_001 | risk_event | 위험 이벤트 | 위험 이벤트 없음 |
| ev_doc_001 | document_block | 업로드 문서 | 업로드 문서 없음 |
| prior_handoff_001 | prior_handoff | 이전 세션 기록 | 이전 세션에서 약물 관련 언급 존재하나 구체적 내용 미제공 |