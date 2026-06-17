---
patient_id: VP-005
vendor: upstage
model: solar-pro3
latency_ms: 6982
tokens: 2251
finish_reason: stop
generated_at: 2026-06-16T14:58:32+09:00
data_type: synthetic
quality_pass: True
sections_present: 11/11
evidence_citations: 22
diagnosis_violations: 0
risk_match: True
---

## Handoff Summary

### 1. One-line Summary
최유진님은 피로감과 졸림, 업무 스트레스를 호소하며 PHQ-9 14점(중등도), GAD-7 11점(중등도)의 우울 및 불안 증상을 보이고 있습니다. [ev_msg_002][ev_msg_006][ev_scale_001][ev_scale_002]

### 2. Chief Complaint (주호소)
- 몸도 안 좋고 요즘 일도 힘들어서 왔어요. [ev_msg_002]
- 잠은 자는데 일어나면 몸이 무겁고, 하루 종일 피곤해요. 자꾸 졸려서 일을 못 할 때도 있어요. [ev_msg_006]

### 3. History of Present Illness (현병력)
환자는 몸 상태가 좋지 않고 업무 스트레스가 심하다고 호소하며 내원했습니다. 두통약을 주 3~4회 복용하고 있으며, 복용 시 소화제를 함께 사용하지만 특별한 부작용은 없다고 했습니다. 수면은 취하고 있으나 아침에 개운하지 않고 피로감이 지속되며, 하루 종일 졸림이 있어 업무에 지장을 받고 있습니다. [ev_msg_002][ev_msg_004][ev_msg_006]

### 4. 주요 증상
| 영역 | 상태 | 근거 |
|---|---|---|
| 수면 | 수면은 취하지만 아침에 개운하지 않고 피로감이 지속됨 | [ev_msg_006] |
| 식욕 | 정보 미수집 | [ev_msg_002] |
| 기분 | 정보 미수집 | [ev_msg_002] |
| 불안 | 정보 미수집 | [ev_msg_002] |
| 집중력 | 정보 미수집 | [ev_msg_002] |
| 기능 손상 | 하루 종일 졸림으로 인해 업무에 지장을 받음 | [ev_msg_006] |

### 5. PHQ-9 / GAD-7
- PHQ-9 총점: 14점 (중등도) [ev_scale_001]
- GAD-7 총점: 11점 (중등도) [ev_scale_002]

### 6. Risk & Safety Flags
현재 직접적 위험 신호 없음 [ev_risk_001]

### 7. Medication / Past History
- 두통약: 주 3~4회 복용, 소화제와 함께 사용, 특별한 부작용은 없음 [ev_msg_004]
- 과거 정신건강 진료 이력: 재진 — 이전 세션 정보는 대화 내 약물 관련 발화 참조 [ev_prior_handoff_001]

### 8. Uploaded Documents
없음 [ev_doc_001]

### 9. Longitudinal Delta
해당 없음 (초진) [ev_msg_002]

### 10. Missing Information
- 식욕 변화
- 기분 변화
- 불안 수준
- 집중력 변화
- 과거 정신건강 진료 이력 상세 내용
- 이전 세션의 구체적인 약물 관련 발화 내용

### 11. Evidence Table
| ID | 유형 | 출처 | 내용 요약 |
|---|---|---|---|
| ev_msg_001 | message | 환자 발화 | "안녕하세요, 최유진님. 지난번 상담을 기억합니다. 오늘은 몸 상태와 기분 변화를 좀 더 자세히 얘기해 주실 수 있을까요?" |
| ev_msg_002 | message | 환자 발화 | "네, 안녕하세요. 몸도 좀 안 좋고 요즘 일도 힘들어서 왔어요." |
| ev_msg_003 | message | 환자 발화 | "두통약을 주 3~4회 정도 복용하고 계신가요? 혹시 복용 후 부작용은 없었나요?" |
| ev_msg_004 | message | 환자 발화 | "네, 가끔 먹어요. 속이 안 좋아서 소화제도 같이 먹곤 해요. 근데 약은 별 문제 없어요." |
| ev_msg_005 | message | 환자 발화 | "잠은 잘 주무시나요? 아침에 일어나면 개운하신가요, 아니면 여전히 피로감이 남아 있나요?" |
| ev_msg_006 | message | 환자 발화 | "잠은 자는데 일어나면 몸이 무겁고, 하루 종일 피곤해요. 자꾸 졸려서 일을 못 할 때도 있어요." |
| ev_scale_001 | scale | PHQ-9 | 총점 14점, 중등도 |
| ev_scale_002 | scale | GAD-7 | 총점 11점, 중등도 |
| ev_risk_001 | risk_event | 위험 이벤트 | 없음 |
