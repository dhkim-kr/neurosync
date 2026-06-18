---
patient_id: VP-003
vendor: upstage
model: solar-pro3
latency_ms: 8831
tokens: 2539
finish_reason: stop
generated_at: 2026-06-16T14:56:38+09:00
data_type: synthetic
quality_pass: False
sections_present: 11/11
evidence_citations: 26
diagnosis_violations: 0
risk_match: False
---

## Handoff Summary

### 1. One-line Summary
박성호님은 심한 우울 및 불안 증상을 호소하며, 수면 부족과 무기력감이 지속되고 있습니다. [ev_msg_002][ev_msg_004][ev_msg_006][ev_msg_007][ev_msg_009]

### 2. Chief Complaint (주호소)
- 매일 집에 누워만 있으며, 일상 활동에 대한 흥미와 동기 부족을 호소합니다. [ev_msg_002]
- 수면 장애(새벽 3시 경 각성 후 재수면 불가)로 인해 하루 3시간 정도만 수면을 취하고 있습니다. [ev_msg_004]

### 3. History of Present Illness (현병력)
- 환자는 "매일 똑같아요. 집에 누워만 있어요"라고 표현하며, 일상 생활의 무기력함과 활동 감소를 호소하고 있습니다. [ev_msg_002]
- 수면 시작 및 유지에 어려움을 겪고 있으며, 새벽 3시경 각성 후 다시 잠들지 못해 하루 평균 3시간 정도만 수면을 취하고 있습니다. [ev_msg_004]
- 식욕이 많이 떨어졌다고 표현하며, 식사나 물 마시는 것에 대한 구체적인 어려움은 언급되지 않았습니다. [ev_msg_005]
- 기분이 무겁고 희망이 없어진 것 같다고 느끼며, 미래에 대한 경제적 걱정이 많다고 호소합니다. [ev_msg_006][ev_msg_007]
- 기운이 없고, TV 보는 것도 힘들 정도로 일상 활동에 대한 에너지가 부족하다고 표현합니다. [ev_msg_009]

### 4. 주요 증상
| 영역 | 상태 | 근거 |
|---|---|---|
| 수면 | 새벽 3시경 각성 후 재수면 불가, 하루 3시간 수면 | [ev_msg_004] |
| 식욕 | 식욕 감소 | [ev_msg_005] |
| 기분 | 무겁고 희망이 없어진 느낌 | [ev_msg_006] |
| 불안 | 미래에 대한 경제적 걱정 | [ev_msg_007] |
| 집중력 | TV 시청 등 일상 활동에 어려움 | [ev_msg_009] |
| 기능 손상 | 집에 누워만 있는 상태, 일상 활동 감소 | [ev_msg_002][ev_msg_009] |

### 5. PHQ-9 / GAD-7
- **PHQ-9**: 총점 22점 (심각도: severe) — 우울 증상 전반에 걸쳐 높은 점수 분포 [ev_scale_001]
- **GAD-7**: 총점 16점 (심각도: severe) — 불안 증상 전반에 걸쳐 높은 점수 분포 [ev_scale_002]

### 6. Risk & Safety Flags
- 현재 직접적 위험 신호 없음 [ev_risk_001]

### 7. Medication / Past History
- 이전 세션에서 약물 관련 발화가 있었으나, 구체적인 약물명, 용량, 복용 이력 등은 제공되지 않았습니다. [ev_prior_handoff_001]

### 8. Uploaded Documents
- 없음 [ev_doc_001]

### 9. Longitudinal Delta
- 해당 없음 (초진) [ev_prior_handoff_001]

### 10. Missing Information
- 구체적인 약물 복용 이력 및 과거 정신건강 진료 이력
- 식욕 감소의 구체적 정도 및 체중 변화
- 경제적 걱정의 구체적 내용 및 영향
- 수면 장애의 지속 기간 및 과거 수면 패턴
- 일상 활동 감소의 구체적 범위 및 사회적 기능 손상 정도

### 11. Evidence Table
| ID | 유형 | 출처 | 내용 요약 |
|---|---|---|---|
| ev_msg_001 | message | 환자 발화 | "안녕하세요, 박성호님. 최근 어떻게 지내고 계세요?" |
| ev_msg_002 | message | 환자 발화 | "그냥... 매일 똑같아요. 집에 누워만 있어요." |
| ev_msg_003 | message | 환자 발화 | "잠은 잘 주무시고 계신가요? 요즘은 어떤가요?" |
| ev_msg_004 | message | 환자 발화 | "새벽 3시쯤 깨서 다시 못 자요. 하루 3시간 정도밖에 못 자요." |
| ev_msg_005 | message | 환자 발화 | "식사나 물 마시는 건 어떠세요? 식욕이 많이 떨어졌다고 들었어요." |
| ev_msg_006 | message | 환자 발화 | "기분이 계속 무겁고 희망이 없어진 것 같다고 느껴지세요?" |
| ev_msg_007 | message | 환자 발화 | "미래에 대한 걱정도 많이 되시나요? 특히 경제적으로요." |
| ev_msg_008 | message | 환자 발화 | "술을 자주 드시게 되신 이유가 뭔가요? 잠도 잘 못 자시고." |
| ev_msg_009 | message | 환자 발화 | "기운이 없고, 뭘 하기도 힘드신가요? TV 보는 것도 어렵나요?" |
| ev_msg_010 | message | 환자 발화 | "혼자서 힘들어하실 필요 없어요. 언제든 다시 이야기 나눠요." |
| ev_scale_001 | scale | PHQ-9 | 총점 22점 (심각도: severe), 문항별 점수 [3, 3, 3, 3, 2, 2, 3, 2, 1] |
| ev_scale_002 | scale | GAD-7 | 총점 16점 (심각도: severe), 문항별 점수 [3, 2, 3, 2, 2, 2, 2] |
| ev_risk_001 | risk_event | 위험 이벤트 | 없음 |
