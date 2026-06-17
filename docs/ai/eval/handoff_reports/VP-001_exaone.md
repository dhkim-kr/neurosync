---
patient_id: VP-001
vendor: exaone
model: depmkuykpfon9lg
latency_ms: 6127
tokens: 2147
finish_reason: stop
generated_at: 2026-06-16T14:55:43+09:00
data_type: synthetic
quality_pass: True
sections_present: 11/11
evidence_citations: 20
diagnosis_violations: 0
risk_match: True
---

## Handoff Summary

### 1. One-line Summary
환자는 최근 3주간 수면 장애와 출근 시 답답함을 호소하며, 수면 유지 및 입면 곤란이 지속되고 있음 [ev_msg_002][ev_msg_004][ev_msg_006]

### 2. Chief Complaint (주호소)
- 최근 3주간 수면 장애와 출근 시 답답한 느낌을 호소함 [ev_msg_002][ev_msg_006]

### 3. History of Present Illness (현병력)
- 약 3주 전부터 수면 장애가 시작되었으며, 초기에는 가끔 발생했으나 점차 빈도와 강도가 증가함 [ev_msg_002]
- 입면까지 1~2시간 소요되며, 침대에 누워 있어도 생각이 계속 돌아와 수면 유지에 어려움을 겪고 있음 [ev_msg_004]
- 수면 시간은 밤 12시 취침, 아침 6시 이전 기상으로 총 약 5시간 수준임 [ev_msg_006]
- 출근 시 답답한 느낌을 동반하며, 일상 기능에 일부 영향을 줄 수 있음 [ev_msg_006]

### 4. 주요 증상
| 영역 | 상태 | 근거 |
|------|------|------|
| 수면 | 입면 지연 (1~2시간), 총 수면 시간 약 5시간 | [ev_msg_004][ev_msg_006] |
| 기분 | 우울 증상 호소 (PHQ-9 점수 8점, mild 수준) | [ev_scale_001] |
| 불안 | 불안 증상 호소 (GAD-7 점수 5점, mild 수준) | [ev_scale_002] |
| 기능 손상 | 출근 시 답답함으로 인한 기능 저하 시사 | [ev_msg_006] |
| 식욕 | 정보 미수집 | 판단불가 |
| 집중력 | 정보 미수집 | 판단불가 |

### 5. PHQ-9 / GAD-7
- PHQ-9 총점 8점 (mild 우울 증상 수준) [ev_scale_001]
- GAD-7 총점 5점 (mild 불안 증상 수준) [ev_scale_002]

### 6. Risk & Safety Flags
- 현재 직접적 위험 신호 없음 [ev_risk_001]

### 7. Medication / Past History
- 복용 중인 약물 정보 미수집
- 과거 정신건강 진료 이력 없음 (초진) [ev_msg_001]

### 8. Uploaded Documents
- 업로드된 문서 없음 [ev_doc_001]

### 9. Longitudinal Delta
- 이전 세션 기록 없음 (초진) [ev_msg_001]

### 10. Missing Information
- 복용 중인 약물 정보
- 식욕 변화 여부
- 집중력 저하 여부
- 기분 변화 양상 (예: 무기력, 슬픔 등 구체적 감정)
- 기능 손상 정도 (업무, 대인관계 등)
- 수면 중 각성 여부
- 수면 위생 습관

### 0. Evidence Table
| ID | 유형 | 출처 | 내용 요약 |
|---|---|---|---|
| ev_msg_001 | message | 환자 발화 | 초진 인사 및 대화 시작 |
| ev_msg_002 | message | 환자 발화 | 수면 문제 시작 시점: 약 3주 전 |
| ev_msg_004 | message | 환자 발화 | 입면 지연: 1~2시간 소요 |
| ev_msg_006 | message | 환자 발화 | 취침 시간: 밤 12시, 기상: 아침 6시 이전, 총 수면 약 5시간 |
| ev_scale_001 | scale | PHQ-9 결과 | 총점 8점, mild 우울 증상 수준 |
| ev_scale_002 | scale | GAD-7 결과 | 총점 5점, mild 불안 증상 수준 |
| ev_risk_001 | risk_event | 위험 이벤트 | 현재 직접적 위험 신호 없음 |